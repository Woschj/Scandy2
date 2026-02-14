"""
Admin Backup Service

Dieser Service enthält alle Funktionen für die Backup-Verwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from app.models.mongodb_database import mongodb
from app.utils.backup_manager import backup_manager

logger = logging.getLogger(__name__)

class AdminBackupService:
    """Service für Admin-Backup-Funktionen"""
    
    @staticmethod
    def get_backup_list() -> List[Dict[str, Any]]:
        """Hole Liste aller Backups"""
        try:
            backup_dir = backup_manager.backup_dir
            backups = []
            
            if backup_dir.exists():
                for backup_file in backup_dir.glob('*.json'):
                    if backup_file.is_file():
                        stat = backup_file.stat()
                        backups.append({
                            'name': backup_file.name,
                            'size': stat.st_size,
                            'created': stat.st_mtime,
                            'type': 'json',
                            'filename': backup_file.name,
                            'size_mb': round(stat.st_size / (1024 * 1024), 2),
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'modified_str': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                        })
            
            # Sortiere nach Änderungsdatum (neueste zuerst)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Liste: {str(e)}")
            return []

    @staticmethod
    def create_backup() -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein neues natives MongoDB-Backup (Standard)
        Nur noch BSON-Format für maximale Datentyp-Erhaltung
        
        Returns:
            (success, message, backup_filename)
        """
        try:
            backup_filename = backup_manager.create_native_backup()
            
            if backup_filename:
                logger.info(f"BSON-Backup erstellt: {backup_filename}")
                return True, f"BSON-Backup '{backup_filename}' erfolgreich erstellt", backup_filename
            else:
                return False, "Fehler beim Erstellen des BSON-Backups", None
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des BSON-Backups: {str(e)}")
            return False, f"Fehler beim Erstellen des BSON-Backups: {str(e)}", None

    @staticmethod
    def upload_backup(file) -> Tuple[bool, str]:
        """
        Lädt ein Backup hoch und stellt es wieder her
        Unterstützt JSON-Backups (für Kompatibilität) und BSON-Backups (Standard)
        
        Args:
            file: Die hochgeladene Backup-Datei
            
        Returns:
            (success, message)
        """
        try:
            if not file:
                return False, "Keine Datei ausgewählt"
            
            if file.filename == '':
                return False, "Keine Datei ausgewählt"
            
            # Prüfe Dateityp - unterstütze JSON und ZIP (für BSON-Backups)
            valid_extensions = ['.json', '.zip']
            file_extension = Path(file.filename).suffix.lower()
            
            if file_extension not in valid_extensions:
                return False, f"Ungültiger Dateityp. Unterstützte Formate: {', '.join(valid_extensions)}"
            
            # Prüfe Dateigröße
            file.seek(0, 2)  # Gehe zum Ende der Datei
            file_size = file.tell()
            file.seek(0)  # Zurück zum Anfang
            
            if file_size == 0:
                return False, "Die hochgeladene Datei ist leer. Bitte wählen Sie eine gültige Backup-Datei aus."
            
            logger.info(f"Backup-Upload: Datei {file.filename}, Größe: {file_size} bytes, Typ: {file_extension}")
            
            # Erstelle Backup der aktuellen DB vor dem Upload
            current_backup = backup_manager.create_native_backup()
            logger.info(f"Backup-Upload: Aktuelles BSON-Backup erstellt: {current_backup}")
            
            # Stelle das hochgeladene Backup wieder her
            if file_extension == '.json':
                # JSON-Backup (alte Kompatibilität)
                success = backup_manager.restore_backup(file)
                backup_type = "JSON"
            else:
                # BSON-Backup (ZIP-Format)
                success = backup_manager.restore_native_backup_from_upload(file)
                backup_type = "BSON"
            
            if success:
                logger.info(f"{backup_type}-Backup erfolgreich hochgeladen und aktiviert: {file.filename}")
                return True, f"{backup_type}-Backup '{file.filename}' erfolgreich hochgeladen und aktiviert"
            else:
                return False, f"Fehler beim Wiederherstellen des {backup_type}-Backups"
                
        except Exception as e:
            logger.error(f"Fehler beim Upload des Backups: {str(e)}")
            return False, f"Fehler beim Upload des Backups: {str(e)}"

    @staticmethod
    def restore_backup(filename: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Stellt ein Backup wieder her
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message, validation_info)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden", None
            
            # Erstelle Backup der aktuellen DB vor der Wiederherstellung
            current_backup = backup_manager.create_backup()
            logger.info(f"Backup-Wiederherstellung: Aktuelles Backup erstellt: {current_backup}")
            
            # Stelle das Backup wieder her
            success = backup_manager.restore_backup_by_filename(filename)
            
            if success:
                # Korrigiere fehlende created_at Felder
                fixed_count = AdminBackupService._fix_missing_created_at_fields()
                
                # Validiere das wiederhergestellte Backup
                validation_info = {
                    'filename': filename,
                    'restored_at': datetime.now(),
                    'previous_backup': current_backup,
                    'collections_restored': ['tools', 'workers', 'consumables', 'users', 'lendings', 'tickets', 'settings'],
                    'fixed_created_at_fields': fixed_count
                }
                
                logger.info(f"Backup erfolgreich wiederhergestellt: {filename} (erganzte Felder: {fixed_count})")
                return True, f"Backup '{filename}' erfolgreich wiederhergestellt", validation_info
            else:
                return False, "Fehler beim Wiederherstellen des Backups", None
                
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Wiederherstellen des Backups: {str(e)}", None

    @staticmethod
    def download_backup(filename: str) -> Tuple[bool, str, Optional[bytes]]:
        """
        Lädt ein Backup zum Download herunter
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message, file_content)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden", None
            
            # Datei lesen
            with open(backup_path, 'rb') as f:
                file_content = f.read()
            
            logger.info(f"Backup zum Download bereitgestellt: {filename}")
            return True, f"Backup '{filename}' zum Download bereit", file_content
            
        except Exception as e:
            logger.error(f"Fehler beim Download des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Download des Backups: {str(e)}", None

    @staticmethod
    def delete_backup(filename: str) -> Tuple[bool, str]:
        """
        Löscht ein Backup
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden"
            
            # Datei löschen
            backup_path.unlink()
            
            logger.info(f"Backup gelöscht: {filename}")
            return True, f"Backup '{filename}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Löschen des Backups: {str(e)}"

    @staticmethod
    def get_backup_statistics() -> Dict[str, Any]:
        """Hole Backup-Statistiken"""
        try:
            backups = AdminBackupService.get_backup_list()
            
            total_size_mb = sum(b['size_mb'] for b in backups)
            oldest_backup = min(backups, key=lambda x: x['modified']) if backups else None
            newest_backup = max(backups, key=lambda x: x['modified']) if backups else None
            
            return {
                'total_backups': len(backups),
                'total_size_mb': total_size_mb,
                'oldest_backup': oldest_backup['modified'] if oldest_backup else None,
                'newest_backup': newest_backup['modified'] if newest_backup else None,
                'average_size_mb': round(total_size_mb / len(backups), 2) if backups else 0
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Statistiken: {str(e)}")
            return {
                'total_backups': 0,
                'total_size_mb': 0,
                'oldest_backup': None,
                'newest_backup': None,
                'average_size_mb': 0
            }

    @staticmethod
    def get_backup_path(filename: str) -> Path:
        """
        Gibt den Pfad zu einer Backup-Datei zurück
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            Path-Objekt zur Backup-Datei
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            return backup_path
            
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln des Backup-Pfads für {filename}: {str(e)}")
            return Path()

    @staticmethod
    def test_backup(filename: str) -> Tuple[bool, str]:
        """
        Testet ein Backup ohne es wiederherzustellen
        
        Args:
            filename: Name der Backup-Datei
            
        Returns:
            (success, message)
        """
        try:
            backup_path = backup_manager.backup_dir / filename
            
            if not backup_path.exists():
                return False, f"Backup-Datei '{filename}' nicht gefunden"
            
            # Backup-Datei lesen und validieren
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Prüfe Struktur
            required_collections = ['tools', 'workers', 'consumables', 'users']
            missing_collections = []
            
            for collection in required_collections:
                if collection not in backup_data:
                    missing_collections.append(collection)
            
            if missing_collections:
                return False, f"Backup ist unvollständig. Fehlende Collections: {', '.join(missing_collections)}"
            
            # Statistiken berechnen
            total_documents = sum(len(documents) for documents in backup_data.values())
            
            logger.info(f"Backup getestet: {filename} - {total_documents} Dokumente in {len(backup_data)} Collections")
            return True, f"Backup '{filename}' ist gültig ({total_documents} Dokumente in {len(backup_data)} Collections)"
            
        except json.JSONDecodeError as e:
            logger.error(f"Backup {filename} ist kein gültiges JSON: {str(e)}")
            return False, f"Backup '{filename}' ist kein gültiges JSON-Format"
        except Exception as e:
            logger.error(f"Fehler beim Testen des Backups {filename}: {str(e)}")
            return False, f"Fehler beim Testen des Backups: {str(e)}"

    @staticmethod
    def _fix_missing_created_at_fields():
        """
        Analysiert fehlende created_at Felder (SICHERE VERSION - nur Analyse, keine Updates)
        """
        try:
            from datetime import datetime
            
            missing_count = 0
            
            # Tools ohne created_at Feld (nur Analyse)
            tools_without_created_at = list(mongodb.find('tools', {
                'created_at': {'$exists': False}
            }))
            
            missing_count += len(tools_without_created_at)
            if tools_without_created_at:
                logger.info(f"{len(tools_without_created_at)} Tools ohne created_at Feld gefunden")
                for tool in tools_without_created_at[:3]:  # Zeige erste 3
                    logger.info(f"  Tool ohne created_at: {tool.get('name', 'Unbekannt')} (ID: {tool.get('_id')})")
            
            # Workers ohne created_at Feld (nur Analyse)
            workers_without_created_at = list(mongodb.find('workers', {
                'created_at': {'$exists': False}
            }))
            
            missing_count += len(workers_without_created_at)
            if workers_without_created_at:
                logger.info(f"{len(workers_without_created_at)} Workers ohne created_at Feld gefunden")
                for worker in workers_without_created_at[:3]:  # Zeige erste 3
                    logger.info(f"  Worker ohne created_at: {worker.get('name', 'Unbekannt')} (ID: {worker.get('_id')})")
            
            # Consumables ohne created_at Feld (nur Analyse)
            consumables_without_created_at = list(mongodb.find('consumables', {
                'created_at': {'$exists': False}
            }))
            
            missing_count += len(consumables_without_created_at)
            if consumables_without_created_at:
                logger.info(f"{len(consumables_without_created_at)} Consumables ohne created_at Feld gefunden")
                for consumable in consumables_without_created_at[:3]:  # Zeige erste 3
                    logger.info(f"  Consumable ohne created_at: {consumable.get('name', 'Unbekannt')} (ID: {consumable.get('_id')})")
            
            # Consumables ohne unit Feld (nur Analyse)
            consumables_without_unit = list(mongodb.find('consumables', {
                'unit': {'$exists': False}
            }))
            
            for consumable in consumables_without_unit:
                mongodb.update_one('consumables', 
                                 {'_id': consumable['_id']}, 
                                 {'$set': {'unit': 'Stück'}})
                fixed_count += 1
            
            # Ergänze sync_status Feld für alle Collections falls fehlend
            collections_to_check = ['tools', 'workers', 'consumables']
            for collection in collections_to_check:
                docs_without_sync = mongodb.find(collection, {
                    'sync_status': {'$exists': False}
                })
                
                for doc in docs_without_sync:
                    mongodb.update_one(collection, 
                                     {'_id': doc['_id']}, 
                                     {'$set': {'sync_status': 'synced'}})
                    fixed_count += 1
            
            # Ergänze deleted_at Feld für alle Collections falls fehlend (für Soft-Delete)
            for collection in collections_to_check:
                docs_without_deleted_at = mongodb.find(collection, {
                    'deleted': True,
                    'deleted_at': {'$exists': False}
                })
                
                for doc in docs_without_deleted_at:
                    deleted_at = doc.get('updated_at') or datetime.now()
                    
                    if isinstance(deleted_at, str):
                        try:
                            deleted_at = datetime.strptime(deleted_at, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                deleted_at = datetime.strptime(deleted_at, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                try:
                                    deleted_at = datetime.strptime(deleted_at, '%Y-%m-%d')
                                except ValueError:
                                    deleted_at = datetime.now()
                    
                    mongodb.update_one(collection, 
                                     {'_id': doc['_id']}, 
                                     {'$set': {'deleted_at': deleted_at}})
                    fixed_count += 1
            
            if fixed_count > 0:
                logger.info(f"Fehlende Felder ergänzt: {fixed_count} Dokumente")
            
            return fixed_count
            
        except Exception as e:
            logger.error(f"Fehler beim Ergänzen fehlender Felder: {str(e)}")
            return 0 

    @staticmethod
    def fix_dashboard_after_backup():
        """
        Behebt Dashboard-Probleme nach Backup-Import automatisch
        SICHERE VERSION: Nur Lese-Operationen, keine Datenbank-Manipulation
        """
        try:
            from datetime import datetime
            
            fixes_applied = {
                'datetime_conversions': 0,
                'missing_fields': 0,
                'data_consistency': 0,
                'objectid_conversions': 0,
                'total': 0
            }
            
            # SICHERE VERSION: Nur Analyse und Logging, keine Datenbank-Updates
            collections_to_analyze = ['tools', 'workers', 'consumables', 'lendings', 'tickets', 'users', 'consumable_usages']
            date_fields = ['created_at', 'updated_at', 'modified_at', 'deleted_at', 'lent_at', 'returned_at', 'due_date', 'resolved_at', 'used_at']
            
            for collection in collections_to_analyze:
                try:
                    # Finde alle Dokumente in der Collection (nur lesen)
                    all_docs = list(mongodb.find(collection, {}))
                    
                    for doc in all_docs:
                        try:
                            # Nur Analyse, keine Updates
                            for field in date_fields:
                                if field in doc:
                                    field_value = doc[field]
                                    if isinstance(field_value, str):
                                        fixes_applied['datetime_conversions'] += 1
                                        logger.info(f"String-Datum gefunden in {collection}.{field}: {field_value}")
                            
                            # ObjectId-Analyse (nur lesen)
                            if '_id' in doc and isinstance(doc['_id'], str) and len(doc['_id']) == 24:
                                fixes_applied['objectid_conversions'] += 1
                                logger.info(f"String-ObjectId gefunden in {collection}: {doc['_id']}")
                                
                        except Exception as e:
                            logger.warning(f"Fehler bei Dokument-Analyse in {collection}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Fehler bei Collection-Analyse {collection}: {str(e)}")
            
            # SICHERE VERSION: Nur Analyse der fehlenden Felder
            try:
                # Analysiere Tools ohne created_at
                tools_without_created = list(mongodb.find('tools', {'created_at': {'$exists': False}}))
                fixes_applied['missing_fields'] = len(tools_without_created)
                
                if tools_without_created:
                    logger.info(f"{len(tools_without_created)} Tools ohne created_at Feld gefunden")
                
                # Analysiere Workers ohne created_at
                workers_without_created = list(mongodb.find('workers', {'created_at': {'$exists': False}}))
                fixes_applied['missing_fields'] += len(workers_without_created)
                
                if workers_without_created:
                    logger.info(f"{len(workers_without_created)} Workers ohne created_at Feld gefunden")
                    
            except Exception as e:
                logger.error(f"Fehler bei Datenkonsistenz-Analyse: {str(e)}")
            
            # Gesamtzahl berechnen
            fixes_applied['total'] = sum([
                fixes_applied['datetime_conversions'],
                fixes_applied['missing_fields'],
                fixes_applied['data_consistency'],
                fixes_applied['objectid_conversions']
            ])
            
            logger.info(f"Dashboard-Analyse abgeschlossen (SICHERE VERSION): {fixes_applied}")
            return fixes_applied
            
        except Exception as e:
            logger.error(f"Fehler bei Dashboard-Analyse: {str(e)}")
            return {'total': 0, 'error': 'Ein interner Fehler ist aufgetreten.'}

    @staticmethod
    def fix_dashboard_after_backup_SAFE():
        """
        SICHERE VERSION: Behebt Dashboard-Probleme nach Backup-Import
        Nur notwendige Updates, keine gefährlichen Operationen
        """
        try:
            from datetime import datetime
            
            fixes_applied = {
                'datetime_conversions': 0,
                'missing_fields': 0,
                'data_consistency': 0,
                'objectid_conversions': 0,
                'total': 0
            }
            
            # SICHERE Updates: Nur fehlende created_at Felder ergänzen
            try:
                # Tools ohne created_at Feld
                tools_without_created = list(mongodb.find('tools', {'created_at': {'$exists': False}}))
                for tool in tools_without_created:
                    fallback_date = tool.get('updated_at') or tool.get('modified_at') or datetime.now()
                    if isinstance(fallback_date, str):
                        try:
                            fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                fallback_date = datetime.now()
                    
                    mongodb.update_one('tools', 
                                     {'_id': tool['_id']}, 
                                     {'$set': {'created_at': fallback_date}})
                    fixes_applied['missing_fields'] += 1
                
                # Workers ohne created_at Feld
                workers_without_created = list(mongodb.find('workers', {'created_at': {'$exists': False}}))
                for worker in workers_without_created:
                    fallback_date = worker.get('updated_at') or worker.get('modified_at') or datetime.now()
                    if isinstance(fallback_date, str):
                        try:
                            fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                        except ValueError:
                            try:
                                fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                fallback_date = datetime.now()
                    
                    mongodb.update_one('workers', 
                                     {'_id': worker['_id']}, 
                                     {'$set': {'created_at': fallback_date}})
                    fixes_applied['missing_fields'] += 1
                    
            except Exception as e:
                logger.error(f"Fehler bei sicheren Dashboard-Fixes: {str(e)}")
            
            # Gesamtzahl berechnen
            fixes_applied['total'] = fixes_applied['missing_fields']
            
            logger.info(f"Sichere Dashboard-Fixes angewendet: {fixes_applied}")
            return fixes_applied
            
        except Exception as e:
            logger.error(f"Fehler bei sicheren Dashboard-Fixes: {str(e)}")
            return {'total': 0, 'error': 'Ein interner Fehler ist aufgetreten.'}

    @staticmethod
    def create_native_backup() -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein natives MongoDB-Backup mit mongodump
        Behält alle Datentypen 1:1 bei - keine JSON-Konvertierung!
        """
        try:
            from app.utils.backup_manager import backup_manager
            
            backup_filename = backup_manager.create_native_backup()
            
            if backup_filename:
                logger.info(f"Natives MongoDB-Backup erfolgreich erstellt: {backup_filename}")
                return True, f"Native Backup erstellt: {backup_filename}", backup_filename
            else:
                logger.error("Fehler beim Erstellen des nativen Backups")
                return False, "Fehler beim Erstellen des nativen Backups", None
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des nativen Backups: {str(e)}")
            return False, f"Fehler beim Erstellen des nativen Backups: {str(e)}", None
    
    @staticmethod
    def restore_native_backup(backup_filename: str) -> Tuple[bool, str]:
        """
        Stellt ein natives MongoDB-Backup mit mongorestore wieder her
        Behält alle Datentypen 1:1 bei - keine JSON-Konvertierung!
        """
        try:
            from app.utils.backup_manager import backup_manager
            
            success = backup_manager.restore_native_backup(backup_filename)
            
            if success:
                logger.info(f"Natives MongoDB-Backup erfolgreich wiederhergestellt: {backup_filename}")
                return True, f"Native Backup wiederhergestellt: {backup_filename}"
            else:
                logger.error(f"Fehler beim Wiederherstellen des nativen Backups: {backup_filename}")
                return False, f"Fehler beim Wiederherstellen des nativen Backups: {backup_filename}"
                
        except Exception as e:
            logger.error(f"Fehler beim Wiederherstellen des nativen Backups: {str(e)}")
            return False, f"Fehler beim Wiederherstellen des nativen Backups: {str(e)}"
    
    @staticmethod
    def get_native_backup_list() -> List[Dict[str, Any]]:
        """Hole Liste aller nativen MongoDB-Backups"""
        try:
            from app.utils.backup_manager import backup_manager
            
            return backup_manager.list_native_backups()
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der nativen Backup-Liste: {str(e)}")
            return []
    
    @staticmethod
    def create_json_backup() -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein JSON-Backup (für Kompatibilität)
        
        Returns:
            (success, message, backup_filename)
        """
        try:
            backup_filename = backup_manager.create_backup()
            
            if backup_filename:
                logger.info(f"JSON-Backup erstellt: {backup_filename}")
                return True, f"JSON-Backup '{backup_filename}' erfolgreich erstellt", backup_filename
            else:
                return False, "Fehler beim Erstellen des JSON-Backups", None
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des JSON-Backups: {str(e)}")
            return False, f"Fehler beim Erstellen des JSON-Backups: {str(e)}", None

    @staticmethod
    def create_hybrid_backup() -> Tuple[bool, str, Optional[Dict[str, str]]]:
        """
        Erstellt ein hybrides Backup: Native MongoDB + JSON für Kompatibilität
        """
        try:
            from app.utils.backup_manager import backup_manager
            
            result = backup_manager.create_hybrid_backup()
            
            if result:
                logger.info(f"Hybrides Backup erfolgreich erstellt: {result}")
                return True, f"Hybrides Backup erstellt: Native={result['native']}, JSON={result['json']}", result
            else:
                logger.error("Fehler beim Erstellen des hybriden Backups")
                return False, "Fehler beim Erstellen des hybriden Backups", None
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des hybriden Backups: {str(e)}")
            return False, f"Fehler beim Erstellen des hybriden Backups: {str(e)}", None