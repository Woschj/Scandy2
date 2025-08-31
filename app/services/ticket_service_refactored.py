"""
Refaktorierte Version des TicketService

Beispiel für besseres Code-Refactoring:
- Lange Methoden aufgeteilt
- Hilfsfunktionen extrahiert
- Konstanten definiert
- Bessere Lesbarkeit
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from flask import current_app, g
from app.models.mongodb_database import mongodb
from app.services.unified_notification_service import unified_notification_service
from app.utils.database_helpers import get_next_ticket_number
from app.services.ticket_category_service import ticket_category_service
from app.utils.enhanced_error_handler import (
    handle_service_errors, ValidationException, validate_required_fields
)
from app.utils.performance_optimizer import optimize_db_query, cached_query
from app.utils.constants import (
    TICKET_STATUS, TICKET_PRIORITIES, USER_ROLES, CACHE_TTL,
    DB_COLLECTIONS, PAGINATION_DEFAULTS, BUSINESS_RULES
)
import logging

logger = logging.getLogger(__name__)

class TicketServiceRefactored:
    """
    Refaktorierte Version des TicketService mit besserer Lesbarkeit

    Verbesserungen:
    - Lange Methoden aufgeteilt
    - Hilfsfunktionen für wiederkehrende Logik
    - Konstanten für Magic Strings/Numbers
    - Bessere Fehlerbehandlung
    - Performance-Optimierungen
    """

    def __init__(self):
        pass

    # === HILFSFUNKTIONEN ===

    def _get_current_department(self) -> Optional[str]:
        """Holt das aktuelle Department aus dem Request-Context"""
        return getattr(g, 'current_department', None)

    def _build_base_ticket_filter(self, include_deleted: bool = False) -> Dict[str, Any]:
        """
        Erstellt einen Basis-Filter für Ticket-Abfragen

        Args:
            include_deleted: Ob gelöschte Tickets eingeschlossen werden sollen

        Returns:
            Basis-Filter für MongoDB-Abfragen
        """
        base_filter = {'status': {'$ne': None}}  # Immer einen Status haben

        if not include_deleted:
            base_filter['deleted'] = {'$ne': True}

        department = self._get_current_department()
        if department:
            base_filter['department'] = department

        return base_filter

    def _build_unassigned_filter(self) -> Dict[str, Any]:
        """
        Erstellt einen Filter für nicht zugewiesene Tickets

        Returns:
            Filter für nicht zugewiesene Tickets
        """
        return {
            '$or': [
                {'assigned_to': None},
                {'assigned_to': ''},
                {'assigned_to': {'$exists': False}}
            ]
        }

    def _build_user_assignment_filter(self, username: str) -> Dict[str, Any]:
        """
        Erstellt einen Filter für einem Nutzer zugewiesene Tickets

        Args:
            username: Nutzername

        Returns:
            Filter für zugewiesene Tickets
        """
        department = self._get_current_department()
        base_filter = {'assigned_to': username, 'deleted': {'$ne': True}}

        if department:
            base_filter['$or'] = [
                {'department': department},
                {'department': {'$exists': False}}
            ]

        return base_filter

    def _add_category_filter(self, query_filter: Dict[str, Any], categories: List[str]) -> Dict[str, Any]:
        """
        Fügt einen Kategorie-Filter zu einer Abfrage hinzu

        Args:
            query_filter: Bestehende Abfrage
            categories: Zu filternde Kategorien

        Returns:
            Abfrage mit Kategorie-Filter
        """
        if categories:
            if '$and' not in query_filter:
                query_filter = {'$and': [query_filter]}
            query_filter['$and'].append({'category': {'$in': categories}})

        return query_filter

    def _convert_datetime_fields_in_tickets(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Konvertiert Datumsfelder in Ticket-Listen

        Args:
            tickets: Liste von Tickets

        Returns:
            Tickets mit konvertierten Datumsfeldern
        """
        date_fields = ['created_at', 'updated_at', 'due_date', 'deleted_at']

        for ticket in tickets:
            for field in date_fields:
                if ticket.get(field) and isinstance(ticket[field], str):
                    try:
                        # Versuche verschiedene Datumsformate
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                ticket[field] = datetime.strptime(ticket[field], fmt)
                                break
                            except ValueError:
                                continue
                    except:
                        ticket[field] = None

            # ID-Feld für Template-Kompatibilität
            ticket['id'] = str(ticket['_id'])

        return tickets

    def _add_message_counts_to_tickets(self, tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fügt Nachrichtenanzahl zu Tickets hinzu

        Args:
            tickets: Liste von Tickets

        Returns:
            Tickets mit Nachrichtenanzahl
        """
        for ticket in tickets:
            try:
                ticket_id = str(ticket['_id'])
                messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id})
                ticket['message_count'] = len(list(messages))
            except Exception as e:
                logger.warning(f"Fehler beim Laden der Nachrichten für Ticket {ticket.get('_id')}: {e}")
                ticket['message_count'] = 0

        return tickets

    # === HAUPTMETHODEN ===

    @handle_service_errors("TicketService")
    def create_ticket(self, ticket_data: Dict[str, Any], created_by: str) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein neues Ticket mit verbesserter Validierung

        Args:
            ticket_data: Ticket-Daten
            created_by: Nutzername des Erstellers

        Returns:
            Tuple: (success, message, ticket_id)
        """
        # Verbesserte Validierung
        validate_required_fields(ticket_data, ['title'])

        if not created_by or not isinstance(created_by, str):
            raise ValidationException("Ersteller ist erforderlich", field="created_by")

        # Kategorie validieren falls vorhanden
        category = ticket_data.get('category')
        current_department = self._get_current_department()

        if category:
            allowed_categories = ticket_category_service.get_ticket_categories_for_department(current_department)
            if category not in allowed_categories:
                raise ValidationException(
                    f"Kategorie '{category}' ist für diese Abteilung nicht zulässig",
                    field="category"
                )

        # Fälligkeitsdatum validieren
        due_date = ticket_data.get('due_date')
        if due_date:
            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                raise ValidationException("Ungültiges Datumsformat", field="due_date")

        # Ticket-Daten vorbereiten
        ticket = {
            'title': ticket_data['title'].strip(),
            'description': ticket_data.get('description', '').strip(),
            'priority': ticket_data.get('priority', 'normal'),
            'created_by': created_by,
            'category': category,
            'due_date': due_date,
            'estimated_time': ticket_data.get('estimated_time'),
            'status': TICKET_STATUS_OFFEN,
            'department': current_department,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'ticket_number': get_next_ticket_number()
        }

        # In Datenbank speichern
        result = mongodb.insert_one(DB_COLLECTIONS['TICKETS'], ticket)
        ticket_id = str(result)

        logger.info(f"Ticket erstellt: {ticket_id} von {created_by}")
        return True, 'Ticket wurde erfolgreich erstellt', ticket_id

    @cached_query(ttl=CACHE_TTL['LONG'], key_prefix="ticket")
    @optimize_db_query
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt ein Ticket anhand der ID mit optimierter Performance

        Args:
            ticket_id: Ticket-ID

        Returns:
            Ticket-Daten oder None
        """
        ticket = mongodb.find_one('tickets', {'_id': ticket_id})

        if ticket:
            ticket = self._convert_datetime_fields_in_tickets([ticket])[0]
            return ticket

        return None

    @cached_query(ttl=CACHE_TTL['SHORT'], key_prefix="tickets_user")
    @optimize_db_query
    def get_tickets_by_user(self, username: str, role: str, handlungsfelder: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Holt Tickets für einen Nutzer - refaktoriert für bessere Lesbarkeit

        Args:
            username: Nutzername
            role: Nutzerrolle
            handlungsfelder: Zugewiesene Handlungsfelder

        Returns:
            Dictionary mit verschiedenen Ticket-Listen
        """
        logger.debug(f"Lade Tickets für Nutzer: {username}, Rolle: {role}")

        # Offene Tickets laden
        open_tickets = self._get_open_tickets_for_user(username, role, handlungsfelder)

        # Zugewiesene Tickets laden
        assigned_tickets = self._get_assigned_tickets_for_user(username, role)

        # Alle Tickets für Admin
        all_tickets = []
        if role == 'admin':
            all_tickets = self._get_all_tickets_for_admin()

        # Daten anreichern und sortieren
        ticket_lists = [open_tickets, assigned_tickets, all_tickets]

        for ticket_list in ticket_lists:
            self._enrich_ticket_data(ticket_list)

        # Sortierung: Neueste zuerst
        for ticket_list in ticket_lists:
            ticket_list.sort(key=lambda t: t.get('updated_at', datetime.min), reverse=True)

        return {
            'open_tickets': open_tickets,
            'assigned_tickets': assigned_tickets,
            'all_tickets': all_tickets
        }

    # === HILFSMETHODE FÜR TICKET-ABFRAGEN ===

    def _get_open_tickets_for_user(self, username: str, role: str, handlungsfelder: List[str] = None) -> List[Dict[str, Any]]:
        """Lädt offene Tickets für einen Nutzer"""
        base_filter = self._build_base_ticket_filter()
        base_filter['status'] = TICKET_STATUS_OFFEN

        # Nicht zugewiesene Tickets
        unassigned_filter = self._build_unassigned_filter()
        query = {
            '$and': [base_filter, unassigned_filter]
        }

        # Handlungsfeld-Filter für Nicht-Admin-Nutzer
        if role != USER_ROLES['ADMIN'] and handlungsfelder:
            query = self._add_category_filter(query, handlungsfelder)
            logger.debug(f"Offene Tickets mit Handlungsfeld-Filter: {handlungsfelder}")

        logger.debug(f"Offene Tickets Query: {query}")
        return list(mongodb.find('tickets', query))

    def _get_assigned_tickets_for_user(self, username: str, role: str) -> List[Dict[str, Any]]:
        """Lädt zugewiesene Tickets für einen Nutzer"""
        # Legacy-Zuweisungen
        legacy_query = self._build_user_assignment_filter(username)
        assigned_tickets_legacy = list(mongodb.find('tickets', legacy_query))

        # Mehrfachzuweisungen
        multi_assigned_ids = self._get_multi_assigned_ticket_ids(username)
        assigned_tickets_multi = []
        if multi_assigned_ids:
            multi_query = {
                '_id': {'$in': multi_assigned_ids},
                'deleted': {'$ne': True}
            }
            assigned_tickets_multi = list(mongodb.find('tickets', multi_query))

        # Verantwortliche Tickets
        responsible_query = {
            'responsible': username,
            'deleted': {'$ne': True}
        }
        responsible_tickets = list(mongodb.find('tickets', responsible_query))

        # Duplikate entfernen und zusammenführen
        all_assigned = assigned_tickets_legacy + assigned_tickets_multi + responsible_tickets
        seen_ids = set()
        deduplicated = []

        for ticket in all_assigned:
            ticket_id = str(ticket.get('_id'))
            if ticket_id not in seen_ids:
                seen_ids.add(ticket_id)
                deduplicated.append(ticket)

        logger.debug(f"Zugewiesene Tickets gefunden: {len(deduplicated)}")
        return deduplicated

    def _get_multi_assigned_ticket_ids(self, username: str) -> List[str]:
        """Holt IDs von Mehrfach-Zuweisungen für einen Nutzer"""
        try:
            assignments = list(mongodb.find('ticket_assignments', {'assigned_to': username}))
            return [str(a.get('ticket_id')) for a in assignments if a.get('ticket_id')]
        except Exception as e:
            logger.warning(f"Fehler beim Laden der Mehrfachzuweisungen: {e}")
            return []

    def _get_all_tickets_for_admin(self) -> List[Dict[str, Any]]:
        """Lädt alle Tickets für Admin-Nutzer"""
        query = self._build_base_ticket_filter()
        logger.debug(f"Alle Tickets Query: {query}")
        return list(mongodb.find('tickets', query))

    def _enrich_ticket_data(self, tickets: List[Dict[str, Any]]) -> None:
        """Reichert Ticket-Daten mit zusätzlichen Informationen an"""
        # Datumsfelder konvertieren
        tickets[:] = self._convert_datetime_fields_in_tickets(tickets)

        # Nachrichtenanzahl hinzufügen
        tickets[:] = self._add_message_counts_to_tickets(tickets)

        # Auftragsdetails-Flag hinzufügen
        for ticket in tickets:
            ticket['has_auftrag_details'] = bool(ticket.get('auftrag_details'))

    # === WEITERE METHODEN (vereinfacht) ===

    @handle_service_errors("TicketService")
    def update_ticket_status(self, ticket_id: str, new_status: str, updated_by: str) -> Tuple[bool, str]:
        """
        Aktualisiert den Status eines Tickets

        Args:
            ticket_id: Ticket-ID
            new_status: Neuer Status
            updated_by: Nutzername des Updaters

        Returns:
            Tuple: (success, message)
        """
        ticket = self.get_ticket_by_id(ticket_id)
        if not ticket:
            return False, 'Ticket nicht gefunden'

        old_status = ticket.get('status', 'unbekannt')

        # Status aktualisieren
        update_result = mongodb.update_one(
            'tickets',
            {'_id': ticket_id},
            {
                '$set': {
                    'status': new_status,
                    'updated_at': datetime.now(),
                    'updated_by': updated_by
                }
            }
        )

        if not update_result:
            return False, 'Fehler beim Aktualisieren des Tickets'

        # Benachrichtigung senden
        self._send_status_update_notification(ticket, new_status, updated_by)

        logger.info(f"Ticket-Status aktualisiert: {ticket_id} -> {new_status}")
        return True, f'Status erfolgreich auf "{new_status}" geändert'

    def _send_status_update_notification(self, ticket: Dict[str, Any], new_status: str, updated_by: str) -> None:
        """Sendet Benachrichtigung bei Status-Update"""
        assigned_user = ticket.get('assigned_to')
        if assigned_user and assigned_user != updated_by:
            try:
                user = mongodb.find_one('users', {'username': assigned_user})
                if user and user.get('email'):
                    unified_notification_service.send_ticket_notification_email(
                        user['email'], ticket, 'updated'
                    )
            except Exception as e:
                logger.warning(f"Fehler beim Senden der Status-Update-Benachrichtigung: {e}")

    def get_unassigned_ticket_count(self) -> int:
        """
        Zählt nicht zugewiesene Tickets

        Returns:
            Anzahl der nicht zugewiesenen Tickets
        """
        try:
            unassigned_filter = self._build_unassigned_filter()
            query = {
                '$and': [
                    unassigned_filter,
                    {'status': TICKET_STATUS_OFFEN},
                    {'deleted': {'$ne': True}}
                ]
            }

            return mongodb.count_documents('tickets', query)

        except Exception as e:
            logger.error(f"Fehler beim Zählen der nicht zugewiesenen Tickets: {e}")
            return 0
