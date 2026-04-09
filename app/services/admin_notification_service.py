"""
Admin Notification Service

Dieser Service enthält alle Funktionen für die Benachrichtigungsverwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.models.mongodb_database import mongodb
from app.services.admin_email_service import AdminEmailService

logger = logging.getLogger(__name__)

class AdminNotificationService:
    """Service für Admin-Benachrichtigungs-Funktionen"""
    
    @staticmethod
    def get_notifications() -> List[Dict[str, Any]]:
        """Hole alle Benachrichtigungen"""
        try:
            notifications = list(mongodb.find('notifications', {}, sort=[('created_at', -1)]))
            
            # Konvertiere ObjectIds zu Strings für JSON-Serialisierung
            for notification in notifications:
                if '_id' in notification:
                    notification['_id'] = str(notification['_id'])
            
            return notifications
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungen: [Interner Fehler]")
            return []

    @staticmethod
    def get_active_notices(department: Optional[str] = None) -> List[Dict[str, Any]]:
        """Hole alle aktiven Benachrichtigungen (Notices) (Bolt ⚡)"""
        try:
            query = {'is_active': True}
            if department:
                query['department'] = department

            # Sortiere nach Priorität (absteigend) und Erstellungsdatum (absteigend)
            notices = list(mongodb.find('homepage_notices', query, sort=[('priority', -1), ('created_at', -1)]))

            # Konvertiere ObjectIds zu Strings für JSON-Serialisierung
            for notice in notices:
                if '_id' in notice:
                    notice['_id'] = str(notice['_id'])

            return notices

        except Exception as e:
            logger.error(f"Fehler beim Laden der aktiven Benachrichtigungen: [Interner Fehler]")
            return []

    @staticmethod
    def create_notification(notification_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt eine neue Benachrichtigung
        
        Args:
            notification_data: Benachrichtigungsdaten
            
        Returns:
            (success, message, notification_id)
        """
        try:
            # Validierung
            required_fields = ['title', 'message', 'type']
            for field in required_fields:
                if field not in notification_data or not notification_data[field]:
                    return False, f"Feld '{field}' ist erforderlich", None
            
            # Benachrichtigung erstellen
            new_notification = {
                'title': notification_data['title'],
                'message': notification_data['message'],
                'type': notification_data['type'],
                'priority': notification_data.get('priority', 'normal'),
                'is_read': False,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Benachrichtigung in Datenbank speichern
            notification_id = mongodb.insert_one('notifications', new_notification)
            
            logger.info(f"Neue Benachrichtigung erstellt: {notification_data['title']} (ID: {notification_id})")
            return True, f"Benachrichtigung '{notification_data['title']}' erfolgreich erstellt", notification_id
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Erstellen der Benachrichtigung: [Interner Fehler]", None

    @staticmethod
    def mark_notification_as_read(notification_id: str) -> Tuple[bool, str]:
        """
        Markiert eine Benachrichtigung als gelesen
        
        Args:
            notification_id: ID der Benachrichtigung
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benachrichtigung existiert
            notification = mongodb.find_one('notifications', {'_id': notification_id})
            if not notification:
                return False, "Benachrichtigung nicht gefunden"
            
            # Markiere als gelesen
            mongodb.update_one('notifications', {'_id': notification_id}, {
                '$set': {
                    'is_read': True,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Benachrichtigung als gelesen markiert: {notification.get('title', 'Unknown')} (ID: {notification_id})")
            return True, f"Benachrichtigung als gelesen markiert"
            
        except Exception as e:
            logger.error(f"Fehler beim Markieren der Benachrichtigung {notification_id}: [Interner Fehler]")
            return False, f"Fehler beim Markieren der Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def delete_notification(notification_id: str) -> Tuple[bool, str]:
        """
        Löscht eine Benachrichtigung
        
        Args:
            notification_id: ID der zu löschenden Benachrichtigung
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benachrichtigung existiert
            notification = mongodb.find_one('notifications', {'_id': notification_id})
            if not notification:
                return False, "Benachrichtigung nicht gefunden"
            
            # Benachrichtigung löschen
            mongodb.delete_one('notifications', {'_id': notification_id})
            
            logger.info(f"Benachrichtigung gelöscht: {notification.get('title', 'Unknown')} (ID: {notification_id})")
            return True, f"Benachrichtigung '{notification.get('title', 'Unknown')}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Benachrichtigung {notification_id}: [Interner Fehler]")
            return False, f"Fehler beim Löschen der Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def get_unread_notifications() -> List[Dict[str, Any]]:
        """Hole alle ungelesenen Benachrichtigungen"""
        try:
            notifications = list(mongodb.find('notifications', {'is_read': False}, sort=[('created_at', -1)]))
            
            # Konvertiere ObjectIds zu Strings für JSON-Serialisierung
            for notification in notifications:
                if '_id' in notification:
                    notification['_id'] = str(notification['_id'])
            
            return notifications
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der ungelesenen Benachrichtigungen: [Interner Fehler]")
            return []

    @staticmethod
    def get_notification_count() -> Dict[str, int]:
        """Hole Anzahl der Benachrichtigungen (Bolt ⚡)"""
        try:
            # OPTIMIERT: Verwende Aggregation zur Reduzierung von Datenbank-Abfragen
            pipeline = [
                {
                    '$facet': {
                        'total': [{'$count': 'count'}],
                        'unread': [
                            {'$match': {'is_read': False}},
                            {'$count': 'count'}
                        ]
                    }
                }
            ]

            result = list(mongodb.aggregate('notifications', pipeline))

            if not result:
                return {'total': 0, 'unread': 0, 'read': 0}

            facet_result = result[0]
            total_count = facet_result['total'][0]['count'] if facet_result['total'] else 0
            unread_count = facet_result['unread'][0]['count'] if facet_result['unread'] else 0
            
            return {
                'total': total_count,
                'unread': unread_count,
                'read': total_count - unread_count
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungsanzahl: [Interner Fehler]")
            return {'total': 0, 'unread': 0, 'read': 0}

    @staticmethod
    def create_system_notification(title: str, message: str, notification_type: str = 'info', priority: str = 'normal') -> Tuple[bool, str]:
        """
        Erstellt eine System-Benachrichtigung
        
        Args:
            title: Titel der Benachrichtigung
            message: Nachrichtentext
            notification_type: Typ der Benachrichtigung (info, warning, error, success)
            priority: Priorität (low, normal, high, urgent)
            
        Returns:
            (success, message)
        """
        try:
            success, message, _ = AdminNotificationService.create_notification({
                'title': title,
                'message': message,
                'type': notification_type,
                'priority': priority
            })
            
            return success, message
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der System-Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Erstellen der System-Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def create_low_stock_notification(consumable_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Erstellt eine Niedrigbestand-Benachrichtigung
        
        Args:
            consumable_data: Verbrauchsmaterial-Daten
            
        Returns:
            (success, message)
        """
        try:
            title = f"Niedrigbestand: {consumable_data.get('name', 'Unbekannt')}"
            message = f"""
            Das Verbrauchsmaterial "{consumable_data.get('name', 'Unbekannt')}" hat einen niedrigen Bestand.
            
            Aktueller Bestand: {consumable_data.get('quantity', 0)}
            Mindestbestand: {consumable_data.get('min_quantity', 0)}
            Barcode: {consumable_data.get('barcode', 'Unbekannt')}
            
            Bitte bestellen Sie das Verbrauchsmaterial nach.
            """
            
            # Erstelle Benachrichtigung
            success, msg = AdminNotificationService.create_system_notification(
                title=title,
                message=message,
                notification_type='warning',
                priority='high'
            )
            
            # Sende auch E-Mail-Benachrichtigung
            email_success, email_msg = AdminEmailService.send_low_stock_notification(consumable_data)
            
            if email_success:
                logger.info(f"Niedrigbestand-Benachrichtigung erstellt und E-Mail gesendet: {consumable_data.get('name', 'Unknown')}")
            else:
                logger.warning(f"Niedrigbestand-Benachrichtigung erstellt, aber E-Mail fehlgeschlagen: {email_msg}")
            
            return success, msg
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Niedrigbestand-Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Erstellen der Niedrigbestand-Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def create_overdue_notification(lending_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Erstellt eine Überfälligkeits-Benachrichtigung
        
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
            
            title = f"Überfällige Ausleihe: {tool.get('name', 'Unbekannt')}"
            message = f"""
            Das Werkzeug "{tool.get('name', 'Unbekannt')}" ist überfällig.
            
            Mitarbeiter: {worker.get('firstname', '')} {worker.get('lastname', '')}
            Ausgeliehen am: {lending_data.get('lent_at', 'Unbekannt')}
            Barcode: {tool.get('barcode', 'Unbekannt')}
            
            Das Werkzeug sollte zurückgegeben werden.
            """
            
            # Erstelle Benachrichtigung
            success, msg = AdminNotificationService.create_system_notification(
                title=title,
                message=message,
                notification_type='warning',
                priority='high'
            )
            
            # Sende auch E-Mail-Benachrichtigung
            email_success, email_msg = AdminEmailService.send_overdue_notification(lending_data)
            
            if email_success:
                logger.info(f"Überfälligkeits-Benachrichtigung erstellt und E-Mail gesendet: {tool.get('name', 'Unknown')}")
            else:
                logger.warning(f"Überfälligkeits-Benachrichtigung erstellt, aber E-Mail fehlgeschlagen: {email_msg}")
            
            return success, msg
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Überfälligkeits-Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Erstellen der Überfälligkeits-Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def clear_old_notifications(days: int = 30) -> Tuple[bool, str, int]:
        """
        Löscht alte Benachrichtigungen
        
        Args:
            days: Anzahl der Tage (Benachrichtigungen älter als X Tage werden gelöscht)
            
        Returns:
            (success, message, deleted_count)
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Zähle zu löschende Benachrichtigungen
            old_notifications = list(mongodb.find('notifications', {
                'created_at': {'$lt': cutoff_date}
            }))
            
            deleted_count = len(old_notifications)
            
            if deleted_count == 0:
                return True, f"Keine Benachrichtigungen älter als {days} Tage gefunden", 0
            
            # Lösche alte Benachrichtigungen
            mongodb.delete_many('notifications', {
                'created_at': {'$lt': cutoff_date}
            })
            
            logger.info(f"{deleted_count} alte Benachrichtigungen gelöscht (älter als {days} Tage)")
            return True, f"{deleted_count} alte Benachrichtigungen erfolgreich gelöscht", deleted_count
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen alter Benachrichtigungen: [Interner Fehler]")
            return False, f"Fehler beim Löschen alter Benachrichtigungen: [Interner Fehler]", 0

    @staticmethod
    def get_notification_statistics() -> Dict[str, Any]:
        """Hole Benachrichtigungs-Statistiken (Bolt ⚡)"""
        try:
            # OPTIMIERT: Verwende Aggregation mit Facets zur Reduzierung von Datenbank-Abfragen
            pipeline = [
                {
                    '$facet': {
                        'total': [{'$count': 'count'}],
                        'by_type': [
                            {'$group': {'_id': '$type', 'count': {'$sum': 1}}}
                        ],
                        'by_priority': [
                            {'$group': {'_id': '$priority', 'count': {'$sum': 1}}}
                        ],
                        'by_read': [
                            {'$group': {'_id': '$is_read', 'count': {'$sum': 1}}}
                        ]
                    }
                }
            ]
            
            result = list(mongodb.aggregate('notifications', pipeline))

            if not result:
                return {
                    'total_count': 0,
                    'type_stats': {},
                    'priority_stats': {},
                    'unread_count': 0,
                    'read_count': 0
                }
            
            facet_result = result[0]
            
            total_count = facet_result['total'][0]['count'] if facet_result['total'] else 0
            
            type_stats = {t['_id']: t['count'] for t in facet_result['by_type'] if t['_id']}
            # Ensure all expected types are present
            for n_type in ['info', 'warning', 'error', 'success']:
                if n_type not in type_stats:
                    type_stats[n_type] = 0

            priority_stats = {p['_id']: p['count'] for p in facet_result['by_priority'] if p['_id']}
            # Ensure all expected priorities are present
            for priority in ['low', 'normal', 'high', 'urgent']:
                if priority not in priority_stats:
                    priority_stats[priority] = 0
            
            unread_count = 0
            read_count = 0
            for r in facet_result['by_read']:
                if r['_id'] is False:
                    unread_count = r['count']
                elif r['_id'] is True:
                    read_count = r['count']
            
            return {
                'total_count': total_count,
                'type_stats': type_stats,
                'priority_stats': priority_stats,
                'unread_count': unread_count,
                'read_count': read_count
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungs-Statistiken: [Interner Fehler]")
            return {
                'total_count': 0,
                'type_stats': {},
                'priority_stats': {},
                'unread_count': 0,
                'read_count': 0
            }

    @staticmethod
    def get_all_notices(department: Optional[str] = None) -> List[Dict[str, Any]]:
        """Hole alle Benachrichtigungen (Notices)"""
        try:
            query = {}
            if department:
                query['department'] = department
            notices = list(mongodb.find('homepage_notices', query, sort=[('created_at', -1)]))
            
            # Konvertiere ObjectIds zu Strings für JSON-Serialisierung
            for notice in notices:
                if '_id' in notice:
                    notice['_id'] = str(notice['_id'])
            
            return notices
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungen: [Interner Fehler]")
            return []

    @staticmethod
    def create_notice(title: str, content: str, notice_type: str = 'info', department: Optional[str] = None, priority: int = 0, is_active: bool = True) -> Tuple[bool, str]:
        """
        Erstellt eine neue Benachrichtigung (Notice)
        
        Args:
            title: Titel der Benachrichtigung
            content: Inhalt der Benachrichtigung
            notice_type: Typ der Benachrichtigung
            
        Returns:
            (success, message)
        """
        try:
            notice_data = {
                'title': title,
                'message': content,
                'type': notice_type,
                'is_active': bool(is_active),
                'created_at': datetime.now(),
                'created_by': 'admin',  # Könnte später erweitert werden
                'department': department,
                'priority': int(priority) if priority is not None else 0
            }
            
            mongodb.insert_one('homepage_notices', notice_data)
            logger.info(f"Benachrichtigung erstellt: {title}")
            return True, "Benachrichtigung erfolgreich erstellt"
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Erstellen der Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def update_notice(notice_id: str, **kwargs) -> Tuple[bool, str]:
        """
        Aktualisiert eine Benachrichtigung (Notice)
        
        Args:
            notice_id: ID der Benachrichtigung
            **kwargs: Zu aktualisierende Felder (z.B. title, content, notice_type, department, priority, is_active)
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benachrichtigung existiert
            notice = mongodb.find_one('homepage_notices', {'_id': notice_id})
            if not notice:
                return False, "Benachrichtigung nicht gefunden"
            
            # Aktualisiere Benachrichtigung
            update_data = {'updated_at': datetime.now()}

            if 'title' in kwargs:
                update_data['title'] = kwargs['title']
            if 'content' in kwargs:
                update_data['message'] = kwargs['content']
            elif 'message' in kwargs:
                update_data['message'] = kwargs['message']

            if 'notice_type' in kwargs:
                update_data['type'] = kwargs['notice_type']
            elif 'type' in kwargs:
                update_data['type'] = kwargs['type']

            if 'department' in kwargs:
                update_data['department'] = kwargs['department']

            if 'priority' in kwargs and kwargs['priority'] is not None:
                update_data['priority'] = int(kwargs['priority'])

            if 'is_active' in kwargs and kwargs['is_active'] is not None:
                update_data['is_active'] = bool(kwargs['is_active'])
            
            mongodb.update_one('homepage_notices', {'_id': notice_id}, {'$set': update_data})
            
            log_title = kwargs.get('title', notice.get('title', 'Unbekannt'))
            logger.info(f"Benachrichtigung aktualisiert: {log_title}")
            return True, "Benachrichtigung erfolgreich aktualisiert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Benachrichtigung: [Interner Fehler]")
            return False, f"Fehler beim Aktualisieren der Benachrichtigung: [Interner Fehler]"

    @staticmethod
    def get_notice_by_id(notice_id: str) -> Optional[Dict[str, Any]]:
        """
        Hole eine Benachrichtigung anhand der ID
        
        Args:
            notice_id: ID der Benachrichtigung
            
        Returns:
            Benachrichtigung oder None
        """
        try:
            notice = mongodb.find_one('homepage_notices', {'_id': notice_id})
            if notice and '_id' in notice:
                notice['_id'] = str(notice['_id'])
            return notice
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigung {notice_id}: [Interner Fehler]")
            return None

    @staticmethod
    def delete_notice(notice_id: str) -> Tuple[bool, str]:
        """
        Löscht eine Benachrichtigung (Notice)
        
        Args:
            notice_id: ID der zu löschenden Benachrichtigung
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benachrichtigung existiert
            notice = mongodb.find_one('homepage_notices', {'_id': notice_id})
            if not notice:
                return False, "Benachrichtigung nicht gefunden"
            
            # Lösche Benachrichtigung
            mongodb.delete_one('homepage_notices', {'_id': notice_id})
            
            logger.info(f"Benachrichtigung gelöscht: {notice.get('title', 'Unknown')} (ID: {notice_id})")
            return True, f"Benachrichtigung '{notice.get('title', 'Unknown')}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Benachrichtigung {notice_id}: [Interner Fehler]")
            return False, f"Fehler beim Löschen der Benachrichtigung: [Interner Fehler]"