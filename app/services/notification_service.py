"""
Zentraler Notification Service für Scandy
Alle Benachrichtigungs-Funktionalitäten an einem Ort
"""
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime
from flask import current_app
from app.models.mongodb_database import mongodb
from app.services.email_service import EmailService
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Zentraler Service für alle Benachrichtigungen"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    def create_notice(self, title: str, message: str, priority: int = 1, is_active: bool = True) -> Tuple[bool, str]:
        """
        Erstellt eine neue Benachrichtigung
        
        Args:
            title: Titel der Benachrichtigung
            message: Nachricht
            priority: Priorität (1=hoch, 2=mittel, 3=niedrig)
            is_active: Ob die Benachrichtigung aktiv ist
            
        Returns:
            Tuple: (success, message)
        """
        try:
            notice_data = {
                'title': title,
                'message': message,
                'priority': priority,
                'is_active': is_active,
                'created_at': datetime.now(),
                'created_by': 'system'  # Könnte später erweitert werden
            }
            
            mongodb.insert_one('homepage_notices', notice_data)
            logger.info(f"Benachrichtigung erstellt: {title}")
            return True, "Benachrichtigung erfolgreich erstellt"
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Benachrichtigung: {str(e)}")
            return False, f"Fehler beim Erstellen: {str(e)}"
    
    def get_active_notices(self) -> List[Dict[str, Any]]:
        """
        Holt alle aktiven Benachrichtigungen
        
        Returns:
            List: Liste der aktiven Benachrichtigungen
        """
        try:
            notices = mongodb.find('homepage_notices', {'is_active': True})
            # Sortiere nach Priorität und Erstellungsdatum
            notices.sort(key=lambda x: (x.get('priority', 0), x.get('created_at', datetime.min)), reverse=True)
            return notices
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungen: {str(e)}")
            return []
    
    def update_notice(self, notice_id: str, **kwargs) -> Tuple[bool, str]:
        """
        Aktualisiert eine Benachrichtigung
        
        Args:
            notice_id: ID der Benachrichtigung
            **kwargs: Zu aktualisierende Felder
            
        Returns:
            Tuple: (success, message)
        """
        try:
            update_data = {
                'updated_at': datetime.now(),
                **kwargs
            }
            
            mongodb.update_one('homepage_notices', 
                             {'_id': notice_id}, 
                             {'$set': update_data})
            
            logger.info(f"Benachrichtigung aktualisiert: {notice_id}")
            return True, "Benachrichtigung erfolgreich aktualisiert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Benachrichtigung: {str(e)}")
            return False, f"Fehler beim Aktualisieren: {str(e)}"
    
    def delete_notice(self, notice_id: str) -> Tuple[bool, str]:
        """
        Löscht eine Benachrichtigung
        
        Args:
            notice_id: ID der Benachrichtigung
            
        Returns:
            Tuple: (success, message)
        """
        try:
            mongodb.delete_one('homepage_notices', {'_id': notice_id})
            logger.info(f"Benachrichtigung gelöscht: {notice_id}")
            return True, "Benachrichtigung erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Benachrichtigung: {str(e)}")
            return False, f"Fehler beim Löschen: {str(e)}"
    
    def send_system_notification(self, user_email: str, subject: str, message: str, notification_type: str = "info") -> bool:
        """
        Sendet eine System-Benachrichtigung per E-Mail
        
        Args:
            user_email: E-Mail-Adresse des Empfängers
            subject: Betreff
            message: Nachricht
            notification_type: Typ der Benachrichtigung
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            return self.email_service.send_notification_email(user_email, subject, message, notification_type)
            
        except Exception as e:
            logger.error(f"Fehler beim Senden der System-Benachrichtigung: {str(e)}")
            return False
    
    def notify_ticket_assignment(self, ticket_data: Dict[str, Any], assigned_user_email: str) -> bool:
        """
        Benachrichtigt einen Benutzer über eine Ticket-Zuweisung
        
        Args:
            ticket_data: Ticket-Daten
            assigned_user_email: E-Mail-Adresse des zugewiesenen Benutzers
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            return self.email_service.send_ticket_notification_email(
                assigned_user_email, 
                ticket_data, 
                "assigned"
            )
            
        except Exception as e:
            logger.error(f"Fehler bei Ticket-Zuweisungs-Benachrichtigung: {str(e)}")
            return False
    
    def notify_ticket_update(self, ticket_data: Dict[str, Any], user_email: str) -> bool:
        """
        Benachrichtigt einen Benutzer über eine Ticket-Aktualisierung
        
        Args:
            ticket_data: Ticket-Daten
            user_email: E-Mail-Adresse des Benutzers
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            return self.email_service.send_ticket_notification_email(
                user_email, 
                ticket_data, 
                "updated"
            )
            
        except Exception as e:
            logger.error(f"Fehler bei Ticket-Update-Benachrichtigung: {str(e)}")
            return False
    
    def notify_lending_action(self, lending_data: Dict[str, Any], user_email: str, action: str) -> bool:
        """
        Benachrichtigt einen Benutzer über eine Ausleihe-Aktion
        
        Args:
            lending_data: Ausleihe-Daten
            user_email: E-Mail-Adresse des Benutzers
            action: Aktion (lent, returned, overdue)
            
        Returns:
            bool: True wenn erfolgreich gesendet
        """
        try:
            return self.email_service.send_lending_notification_email(
                user_email, 
                lending_data, 
                action
            )
            
        except Exception as e:
            logger.error(f"Fehler bei Ausleihe-Benachrichtigung: {str(e)}")
            return False
    
    def create_system_alert(self, title: str, message: str, alert_type: str = "warning") -> Tuple[bool, str]:
        """
        Erstellt eine System-Warnung
        
        Args:
            title: Titel der Warnung
            message: Nachricht
            alert_type: Typ der Warnung (info, warning, error)
            
        Returns:
            Tuple: (success, message)
        """
        try:
            # Erstelle eine Benachrichtigung mit hoher Priorität
            priority = 1 if alert_type == "error" else 2 if alert_type == "warning" else 3
            
            return self.create_notice(
                title=f"[{alert_type.upper()}] {title}",
                message=message,
                priority=priority,
                is_active=True
            )
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der System-Warnung: {str(e)}")
            return False, f"Fehler beim Erstellen: {str(e)}"
    
    def check_and_notify_low_stock(self, consumable_data: Dict[str, Any]) -> bool:
        """
        Prüft ob ein Verbrauchsmaterial niedrige Bestände hat und erstellt eine Benachrichtigung
        
        Args:
            consumable_data: Verbrauchsmaterial-Daten
            
        Returns:
            bool: True wenn Benachrichtigung erstellt wurde
        """
        try:
            current_quantity = consumable_data.get('quantity', 0)
            min_quantity = consumable_data.get('min_quantity', 0)
            name = consumable_data.get('name', 'Unbekannt')
            
            if current_quantity <= min_quantity:
                title = "Niedriger Bestand"
                message = f"Das Verbrauchsmaterial '{name}' hat einen niedrigen Bestand. Aktuell: {current_quantity}, Minimum: {min_quantity}"
                
                success, _ = self.create_system_alert(title, message, "warning")
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Fehler bei der Bestandsprüfung: {str(e)}")
            return False
    
    def check_and_notify_overdue_tools(self) -> int:
        """
        Prüft auf überfällige Werkzeuge und erstellt Benachrichtigungen
        
        Returns:
            int: Anzahl der erstellten Benachrichtigungen
        """
        try:
            from datetime import timedelta
            
            # Werkzeuge die länger als 30 Tage ausgeliehen sind
            overdue_date = datetime.now() - timedelta(days=30)
            
            overdue_lendings = mongodb.find('lendings', {
                'returned_at': None,
                'lent_at': {'$lt': overdue_date}
            })
            
            notification_count = 0
            
            for lending in overdue_lendings:
                try:
                    tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
                    worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
                    
                    if tool and worker:
                        title = "Überfälliges Werkzeug"
                        message = f"Das Werkzeug '{tool.get('name', '')}' ist seit über 30 Tagen an {worker.get('firstname', '')} {worker.get('lastname', '')} ausgeliehen."
                        
                        success, _ = self.create_system_alert(title, message, "warning")
                        if success:
                            notification_count += 1
                            
                except Exception as e:
                    logger.error(f"Fehler bei der Überfälligkeitsprüfung: {str(e)}")
                    continue
            
            return notification_count
            
        except Exception as e:
            logger.error(f"Fehler bei der Überfälligkeitsprüfung: {str(e)}")
            return 0
    
    def get_notification_settings(self) -> Dict[str, Any]:
        """
        Holt die Benachrichtigungseinstellungen
        
        Returns:
            Dict: Benachrichtigungseinstellungen
        """
        try:
            settings = mongodb.find_one('settings', {'key': 'notification_settings'})
            if settings:
                return settings.get('value', {})
            else:
                # Standard-Einstellungen
                default_settings = {
                    'email_notifications': True,
                    'low_stock_alerts': True,
                    'overdue_tool_alerts': True,
                    'ticket_notifications': True,
                    'lending_notifications': False
                }
                return default_settings
                
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungseinstellungen: {str(e)}")
            return {}
    
    def update_notification_settings(self, settings: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert die Benachrichtigungseinstellungen
        
        Args:
            settings: Neue Einstellungen
            
        Returns:
            Tuple: (success, message)
        """
        try:
            mongodb.update_one('settings', 
                             {'key': 'notification_settings'}, 
                             {'$set': {'value': settings}}, 
                             upsert=True)
            
            logger.info("Benachrichtigungseinstellungen aktualisiert")
            return True, "Einstellungen erfolgreich aktualisiert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Benachrichtigungseinstellungen: {str(e)}")
            return False, f"Fehler beim Aktualisieren: {str(e)}"