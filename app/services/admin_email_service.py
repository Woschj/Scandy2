"""
Admin Email Service

Dieser Service enthält alle Funktionen für die E-Mail-Verwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from app.models.mongodb_database import mongodb
from app.utils.email_utils import send_email

logger = logging.getLogger(__name__)

class AdminEmailService:
    """Service für Admin-E-Mail-Funktionen"""
    
    @staticmethod
    def get_email_settings() -> Dict[str, Any]:
        """Hole alle E-Mail-Einstellungen"""
        try:
            settings = {}
            rows = mongodb.find('settings', {})
            
            for row in rows:
                if row['key'].startswith('email_'):
                    settings[row['key']] = row['value']
            
            return settings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der E-Mail-Einstellungen: [Interner Fehler]")
            return {}

    @staticmethod
    def update_email_settings(settings_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert E-Mail-Einstellungen
        
        Args:
            settings_data: Neue E-Mail-Einstellungen
            
        Returns:
            (success, message)
        """
        try:
            for key, value in settings_data.items():
                if key.startswith('email_'):
                    mongodb.update_one('settings', 
                                     {'key': key}, 
                                     {'$set': {'value': value}}, 
                                     upsert=True)
            
            logger.info("E-Mail-Einstellungen aktualisiert")
            return True, "E-Mail-Einstellungen erfolgreich gespeichert"
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der E-Mail-Einstellungen: [Interner Fehler]")
            return False, f"Fehler beim Speichern der E-Mail-Einstellungen: [Interner Fehler]"

    @staticmethod
    def test_email_configuration() -> Tuple[bool, str]:
        """
        Testet die E-Mail-Konfiguration
        
        Returns:
            (success, message)
        """
        try:
            # Hole E-Mail-Konfiguration aus dem neuen System
            config = AdminEmailService.get_email_config()
            
            if not config:
                return False, "Keine E-Mail-Konfiguration gefunden"
            
            # Prüfe ob alle erforderlichen Einstellungen vorhanden sind
            required_settings = ['mail_server', 'mail_port', 'mail_username', 'mail_password']
            missing_settings = []
            
            for setting in required_settings:
                if setting not in config or not config[setting]:
                    missing_settings.append(setting.replace('mail_', ''))
            
            if missing_settings:
                return False, f"Fehlende E-Mail-Einstellungen: {', '.join(missing_settings)}"
            
            # Teste E-Mail-Versand
            test_subject = "Scandy - E-Mail-Test"
            test_message = f"""
            Dies ist eine Test-E-Mail von Scandy.
            
            Gesendet am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
            
            Wenn Sie diese E-Mail erhalten, ist die E-Mail-Konfiguration korrekt.
            """
            
            # Sende Test-E-Mail an Admin
            admin_users = list(mongodb.find('users', {'role': 'admin'}))
            
            if not admin_users:
                return False, "Keine Admin-Benutzer gefunden"
            
            admin_email = admin_users[0].get('email')
            if not admin_email:
                return False, "Admin-Benutzer hat keine E-Mail-Adresse"
            
            success = send_email(
                to_email=admin_email,
                subject=test_subject,
                html_content=test_message,
                text_content=test_message
            )
            
            if success:
                logger.info("E-Mail-Konfiguration erfolgreich getestet")
                return True, f"Test-E-Mail erfolgreich an {admin_email} gesendet"
            else:
                return False, "Fehler beim Senden der Test-E-Mail"
                
        except Exception as e:
            logger.error(f"Fehler beim Testen der E-Mail-Konfiguration: [Interner Fehler]")
            return False, f"Fehler beim Testen der E-Mail-Konfiguration: [Interner Fehler]"

    @staticmethod
    def send_notification_email(recipient_email: str, subject: str, message: str) -> Tuple[bool, str]:
        """
        Sendet eine Benachrichtigungs-E-Mail
        
        Args:
            recipient_email: E-Mail-Adresse des Empfängers
            subject: Betreff der E-Mail
            message: Nachrichtentext
            
        Returns:
            (success, message)
        """
        try:
            success = send_email(
                to_email=recipient_email,
                subject=subject,
                html_content=message,
                text_content=message
            )
            
            if success:
                logger.info(f"Benachrichtigungs-E-Mail gesendet an: {recipient_email}")
                return True, f"E-Mail erfolgreich an {recipient_email} gesendet"
            else:
                return False, "Fehler beim Senden der E-Mail"
                
        except Exception as e:
            logger.error(f"Fehler beim Senden der Benachrichtigungs-E-Mail: [Interner Fehler]")
            return False, f"Fehler beim Senden der E-Mail: [Interner Fehler]"

    @staticmethod
    def send_low_stock_notification(consumable_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Sendet eine Niedrigbestand-Benachrichtigung
        
        Args:
            consumable_data: Verbrauchsmaterial-Daten
            
        Returns:
            (success, message)
        """
        try:
            # Hole Admin-Benutzer
            admin_users = list(mongodb.find('users', {'role': 'admin'}))
            
            if not admin_users:
                return False, "Keine Admin-Benutzer für Benachrichtigung gefunden"
            
            # Erstelle E-Mail-Nachricht
            subject = f"Scandy - Niedrigbestand: {consumable_data.get('name', 'Unbekannt')}"
            message = f"""
            Niedrigbestand-Warnung
            
            Verbrauchsmaterial: {consumable_data.get('name', 'Unbekannt')}
            Barcode: {consumable_data.get('barcode', 'Unbekannt')}
            Aktueller Bestand: {consumable_data.get('quantity', 0)}
            Mindestbestand: {consumable_data.get('min_quantity', 0)}
            
            Bitte bestellen Sie das Verbrauchsmaterial nach.
            
            Gesendet am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
            """
            
            # Sende E-Mail an alle Admins
            success_count = 0
            total_count = 0
            
            for admin in admin_users:
                admin_email = admin.get('email')
                if admin_email:
                    total_count += 1
                    success, _ = AdminEmailService.send_notification_email(
                        admin_email, subject, message
                    )
                    if success:
                        success_count += 1
            
            if success_count > 0:
                logger.info(f"Niedrigbestand-Benachrichtigung gesendet: {success_count}/{total_count} erfolgreich")
                return True, f"Niedrigbestand-Benachrichtigung an {success_count}/{total_count} Admins gesendet"
            else:
                return False, "Keine E-Mails erfolgreich gesendet"
                
        except Exception as e:
            logger.error(f"Fehler beim Senden der Niedrigbestand-Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Senden der Niedrigbestand-Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def send_overdue_notification(lending_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Sendet eine Überfälligkeits-Benachrichtigung
        
        Args:
            lending_data: Ausleih-Daten
            
        Returns:
            (success, message)
        """
        try:
            # Hole Werkzeug und Mitarbeiter
            tool = mongodb.find_one('tools', {'barcode': lending_data.get('tool_barcode')})
            worker = mongodb.find_one('workers', {'barcode': lending_data.get('worker_barcode')})
            
            if not tool or not worker:
                return False, "Werkzeug oder Mitarbeiter nicht gefunden"
            
            # Erstelle E-Mail-Nachricht
            subject = f"Scandy - Überfällige Ausleihe: {tool.get('name', 'Unbekannt')}"
            message = f"""
            Überfällige Ausleihe
            
            Werkzeug: {tool.get('name', 'Unbekannt')}
            Barcode: {tool.get('barcode', 'Unbekannt')}
            Mitarbeiter: {worker.get('firstname', '')} {worker.get('lastname', '')}
            Ausgeliehen am: {lending_data.get('lent_at', 'Unbekannt')}
            
            Das Werkzeug ist überfällig und sollte zurückgegeben werden.
            
            Gesendet am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
            """
            
            # Sende E-Mail an Admin
            admin_users = list(mongodb.find('users', {'role': 'admin'}))
            
            if not admin_users:
                return False, "Keine Admin-Benutzer für Benachrichtigung gefunden"
            
            success_count = 0
            total_count = 0
            
            for admin in admin_users:
                admin_email = admin.get('email')
                if admin_email:
                    total_count += 1
                    success, _ = AdminEmailService.send_notification_email(
                        admin_email, subject, message
                    )
                    if success:
                        success_count += 1
            
            if success_count > 0:
                logger.info(f"Überfälligkeits-Benachrichtigung gesendet: {success_count}/{total_count} erfolgreich")
                return True, f"Überfälligkeits-Benachrichtigung an {success_count}/{total_count} Admins gesendet"
            else:
                return False, "Keine E-Mails erfolgreich gesendet"
                
        except Exception as e:
            logger.error(f"Fehler beim Senden der Überfälligkeits-Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Senden der Überfälligkeits-Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def get_email_statistics() -> Dict[str, Any]:
        """Hole E-Mail-Statistiken"""
        try:
            # Zähle E-Mail-Einstellungen aus dem neuen System
            email_config = AdminEmailService.get_email_config()
            
            # Prüfe ob E-Mail konfiguriert ist
            smtp_configured = all([
                'mail_server' in email_config and email_config['mail_server'],
                'mail_port' in email_config and email_config['mail_port'],
                'mail_username' in email_config and email_config['mail_username'],
                'mail_password' in email_config and email_config['mail_password']
            ])
            
            # Zähle Benutzer mit E-Mail-Adressen
            users_with_email = mongodb.count_documents('users', {'email': {'$ne': ''}})
            total_users = mongodb.count_documents('users', {})
            
            return {
                'email_configured': smtp_configured,
                'users_with_email': users_with_email,
                'total_users': total_users,
                'email_percentage': round((users_with_email / total_users * 100), 1) if total_users > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der E-Mail-Statistiken: [Interner Fehler]")
            return {
                'email_configured': False,
                'users_with_email': 0,
                'total_users': 0,
                'email_percentage': 0
            } 

    @staticmethod
    def get_email_config() -> Dict[str, Any]:
        """
        Gibt die aktuelle E-Mail-Konfiguration zurück
        
        Returns:
            Dictionary mit E-Mail-Konfiguration
        """
        try:
            from app.utils.email_utils import get_email_config as get_config
            
            # Verwende die get_email_config aus email_utils
            config = get_config()
            
            if config:
                return config
            else:
                # Fallback-Konfiguration
                return {
                    'mail_server': 'smtp.gmail.com',
                    'mail_port': 587,
                    'mail_use_tls': True,
                    'mail_username': '',
                    'mail_password': '',
                    'test_email': '',
                    'use_auth': True
                }
                
        except Exception as e:
            logger.error(f"Fehler beim Laden der E-Mail-Konfiguration: [Interner Fehler]")
            return {
                'mail_server': 'smtp.gmail.com',
                'mail_port': 587,
                'mail_use_tls': True,
                'mail_username': '',
                'mail_password': '',
                'test_email': '',
                'use_auth': True
            }

    @staticmethod
    def save_email_config(config_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Speichert die E-Mail-Konfiguration
        
        Args:
            config_data: E-Mail-Konfiguration
            
        Returns:
            (success, message)
        """
        try:
            from app.utils.email_utils import save_email_config as save_config
            
            # Verwende die save_email_config aus email_utils
            success = save_config(config_data)
            
            if success:
                return True, "E-Mail-Konfiguration erfolgreich gespeichert"
            else:
                return False, "Fehler beim Speichern der E-Mail-Konfiguration"
                
        except Exception as e:
            logger.error(f"Fehler beim Speichern der E-Mail-Konfiguration: [Interner Fehler]")
            return False, f"Fehler beim Speichern der E-Mail-Konfiguration: [Interner Fehler]"

    @staticmethod
    def test_email_config(config_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Testet die E-Mail-Konfiguration
        
        Args:
            config_data: E-Mail-Konfiguration zum Testen
            
        Returns:
            (success, message)
        """
        try:
            from app.utils.email_utils import test_email_config as test_config
            
            # Verwende die test_email_config aus email_utils
            success, message = test_config(config_data)
            
            return success, message
            
        except Exception as e:
            logger.error(f"Fehler beim Testen der E-Mail-Konfiguration: [Interner Fehler]")
            return False, f"Fehler beim Testen der E-Mail-Konfiguration: [Interner Fehler]"

    @staticmethod
    def diagnose_smtp_connection(config_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Diagnostiziert die SMTP-Verbindung
        
        Args:
            config_data: E-Mail-Konfiguration
            
        Returns:
            (success, result)
        """
        try:
            from app.utils.email_utils import diagnose_smtp_connection as diagnose_smtp
            
            # Verwende die diagnose_smtp_connection aus email_utils
            result = diagnose_smtp(config_data)
            
            if result.get('success'):
                return True, result
            else:
                return False, result.get('error', 'Unbekannter Fehler')
                
        except Exception as e:
            logger.error(f"Fehler bei SMTP-Diagnose: [Interner Fehler]")
            return False, f"Diagnose-Fehler: [Interner Fehler]"