"""
Automatisches Backup-System für Scandy
Führt 2 Backups pro Tag zu festen Zeiten aus
"""
import os
import time
import threading
import logging
import zipfile
import socket
import random
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from app.utils.unified_backup_manager import UnifiedBackupManager

logger = logging.getLogger(__name__)

class AutoBackupScheduler:
    """Automatischer Backup-Scheduler"""
    
    def __init__(self):
        self.backup_manager = UnifiedBackupManager()
        self.running = False
        self.thread = None
        
        # Worker-ID für Koordination zwischen Gunicorn-Workern
        self.worker_id = self._generate_worker_id()
        
        # Standard-Backup-Zeiten (24h Format) - werden aus DB überschrieben
        self.backup_times = [
            dt_time(6, 0),   # 06:00 Uhr
            dt_time(18, 0)   # 18:00 Uhr
        ]
        
        # Wöchentliches Backup-Archiv (Freitag um 17:00)
        self.weekly_backup_time = dt_time(17, 0)  # 17:00 Uhr
        self.last_weekly_backup_date = None
        
        # Backup-Log-Datei
        self.log_file = Path(__file__).parent.parent.parent / 'logs' / 'auto_backup.log'
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Lade konfigurierte Zeiten beim Start
        self._load_backup_times()
        self._load_weekly_backup_config()
        
    def _generate_worker_id(self):
        """Generiert eine eindeutige Worker-ID basierend auf Hostname und PID"""
        try:
            hostname = socket.gethostname()
            pid = os.getpid()
            # Zusätzliche Zufallszahl für bessere Eindeutigkeit
            random_suffix = random.randint(1000, 9999)
            return f"{hostname}-{pid}-{random_suffix}"
        except Exception:
            # Fallback falls Hostname nicht verfügbar
            return f"worker-{os.getpid()}-{random.randint(1000, 9999)}"
    
    def _is_primary_worker(self):
        """Ermittelt ob dieser Worker das Backup ausführen soll"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Prüfe ob bereits ein Backup für diese Zeit läuft
            current_time = datetime.now()
            backup_key = f"backup_running_{current_time.strftime('%Y%m%d_%H%M')}"
            
            # Versuche Lock zu setzen (TTL: 5 Minuten)
            lock_ok = mongodb.update_one(
                'system_locks',
                {'key': backup_key},
                {'$set': {'worker_id': self.worker_id, 'created_at': current_time}},
                upsert=True
            )
            
            # Kompatibel: bool oder UpdateResult-ähnlich
            acquired = False
            try:
                acquired = bool(lock_ok)
            except Exception:
                acquired = False
            try:
                if hasattr(lock_ok, 'upserted_id') and lock_ok.upserted_id:
                    acquired = True
                if hasattr(lock_ok, 'modified_count') and getattr(lock_ok, 'modified_count', 0) > 0:
                    acquired = True
            except Exception:
                pass
            
            if acquired:
                logger.info(f"Worker {self.worker_id} übernimmt Backup-Aufgabe")
                return True
            else:
                logger.info(f"Worker {self.worker_id} überspringt Backup (bereits in Bearbeitung)")
                return False
                
        except Exception as e:
            logger.error(f"Fehler bei Worker-Koordination: [Interner Fehler]")
            # Bei Fehlern: Backup trotzdem ausführen (sicherer Fallback)
            return True
    
    def _release_backup_lock(self):
        """Gibt den Backup-Lock frei"""
        try:
            from app.models.mongodb_database import mongodb
            
            current_time = datetime.now()
            backup_key = f"backup_running_{current_time.strftime('%Y%m%d_%H%M')}"
            
            # Lösche Lock nur wenn er von diesem Worker gesetzt wurde
            mongodb.delete_one('system_locks', {
                'key': backup_key,
                'worker_id': self.worker_id
            })
            
        except Exception as e:
            logger.error(f"Fehler beim Freigeben des Backup-Locks: [Interner Fehler]")
    
    def _cleanup_expired_locks(self):
        """Bereinigt abgelaufene Locks aus der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            current_time = datetime.now()
            
            # Lösche alle abgelaufenen Locks (älter als 1 Stunde)
            expiry_time = current_time - timedelta(hours=1)
            result = mongodb.delete_many('system_locks', {
                'created_at': {'$lt': expiry_time}
            })
            
            if hasattr(result, 'deleted_count') and result.deleted_count > 0:
                logger.info(f"{result.deleted_count} abgelaufene Locks bereinigt")
                
        except Exception as e:
            logger.error(f"Fehler beim Bereinigen abgelaufener Locks: [Interner Fehler]")
    
    def _load_backup_times(self):
        """Lädt die konfigurierten Backup-Zeiten aus der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Lade konfigurierte Backup-Zeiten
            backup_times_setting = mongodb.find_one('settings', {'key': 'auto_backup_times'})
            
            if backup_times_setting and backup_times_setting.get('value'):
                # Parse die Zeiten aus dem String-Format "06:00,18:00"
                time_strings = backup_times_setting['value'].split(',')
                self.backup_times = []
                
                for time_str in time_strings:
                    time_str = time_str.strip()
                    if ':' in time_str:
                        try:
                            hour, minute = map(int, time_str.split(':'))
                            if 0 <= hour <= 23 and 0 <= minute <= 59:
                                self.backup_times.append(dt_time(hour, minute))
                        except ValueError:
                            logger.warning(f"Ungültige Backup-Zeit: {time_str}")
                
                # Stelle sicher, dass mindestens eine Zeit vorhanden ist
                if not self.backup_times:
                    self.backup_times = [dt_time(6, 0), dt_time(18, 0)]
                    
                logger.info(f"Backup-Zeiten geladen: {[t.strftime('%H:%M') for t in self.backup_times]}")
            else:
                logger.info("Keine konfigurierten Backup-Zeiten gefunden, verwende Standard-Zeiten")
                
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Zeiten: [Interner Fehler]")
            # Verwende Standard-Zeiten bei Fehlern
            self.backup_times = [dt_time(6, 0), dt_time(18, 0)]
    
    def _load_weekly_backup_config(self):
        """Lädt die wöchentliche Backup-Konfiguration aus der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Lade wöchentliche Backup-Zeit
            weekly_time_setting = mongodb.find_one('settings', {'key': 'weekly_backup_time'})
            if weekly_time_setting and weekly_time_setting.get('value'):
                try:
                    hour, minute = map(int, weekly_time_setting['value'].split(':'))
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        self.weekly_backup_time = dt_time(hour, minute)
                        logger.info(f"Wöchentliche Backup-Zeit geladen: {self.weekly_backup_time.strftime('%H:%M')}")
                except ValueError:
                    logger.warning(f"Ungültige wöchentliche Backup-Zeit: {weekly_time_setting['value']}")
            
            # Lade letztes wöchentliches Backup-Datum
            last_weekly_setting = mongodb.find_one('settings', {'key': 'last_weekly_backup_date'})
            if last_weekly_setting and last_weekly_setting.get('value'):
                try:
                    self.last_weekly_backup_date = datetime.strptime(last_weekly_setting['value'], '%Y-%m-%d').date()
                    logger.info(f"Letztes wöchentliches Backup: {self.last_weekly_backup_date}")
                except ValueError:
                    logger.warning(f"Ungültiges Datum für letztes wöchentliches Backup: {last_weekly_setting['value']}")
                    
        except Exception as e:
            logger.error(f"Fehler beim Laden der wöchentlichen Backup-Konfiguration: [Interner Fehler]")
    
    def save_backup_times(self, times_list):
        """Speichert neue Backup-Zeiten in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Validiere und konvertiere Zeiten
            valid_times = []
            for time_str in times_list:
                time_str = time_str.strip()
                if ':' in time_str:
                    try:
                        hour, minute = map(int, time_str.split(':'))
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            valid_times.append(f"{hour:02d}:{minute:02d}")
                    except ValueError:
                        logger.warning(f"Ungültige Backup-Zeit übersprungen: {time_str}")
            
            if valid_times:
                # Speichere in Datenbank
                times_string = ','.join(valid_times)
                mongodb.update_one('settings', 
                                 {'key': 'auto_backup_times'}, 
                                 {'$set': {'value': times_string}}, 
                                 upsert=True)
                
                # Aktualisiere lokale Zeiten
                self.backup_times = [dt_time(int(t.split(':')[0]), int(t.split(':')[1])) for t in valid_times]
                
                logger.info(f"Backup-Zeiten aktualisiert: {valid_times}")
                return True, "Backup-Zeiten erfolgreich gespeichert"
            else:
                return False, "Keine gültigen Zeiten gefunden"
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Backup-Zeiten: [Interner Fehler]")
            return False, f"Fehler beim Speichern: [Interner Fehler]"
    
    def save_weekly_backup_time(self, time_str):
        """Speichert die wöchentliche Backup-Zeit in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Validiere Zeit
            if ':' in time_str:
                try:
                    hour, minute = map(int, time_str.split(':'))
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        # Speichere in Datenbank
                        mongodb.update_one('settings', 
                                         {'key': 'weekly_backup_time'}, 
                                         {'$set': {'value': f"{hour:02d}:{minute:02d}"}}, 
                                         upsert=True)
                        
                        # Aktualisiere lokale Zeit
                        self.weekly_backup_time = dt_time(hour, minute)
                        
                        logger.info(f"Wöchentliche Backup-Zeit aktualisiert: {self.weekly_backup_time.strftime('%H:%M')}")
                        return True, "Wöchentliche Backup-Zeit erfolgreich gespeichert"
                    else:
                        return False, "Ungültige Zeit (Stunden: 0-23, Minuten: 0-59)"
                except ValueError:
                    return False, "Ungültiges Zeitformat (HH:MM)"
            else:
                return False, "Ungültiges Zeitformat (HH:MM)"
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern der wöchentlichen Backup-Zeit: [Interner Fehler]")
            return False, f"Fehler beim Speichern: [Interner Fehler]"
    
    def get_backup_times(self):
        """Gibt die aktuellen Backup-Zeiten zurück"""
        return [t.strftime('%H:%M') for t in self.backup_times]
    
    def get_weekly_backup_time(self):
        """Gibt die aktuelle wöchentliche Backup-Zeit zurück"""
        return self.weekly_backup_time.strftime('%H:%M')
    
    def start(self):
        """Startet den automatischen Backup-Scheduler"""
        if self.running:
            logger.info("Auto-Backup-Scheduler läuft bereits")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        logger.info("Auto-Backup-Scheduler gestartet")
        self._log_backup_event("Auto-Backup-Scheduler gestartet")
        # Catch-up: wenn letzte 12h verpasst wurden, sofort ein Backup anstoßen
        try:
            from app.utils.unified_backup_manager import unified_backup_manager
            # Führe nur ein zusätzliches Backup aus, wenn in den letzten 12h keins erstellt wurde
            bdir = Path('backups')
            latest = None
            for f in bdir.glob('scandy_backup_*.zip'):
                if not latest or f.stat().st_mtime > latest.stat().st_mtime:
                    latest = f
            if not latest:
                unified_backup_manager.create_backup(include_media=True, compress=True)
            else:
                from datetime import datetime as _dt
                if (_dt.now().timestamp() - latest.stat().st_mtime) > 12*3600:
                    unified_backup_manager.create_backup(include_media=True, compress=True)
        except Exception as _e:
            logger.warning(f"Catch-up-Backup übersprungen: {_e}")
        
    def stop(self):
        """Stoppt den automatischen Backup-Scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Auto-Backup-Scheduler gestoppt")
        self._log_backup_event("Auto-Backup-Scheduler gestoppt")
        
    def _scheduler_loop(self):
        """Hauptschleife des Schedulers"""
        last_cleanup = datetime.now()
        
        while self.running:
            try:
                now = datetime.now()
                current_time = now.time()
                current_date = now.date()
                
                # Bereinige abgelaufene Locks alle 10 Minuten
                if (now - last_cleanup).total_seconds() > 600:  # 10 Minuten
                    self._cleanup_expired_locks()
                    last_cleanup = now
                
                # Prüfe ob es Zeit für ein normales Backup ist
                for backup_time in self.backup_times:
                    if (current_time.hour == backup_time.hour and 
                        current_time.minute == backup_time.minute):
                        
                        self._create_scheduled_backup()
                        # Warte 1 Minute um doppelte Backups zu vermeiden
                        time.sleep(60)
                        break
                
                # Prüfe ob es Zeit für ein wöchentliches Backup-Archiv ist (Freitag)
                if (now.weekday() == 4 and  # Freitag = 4
                    current_time.hour == self.weekly_backup_time.hour and 
                    current_time.minute == self.weekly_backup_time.minute and
                    (self.last_weekly_backup_date is None or 
                     current_date > self.last_weekly_backup_date)):
                    
                    self._create_weekly_backup_archive()
                    # Warte 1 Minute um doppelte Backups zu vermeiden
                    time.sleep(60)
                
                # Warte 30 Sekunden bis zur nächsten Prüfung
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Fehler im Auto-Backup-Scheduler: [Interner Fehler]")
                self._log_backup_event(f"FEHLER: [Interner Fehler]")
                time.sleep(60)  # Warte 1 Minute bei Fehlern
                
    def _create_scheduled_backup(self):
        """Erstellt ein geplantes Backup"""
        try:
            logger.info("Erstelle automatisches Backup...")
            self._log_backup_event("Starte automatisches Backup")
            
            # Prüfe ob dieser Worker das Backup ausführen soll
            if not self._is_primary_worker():
                logger.info(f"Worker {self.worker_id} überspringt Backup (nicht primär)")
                return

            # Backup erstellen über vereinheitlichtes System
            from app.utils.unified_backup_manager import unified_backup_manager
            backup_filename = unified_backup_manager.create_backup(include_media=True, compress=True)
            
            if backup_filename:
                logger.info(f"Automatisches ZIP-Backup erfolgreich erstellt: {backup_filename}")
                self._log_backup_event(f"ZIP-Backup erfolgreich: {backup_filename}")
                
                # Retention (7 Tage) sicherstellen – bereits durch Manager, zusätzlich harte Grenze
                try:
                    unified_backup_manager._prune_old_backups(days=7)
                except Exception:
                    pass
                # Optional: E-Mail-Benachrichtigung
                self._send_backup_notification(backup_filename, success=True)
            else:
                logger.error("Automatisches ZIP-Backup fehlgeschlagen")
                self._log_backup_event("ZIP-Backup fehlgeschlagen")
                self._send_backup_notification(None, success=False)
                
        except Exception as e:
            logger.error(f"Fehler beim automatischen Backup: [Interner Fehler]")
            self._log_backup_event(f"Backup-Fehler: [Interner Fehler]")
            self._send_backup_notification(None, success=False)
        finally:
            # Lock freigeben
            self._release_backup_lock()
    
    def _create_weekly_backup_archive(self):
        """Erstellt ein wöchentliches Backup-Archiv und sendet es per E-Mail"""
        try:
            logger.info("Erstelle wöchentliches Backup-Archiv...")
            self._log_backup_event("Starte wöchentliches Backup-Archiv")
            
            # Prüfe ob dieser Worker das Backup ausführen soll
            if not self._is_primary_worker():
                logger.info(f"Worker {self.worker_id} überspringt wöchentliches Backup (nicht primär)")
                return

            # Alle aktuellen ZIP-Backups finden
            backup_files = list(self.backup_manager.backup_dir.glob('scandy_backup_*.zip'))
            
            if not backup_files:
                logger.warning("Keine ZIP-Backup-Dateien für wöchentliches Archiv gefunden")
                self._log_backup_event("Keine ZIP-Backup-Dateien für wöchentliches Archiv gefunden")
                return
            
            # Sortiere nach Änderungsdatum (neueste zuerst)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Erstelle ZIP-Archiv
            archive_filename = f"scandy_weekly_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            archive_path = self.backup_manager.backup_dir / archive_filename
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for backup_file in backup_files:
                    zipf.write(backup_file, backup_file.name)
            
            logger.info(f"Wöchentliches Backup-Archiv erstellt: {archive_filename}")
            self._log_backup_event(f"Wöchentliches Backup-Archiv erstellt: {archive_filename}")
            
            # Sende E-Mail mit Archiv
            email_sent = self._send_weekly_backup_archive(archive_path)
            
            # Aktualisiere letztes wöchentliches Backup-Datum
            self._update_last_weekly_backup_date()
            
            # Lösche ZIP-Datei nach erfolgreichem Versand
            if email_sent and archive_path.exists():
                try:
                    archive_path.unlink()
                    logger.info(f"ZIP-Archiv nach Versand gelöscht: {archive_filename}")
                    self._log_backup_event(f"ZIP-Archiv nach Versand gelöscht: {archive_filename}")
                except Exception as e:
                    logger.error(f"Fehler beim Löschen der ZIP-Datei: [Interner Fehler]")
                    self._log_backup_event(f"Fehler beim Löschen der ZIP-Datei: [Interner Fehler]")
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des wöchentlichen Backup-Archivs: [Interner Fehler]")
            self._log_backup_event(f"Fehler beim wöchentlichen Backup-Archiv: [Interner Fehler]")
        finally:
            # Lock freigeben
            self._release_backup_lock()
    
    def _send_weekly_backup_archive(self, archive_path):
        """Sendet das wöchentliche Backup-Archiv per E-Mail"""
        try:
            from app.utils.email_utils import send_weekly_backup_mail
            
            # E-Mail-Empfänger aus Einstellungen laden
            recipient_email = self._get_weekly_backup_email()
            
            if recipient_email:
                success = send_weekly_backup_mail(recipient_email, str(archive_path))
                if success:
                    logger.info(f"Wöchentliches Backup-Archiv erfolgreich an {recipient_email} gesendet")
                    self._log_backup_event(f"Wöchentliches Backup-Archiv an {recipient_email} gesendet")
                    return True
                else:
                    logger.error("Fehler beim Senden des wöchentlichen Backup-Archivs")
                    self._log_backup_event("Fehler beim Senden des wöchentlichen Backup-Archivs")
                    return False
            else:
                logger.warning("Keine E-Mail-Adresse für wöchentliche Backups konfiguriert")
                self._log_backup_event("Keine E-Mail-Adresse für wöchentliche Backups konfiguriert")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Senden des wöchentlichen Backup-Archivs: [Interner Fehler]")
            self._log_backup_event(f"Fehler beim Senden des wöchentlichen Backup-Archivs: [Interner Fehler]")
            return False
    
    def _get_weekly_backup_email(self):
        """Ermittelt die E-Mail-Adresse für wöchentliche Backups aus den Einstellungen"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Suche nach E-Mail-Einstellung für wöchentliche Backups
            email_setting = mongodb.find_one('settings', {'key': 'weekly_backup_email'})
            if email_setting and email_setting.get('value'):
                return email_setting['value']
            
            # Fallback: Admin-E-Mail
            admin_user = mongodb.find_one('users', {'role': 'admin'})
            if admin_user and admin_user.get('email'):
                return admin_user['email']
                
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln der E-Mail für wöchentliche Backups: [Interner Fehler]")
            return None
    
    def _update_last_weekly_backup_date(self):
        """Aktualisiert das Datum des letzten wöchentlichen Backups"""
        try:
            from app.models.mongodb_database import mongodb
            
            current_date = datetime.now().date()
            self.last_weekly_backup_date = current_date
            
            mongodb.update_one('settings', 
                             {'key': 'last_weekly_backup_date'}, 
                             {'$set': {'value': current_date.strftime('%Y-%m-%d')}}, 
                             upsert=True)
            
            logger.info(f"Letztes wöchentliches Backup-Datum aktualisiert: {current_date}")
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des letzten wöchentlichen Backup-Datums: [Interner Fehler]")
            
    def _log_backup_event(self, message):
        """Loggt Backup-Ereignisse in eine separate Datei"""
        try:
            timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            log_entry = f"[{timestamp}] {message}\n"
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Fehler beim Loggen des Backup-Ereignisses: [Interner Fehler]")
            
    def _send_backup_notification(self, backup_filename, success=True):
        """Sendet E-Mail-Benachrichtigung über Backup-Status"""
        try:
            from app.utils.email_utils import send_backup_mail
            
            if success and backup_filename:
                # Backup-Pfad ermitteln
                backup_path = self.backup_manager.get_backup_path(backup_filename)
                
                # E-Mail an Admin senden
                admin_email = self._get_admin_email()
                if admin_email:
                    send_backup_mail(admin_email, str(backup_path))
                    logger.info(f"Backup-Benachrichtigung an {admin_email} gesendet")
                    
        except Exception as e:
            logger.error(f"Fehler beim Senden der Backup-Benachrichtigung: [Interner Fehler]")
            
    def _get_admin_email(self):
        """Ermittelt die Admin-E-Mail-Adresse aus den Einstellungen"""
        try:
            from app.models.mongodb_database import mongodb
            
            # Suche nach Admin-Benutzer
            admin_user = mongodb.find_one('users', {'role': 'admin'})
            if admin_user and admin_user.get('email'):
                return admin_user['email']
                
            # Fallback: Suche nach erster E-Mail in Settings
            email_setting = mongodb.find_one('settings', {'key': 'admin_email'})
            if email_setting and email_setting.get('value'):
                return email_setting['value']
                
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln der Admin-E-Mail: [Interner Fehler]")
            return None
            
    def get_status(self):
        """Gibt den aktuellen Status des Schedulers zurück"""
        try:
            return {
                'running': self.running,
                'backup_times': [t.strftime('%H:%M') for t in self.backup_times],
                'weekly_backup_time': self.weekly_backup_time.strftime('%H:%M'),
                'next_backup': self._get_next_backup_time(),
                'next_weekly_backup': self._get_next_weekly_backup_time(),
                'last_weekly_backup': self.last_weekly_backup_date.strftime('%d.%m.%Y') if self.last_weekly_backup_date else 'Nie',
                'weekly_backup_email': self._get_weekly_backup_email(),
                'log_file': str(self.log_file)
            }
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Auto-Backup-Status: [Interner Fehler]")
            return {
                'running': self.running,
                'backup_times': [t.strftime('%H:%M') for t in self.backup_times],
                'weekly_backup_time': self.weekly_backup_time.strftime('%H:%M'),
                'next_backup': 'Fehler beim Berechnen',
                'next_weekly_backup': 'Fehler beim Berechnen',
                'last_weekly_backup': 'Fehler beim Laden',
                'weekly_backup_email': 'Fehler beim Laden',
                'log_file': str(self.log_file)
            }
        
    def _get_next_backup_time(self):
        """Ermittelt die nächste Backup-Zeit"""
        now = datetime.now()
        current_time = now.time()
        
        for backup_time in self.backup_times:
            if current_time < backup_time:
                # Heute noch
                next_backup = datetime.combine(now.date(), backup_time)
                return next_backup.strftime('%d.%m.%Y %H:%M')
            else:
                # Morgen - verwende timedelta für sicheres Datum
                tomorrow = now.date() + timedelta(days=1)
                next_backup = datetime.combine(tomorrow, backup_time)
                return next_backup.strftime('%d.%m.%Y %H:%M')
                
        return "Unbekannt"
    
    def _get_next_weekly_backup_time(self):
        """Ermittelt die nächste wöchentliche Backup-Zeit (Freitag)"""
        now = datetime.now()
        current_time = now.time()
        current_date = now.date()
        
        # Berechne nächsten Freitag
        days_until_friday = (4 - now.weekday()) % 7  # 4 = Freitag
        if days_until_friday == 0 and current_time >= self.weekly_backup_time:
            # Heute ist Freitag, aber Zeit ist schon vorbei -> nächster Freitag
            days_until_friday = 7
        
        next_friday = current_date + timedelta(days=days_until_friday)
        next_weekly_backup = datetime.combine(next_friday, self.weekly_backup_time)
        
        return next_weekly_backup.strftime('%d.%m.%Y %H:%M')

# Globale Instanz
auto_backup_scheduler = AutoBackupScheduler()

def start_auto_backup():
    """Startet das automatische Backup-System"""
    auto_backup_scheduler.start()

def stop_auto_backup():
    """Stoppt das automatische Backup-System"""
    auto_backup_scheduler.stop()

def get_auto_backup_status():
    """Gibt den Status des automatischen Backup-Systems zurück"""
    return auto_backup_scheduler.get_status() 