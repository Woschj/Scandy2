"""
Vereinheitlichter Notification Service

Dieser Service konsolidiert alle Benachrichtigungs- und E-Mail-Funktionen
aus verschiedenen Services für bessere Wartbarkeit und Konsistenz.

Konsolidiert aus:
- admin_email_service.py
- email_service.py
- notification_service.py
- admin_notification_service.py
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from flask import current_app, g
from app.models.mongodb_database import mongodb
from app.utils.email_utils import send_email
from app.utils.id_helpers import convert_id_for_query

logger = logging.getLogger(__name__)

class UnifiedNotificationService:
    """
    Vereinheitlichter Service für alle Benachrichtigungsfunktionen

    Dieser Service konsolidiert:
    - E-Mail-Benachrichtigungen
    - System-Benachrichtigungen
    - Admin-Benachrichtigungen
    - Template-Management
    """

    # === E-MAIL FUNKTIONEN (aus admin_email_service.py und email_service.py) ===

    @staticmethod
    def send_notification_email(recipient_email: str, subject: str, message: str) -> Tuple[bool, str]:
        """
        Sendet eine einfache Benachrichtigungs-E-Mail

        Args:
            recipient_email: Empfänger-E-Mail
            subject: Betreff
            message: Nachricht

        Returns:
            Tuple: (success, message)
        """
        try:
            success = send_email(recipient_email, subject, message)
            if success:
                logger.info(f"E-Mail-Benachrichtigung gesendet an {recipient_email}: {subject}")
                return True, "E-Mail erfolgreich gesendet"
            else:
                logger.error(f"Fehler beim Senden der E-Mail-Benachrichtigung an {recipient_email}")
                return False, "Fehler beim Senden der E-Mail"
        except Exception as e:
            logger.error(f"Fehler beim Senden der E-Mail-Benachrichtigung: {e}")
            return False, f"Fehler beim Senden: {str(e)}"

    @staticmethod
    def send_ticket_notification_email(user_email: str, ticket_data: Dict[str, Any], action: str) -> bool:
        """
        Sendet eine Ticket-Benachrichtigungs-E-Mail

        Args:
            user_email: Empfänger-E-Mail
            ticket_data: Ticket-Daten
            action: Aktion (created, updated, assigned, etc.)

        Returns:
            bool: Erfolg
        """
        try:
            ticket_number = ticket_data.get('ticket_number', 'N/A')
            ticket_title = ticket_data.get('title', 'Unbekannt')

            subject_map = {
                'created': f"Neues Ticket erstellt: #{ticket_number}",
                'updated': f"Ticket aktualisiert: #{ticket_number}",
                'assigned': f"Ticket zugewiesen: #{ticket_number}",
                'resolved': f"Ticket gelöst: #{ticket_number}",
                'closed': f"Ticket geschlossen: #{ticket_number}"
            }

            subject = subject_map.get(action, f"Ticket-Benachrichtigung: #{ticket_number}")

            message = f"""
            Ticket #{ticket_number}: {ticket_title}

            Aktion: {action.capitalize()}
            Status: {ticket_data.get('status', 'Unbekannt')}
            Priorität: {ticket_data.get('priority', 'Unbekannt')}

            Beschreibung: {ticket_data.get('description', 'Keine Beschreibung')}

            Diese E-Mail wurde automatisch generiert.
            """

            success = send_email(user_email, subject, message)
            if success:
                logger.info(f"Ticket-Benachrichtigung gesendet an {user_email} für Ticket #{ticket_number}")
            return success

        except Exception as e:
            logger.error(f"Fehler beim Senden der Ticket-Benachrichtigung: {e}")
            return False

    @staticmethod
    def send_lending_notification_email(user_email: str, lending_data: Dict[str, Any], action: str) -> bool:
        """
        Sendet eine Ausleih-Benachrichtigungs-E-Mail

        Args:
            user_email: Empfänger-E-Mail
            lending_data: Ausleih-Daten
            action: Aktion (lent, returned, overdue, etc.)

        Returns:
            bool: Erfolg
        """
        try:
            tool_name = lending_data.get('tool_name', 'Unbekannt')
            worker_name = lending_data.get('worker_name', 'Unbekannt')

            subject_map = {
                'lent': f"Werkzeug ausgeliehen: {tool_name}",
                'returned': f"Werkzeug zurückgegeben: {tool_name}",
                'overdue': f"Überfälliges Werkzeug: {tool_name}",
                'reminder': f"Erinnerung: Werkzeug zurückgeben - {tool_name}"
            }

            subject = subject_map.get(action, f"Ausleih-Benachrichtigung: {tool_name}")

            message = f"""
            Werkzeug: {tool_name}
            Mitarbeiter: {worker_name}
            Aktion: {action.capitalize()}

            Details:
            - Ausgeliehen am: {lending_data.get('lent_at', 'Unbekannt')}
            - Fällig am: {lending_data.get('due_date', 'Unbekannt')}

            Diese E-Mail wurde automatisch generiert.
            """

            success = send_email(user_email, subject, message)
            if success:
                logger.info(f"Ausleih-Benachrichtigung gesendet an {user_email} für {tool_name}")
            return success

        except Exception as e:
            logger.error(f"Fehler beim Senden der Ausleih-Benachrichtigung: {e}")
            return False

    @staticmethod
    def send_low_stock_notification(consumable_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Sendet eine Benachrichtigung bei niedrigem Lagerbestand

        Args:
            consumable_data: Verbrauchsmaterial-Daten

        Returns:
            Tuple: (success, message)
        """
        try:
            name = consumable_data.get('name', 'Unbekannt')
            current_quantity = consumable_data.get('quantity', 0)
            min_quantity = consumable_data.get('min_quantity', 0)

            subject = f"Niedriger Lagerbestand: {name}"
            message = f"""
            Warnung: Niedriger Lagerbestand

            Material: {name}
            Aktueller Bestand: {current_quantity}
            Mindestbestand: {min_quantity}

            Bitte den Bestand auffüllen.

            Diese E-Mail wurde automatisch generiert.
            """

            # Admin-E-Mail aus der Datenbank laden
            admin_email = "admin@scandy.local"  # Fallback
            try:
                settings = mongodb.find_one('settings', {'key': 'admin_email'})
                if settings:
                    admin_email = settings.get('value', admin_email)
            except Exception:
                pass

            success = send_email(admin_email, subject, message)
            if success:
                logger.info(f"Niedriger Lagerbestand Benachrichtigung gesendet für {name}")
                return True, "Benachrichtigung erfolgreich gesendet"
            else:
                return False, "Fehler beim Senden der Benachrichtigung"

        except Exception as e:
            logger.error(f"Fehler beim Senden der Lagerbestand-Benachrichtigung: {e}")
            return False, f"Fehler beim Senden: {str(e)}"

    @staticmethod
    def send_overdue_notification(lending_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Sendet eine Benachrichtigung bei überfälligen Ausleihen

        Args:
            lending_data: Ausleih-Daten

        Returns:
            Tuple: (success, message)
        """
        try:
            tool_name = lending_data.get('tool_name', 'Unbekannt')
            worker_name = lending_data.get('worker_name', 'Unbekannt')
            due_date = lending_data.get('due_date', 'Unbekannt')

            subject = f"Überfällige Ausleihe: {tool_name}"
            message = f"""
            Warnung: Überfällige Ausleihe

            Werkzeug: {tool_name}
            Mitarbeiter: {worker_name}
            Fällig seit: {due_date}

            Bitte das Werkzeug zurückfordern.

            Diese E-Mail wurde automatisch generiert.
            """

            # Admin-E-Mail aus der Datenbank laden
            admin_email = "admin@scandy.local"  # Fallback
            try:
                settings = mongodb.find_one('settings', {'key': 'admin_email'})
                if settings:
                    admin_email = settings.get('value', admin_email)
            except Exception:
                pass

            success = send_email(admin_email, subject, message)
            if success:
                logger.info(f"Überfällige Ausleihe Benachrichtigung gesendet für {tool_name}")
                return True, "Benachrichtigung erfolgreich gesendet"
            else:
                return False, "Fehler beim Senden der Benachrichtigung"

        except Exception as e:
            logger.error(f"Fehler beim Senden der Überfälligkeits-Benachrichtigung: {e}")
            return False, f"Fehler beim Senden: {str(e)}"

    # === SYSTEM-BENACHRICHTIGUNGEN (aus notification_service.py) ===

    @staticmethod
    def send_system_notification(user_email: str, subject: str, message: str, notification_type: str = "info") -> bool:
        """
        Sendet eine System-Benachrichtigung per E-Mail

        Args:
            user_email: Empfänger-E-Mail
            subject: Betreff
            message: Nachricht
            notification_type: Typ der Benachrichtigung (info, warning, error, success)

        Returns:
            bool: Erfolg
        """
        try:
            # E-Mail-Vorlage für System-Benachrichtigungen
            email_subject = f"Scandy - {subject}"

            email_message = f"""
            System-Benachrichtigung

            {message}

            Typ: {notification_type.upper()}
            Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            Diese E-Mail wurde automatisch vom Scandy-System generiert.
            """

            success = send_email(user_email, email_subject, email_message)
            if success:
                logger.info(f"System-Benachrichtigung gesendet an {user_email}: {subject}")
            return success

        except Exception as e:
            logger.error(f"Fehler beim Senden der System-Benachrichtigung: {e}")
            return False

    @staticmethod
    def get_notification_settings() -> Dict[str, Any]:
        """
        Holt die Benachrichtigungseinstellungen

        Returns:
            Dict mit Benachrichtigungseinstellungen
        """
        try:
            settings = mongodb.find_one('settings', {'key': 'notification_settings'})
            if settings:
                return settings.get('value', {})
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungseinstellungen: {e}")
            return {}

    @staticmethod
    def update_notification_settings(settings: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert die Benachrichtigungseinstellungen

        Args:
            settings: Neue Einstellungen

        Returns:
            Tuple: (success, message)
        """
        try:
            result = mongodb.update_one(
                'settings',
                {'key': 'notification_settings'},
                {'$set': {'value': settings, 'updated_at': datetime.now()}},
                upsert=True
            )

            if result:
                logger.info("Benachrichtigungseinstellungen aktualisiert")
                return True, "Einstellungen erfolgreich aktualisiert"
            else:
                return False, "Fehler beim Aktualisieren der Einstellungen"

        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Benachrichtigungseinstellungen: {e}")
            return False, f"Fehler beim Aktualisieren: {str(e)}"

    # === ADMIN-BENACHRICHTIGUNGEN (aus admin_notification_service.py) ===

    @staticmethod
    def get_notifications() -> List[Dict[str, Any]]:
        """
        Holt alle Benachrichtigungen

        Returns:
            Liste aller Benachrichtigungen
        """
        try:
            notifications = list(mongodb.find('notifications', {}).sort('created_at', -1))
            # ID zu String konvertieren für JSON-Serialisierung
            for notification in notifications:
                if '_id' in notification:
                    notification['_id'] = str(notification['_id'])
            return notifications
        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungen: {e}")
            return []

    @staticmethod
    def create_notification(notification_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt eine neue Benachrichtigung

        Args:
            notification_data: Benachrichtigungsdaten

        Returns:
            Tuple: (success, message, notification_id)
        """
        try:
            # Standardwerte setzen
            notification = {
                'title': notification_data.get('title', ''),
                'message': notification_data.get('message', ''),
                'type': notification_data.get('type', 'info'),
                'priority': notification_data.get('priority', 'normal'),
                'read': False,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            result = mongodb.insert_one('notifications', notification)
            notification_id = str(result)

            logger.info(f"Benachrichtigung erstellt: {notification_id}")
            return True, "Benachrichtigung erfolgreich erstellt", notification_id

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Benachrichtigung: {e}")
            return False, f"Fehler beim Erstellen: {str(e)}", None

    @staticmethod
    def mark_notification_as_read(notification_id: str) -> Tuple[bool, str]:
        """
        Markiert eine Benachrichtigung als gelesen

        Args:
            notification_id: ID der Benachrichtigung

        Returns:
            Tuple: (success, message)
        """
        try:
            result = mongodb.update_one(
                'notifications',
                {'_id': convert_id_for_query(notification_id)},
                {'$set': {'read': True, 'updated_at': datetime.now()}}
            )

            if result:
                logger.info(f"Benachrichtigung als gelesen markiert: {notification_id}")
                return True, "Benachrichtigung als gelesen markiert"
            else:
                return False, "Benachrichtigung nicht gefunden"

        except Exception as e:
            logger.error(f"Fehler beim Markieren der Benachrichtigung: {e}")
            return False, f"Fehler beim Markieren: {str(e)}"

    @staticmethod
    def delete_notification(notification_id: str) -> Tuple[bool, str]:
        """
        Löscht eine Benachrichtigung

        Args:
            notification_id: ID der Benachrichtigung

        Returns:
            Tuple: (success, message)
        """
        try:
            result = mongodb.delete_one('notifications', {'_id': convert_id_for_query(notification_id)})

            if result:
                logger.info(f"Benachrichtigung gelöscht: {notification_id}")
                return True, "Benachrichtigung erfolgreich gelöscht"
            else:
                return False, "Benachrichtigung nicht gefunden"

        except Exception as e:
            logger.error(f"Fehler beim Löschen der Benachrichtigung: {e}")
            return False, f"Fehler beim Löschen: {str(e)}"

    @staticmethod
    def get_unread_notifications() -> List[Dict[str, Any]]:
        """
        Holt alle ungelesenen Benachrichtigungen

        Returns:
            Liste der ungelesenen Benachrichtigungen
        """
        try:
            notifications = list(mongodb.find('notifications', {'read': False}).sort('created_at', -1))
            # ID zu String konvertieren für JSON-Serialisierung
            for notification in notifications:
                if '_id' in notification:
                    notification['_id'] = str(notification['_id'])
            return notifications
        except Exception as e:
            logger.error(f"Fehler beim Laden der ungelesenen Benachrichtigungen: {e}")
            return []

    @staticmethod
    def get_notification_count() -> Dict[str, int]:
        """
        Holt die Anzahl der Benachrichtigungen nach Typ

        Returns:
            Dict mit Anzahl pro Typ
        """
        try:
            total = mongodb.count_documents('notifications', {})
            unread = mongodb.count_documents('notifications', {'read': False})

            return {
                'total': total,
                'unread': unread,
                'read': total - unread
            }
        except Exception as e:
            logger.error(f"Fehler beim Zählen der Benachrichtigungen: {e}")
            return {'total': 0, 'unread': 0, 'read': 0}

    @staticmethod
    def create_system_notification(title: str, message: str, notification_type: str = 'info', priority: str = 'normal') -> Tuple[bool, str]:
        """
        Erstellt eine System-Benachrichtigung

        Args:
            title: Titel der Benachrichtigung
            message: Nachricht
            notification_type: Typ (info, warning, error, success)
            priority: Priorität (low, normal, high)

        Returns:
            Tuple: (success, message)
        """
        notification_data = {
            'title': title,
            'message': message,
            'type': notification_type,
            'priority': priority
        }

        success, message_text, _ = UnifiedNotificationService.create_notification(notification_data)

        if success:
            logger.info(f"System-Benachrichtigung erstellt: {title}")
        else:
            logger.error(f"Fehler beim Erstellen der System-Benachrichtigung: {message_text}")

        return success, message_text

    @staticmethod
    def create_low_stock_notification(consumable_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Erstellt eine Benachrichtigung bei niedrigem Lagerbestand

        Args:
            consumable_data: Verbrauchsmaterial-Daten

        Returns:
            Tuple: (success, message)
        """
        try:
            name = consumable_data.get('name', 'Unbekannt')
            quantity = consumable_data.get('quantity', 0)
            min_quantity = consumable_data.get('min_quantity', 0)

            title = f"Niedriger Lagerbestand: {name}"
            message = f"""
            Der Lagerbestand für '{name}' ist niedrig.

            Aktueller Bestand: {quantity}
            Mindestbestand: {min_quantity}

            Bitte den Bestand auffüllen.
            """

            return UnifiedNotificationService.create_system_notification(
                title=title,
                message=message,
                notification_type='warning',
                priority='normal'
            )

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Lagerbestand-Benachrichtigung: {e}")
            return False, f"Fehler beim Erstellen: {str(e)}"

    @staticmethod
    def create_overdue_notification(lending_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Erstellt eine Benachrichtigung bei überfälligen Ausleihen

        Args:
            lending_data: Ausleih-Daten

        Returns:
            Tuple: (success, message)
        """
        try:
            tool_name = lending_data.get('tool_name', 'Unbekannt')
            worker_name = lending_data.get('worker_name', 'Unbekannt')
            due_date = lending_data.get('due_date', 'Unbekannt')

            title = f"Überfällige Ausleihe: {tool_name}"
            message = f"""
            Die Ausleihe für '{tool_name}' ist überfällig.

            Mitarbeiter: {worker_name}
            Fällig seit: {due_date}

            Bitte das Werkzeug zurückfordern.
            """

            return UnifiedNotificationService.create_system_notification(
                title=title,
                message=message,
                notification_type='error',
                priority='high'
            )

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Überfälligkeits-Benachrichtigung: {e}")
            return False, f"Fehler beim Erstellen: {str(e)}"

    @staticmethod
    def clear_old_notifications(days: int = 30) -> Tuple[bool, str, int]:
        """
        Löscht alte Benachrichtigungen

        Args:
            days: Alter in Tagen

        Returns:
            Tuple: (success, message, deleted_count)
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            result = mongodb.delete_many('notifications', {
                'created_at': {'$lt': cutoff_date}
            })

            deleted_count = result.deleted_count

            logger.info(f"Alte Benachrichtigungen gelöscht: {deleted_count}")
            return True, f"{deleted_count} alte Benachrichtigungen gelöscht", deleted_count

        except Exception as e:
            logger.error(f"Fehler beim Löschen alter Benachrichtigungen: {e}")
            return False, f"Fehler beim Löschen: {str(e)}", 0

    @staticmethod
    def get_notification_statistics() -> Dict[str, Any]:
        """
        Holt Statistiken zu Benachrichtigungen

        Returns:
            Dict mit Statistiken
        """
        try:
            total = mongodb.count_documents('notifications', {})
            unread = mongodb.count_documents('notifications', {'read': False})

            # Nach Typ gruppieren
            type_stats = {}
            pipeline = [
                {'$group': {'_id': '$type', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]

            for stat in mongodb.aggregate('notifications', pipeline):
                type_stats[stat['_id']] = stat['count']

            # Nach Priorität gruppieren
            priority_stats = {}
            pipeline = [
                {'$group': {'_id': '$priority', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]

            for stat in mongodb.aggregate('notifications', pipeline):
                priority_stats[stat['_id']] = stat['count']

            return {
                'total': total,
                'unread': unread,
                'by_type': type_stats,
                'by_priority': priority_stats
            }

        except Exception as e:
            logger.error(f"Fehler beim Laden der Benachrichtigungsstatistiken: {e}")
            return {
                'total': 0,
                'unread': 0,
                'by_type': {},
                'by_priority': {}
            }

    # === E-MAIL TEMPLATE FUNKTIONEN (aus admin_email_templates_service.py) ===

    @staticmethod
    def get_email_templates() -> List[Dict[str, Any]]:
        """
        Holt alle E-Mail-Templates

        Returns:
            Liste der E-Mail-Templates
        """
        try:
            templates = list(mongodb.find('email_templates', {}).sort('name', 1))
            # ID zu String konvertieren für JSON-Serialisierung
            for template in templates:
                if '_id' in template:
                    template['_id'] = str(template['_id'])
            return templates
        except Exception as e:
            logger.error(f"Fehler beim Laden der E-Mail-Templates: {e}")
            return []

    @staticmethod
    def get_email_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt ein E-Mail-Template anhand der ID

        Args:
            template_id: Template-ID

        Returns:
            Template-Daten oder None
        """
        try:
            template = mongodb.find_one('email_templates', {'_id': convert_id_for_query(template_id)})
            if template and '_id' in template:
                template['_id'] = str(template['_id'])
            return template
        except Exception as e:
            logger.error(f"Fehler beim Laden des E-Mail-Templates {template_id}: {e}")
            return None

    @staticmethod
    def create_email_template(template_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein neues E-Mail-Template

        Args:
            template_data: Template-Daten

        Returns:
            Tuple: (success, message, template_id)
        """
        try:
            template = {
                'name': template_data.get('name', ''),
                'subject': template_data.get('subject', ''),
                'body': template_data.get('body', ''),
                'variables': template_data.get('variables', []),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            result = mongodb.insert_one('email_templates', template)
            template_id = str(result)

            logger.info(f"E-Mail-Template erstellt: {template_id}")
            return True, "Template erfolgreich erstellt", template_id

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des E-Mail-Templates: {e}")
            return False, f"Fehler beim Erstellen: {str(e)}", None

    @staticmethod
    def update_email_template(template_id: str, template_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert ein E-Mail-Template

        Args:
            template_id: Template-ID
            template_data: Neue Template-Daten

        Returns:
            Tuple: (success, message)
        """
        try:
            update_data = {
                'updated_at': datetime.now()
            }

            if 'name' in template_data:
                update_data['name'] = template_data['name']
            if 'subject' in template_data:
                update_data['subject'] = template_data['subject']
            if 'body' in template_data:
                update_data['body'] = template_data['body']
            if 'variables' in template_data:
                update_data['variables'] = template_data['variables']

            result = mongodb.update_one(
                'email_templates',
                {'_id': convert_id_for_query(template_id)},
                {'$set': update_data}
            )

            if result:
                logger.info(f"E-Mail-Template aktualisiert: {template_id}")
                return True, "Template erfolgreich aktualisiert"
            else:
                return False, "Template nicht gefunden"

        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des E-Mail-Templates: {e}")
            return False, f"Fehler beim Aktualisieren: {str(e)}"

    @staticmethod
    def delete_email_template(template_id: str) -> Tuple[bool, str]:
        """
        Löscht ein E-Mail-Template

        Args:
            template_id: Template-ID

        Returns:
            Tuple: (success, message)
        """
        try:
            result = mongodb.delete_one('email_templates', {'_id': convert_id_for_query(template_id)})

            if result:
                logger.info(f"E-Mail-Template gelöscht: {template_id}")
                return True, "Template erfolgreich gelöscht"
            else:
                return False, "Template nicht gefunden"

        except Exception as e:
            logger.error(f"Fehler beim Löschen des E-Mail-Templates: {e}")
            return False, f"Fehler beim Löschen: {str(e)}"

    @staticmethod
    def render_email_template(template_id: str, variables: Dict[str, Any]) -> Tuple[bool, str, str]:
        """
        Rendert ein E-Mail-Template mit Variablen

        Args:
            template_id: Template-ID
            variables: Variablen für das Template

        Returns:
            Tuple: (success, subject, body)
        """
        try:
            template = UnifiedNotificationService.get_email_template_by_id(template_id)
            if not template:
                return False, "", "Template nicht gefunden"

            subject = template.get('subject', '')
            body = template.get('body', '')

            # Variablen ersetzen
            for key, value in variables.items():
                placeholder = f"{{{key}}}"
                subject = subject.replace(placeholder, str(value))
                body = body.replace(placeholder, str(value))

            return True, subject, body

        except Exception as e:
            logger.error(f"Fehler beim Rendern des E-Mail-Templates: {e}")
            return False, "", f"Fehler beim Rendern: {str(e)}"


# Globale Instanz für einfache Verwendung
unified_notification_service = UnifiedNotificationService()
