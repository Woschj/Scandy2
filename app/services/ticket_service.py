"""
Zentraler Ticket Service für Scandy
Alle Ticket-Funktionalitäten an einem Ort
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from flask import current_app, g
from app.models.mongodb_database import mongodb
from app.services.notification_service import NotificationService
from app.services.utility_service import UtilityService
from app.utils.database_helpers import get_next_ticket_number
from app.services.ticket_category_service import ticket_category_service
import logging

logger = logging.getLogger(__name__)

class TicketService:
    """Zentraler Service für alle Ticket-Operationen"""
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.utility_service = UtilityService()
        # Erlaubte Stati und Transitionen (robuste Statusmaschine)
        self.ALLOWED_STATUSES = ['offen', 'zugewiesen', 'in_bearbeitung', 'wartet_auf_antwort', 'gelöst', 'geschlossen']
        self.ALLOWED_TRANSITIONS = {
            'offen': {'zugewiesen', 'in_bearbeitung', 'geschlossen'},
            'zugewiesen': {'in_bearbeitung', 'wartet_auf_antwort', 'gelöst', 'geschlossen'},
            'in_bearbeitung': {'wartet_auf_antwort', 'gelöst', 'geschlossen'},
            'wartet_auf_antwort': {'in_bearbeitung', 'gelöst', 'geschlossen'},
            'gelöst': {'geschlossen', 'offen'},  # Reopen erlaubt
            'geschlossen': {'offen'}             # Reopen
        }

    def _get_required_fields_for_category(self, department: str, category: str) -> list:
        """Ermittelt Pflichtfelder aus Settings je Abteilung/Kategorie."""
        try:
            # Department‑spezifisch
            if department:
                s = mongodb.find_one('settings', {'key': 'ticket_required_fields', 'department': department})
                if s and isinstance(s.get('value'), dict):
                    return s['value'].get(category, []) or []
            # Global
            s = mongodb.find_one('settings', {'key': 'ticket_required_fields'})
            if s and isinstance(s.get('value'), dict):
                return s['value'].get(category, []) or []
        except Exception:
            pass
        return []
    
    def create_ticket(self, ticket_data: Dict[str, Any], created_by: str) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein neues Ticket
        
        Args:
            ticket_data: Ticket-Daten
            created_by: Benutzername des Erstellers
            
        Returns:
            Tuple: (success, message, ticket_id)
        """
        try:
            # Validierung
            if not ticket_data.get('title'):
                return False, 'Titel ist erforderlich', None
            
            # Kategorie validieren: strikt gegen department-spezifische Kategorien
            category = ticket_data.get('category')
            current_department = getattr(g, 'current_department', None)
            if category:
                allowed = set(ticket_category_service.get_ticket_categories_for_department(current_department))
                if category not in allowed:
                    return False, 'Kategorie ist für diese Abteilung nicht zulässig', None
            
            # Pflichtfelder prüfen (aus Settings)
            required_fields = self._get_required_fields_for_category(current_department, category or '')
            for field in required_fields:
                val = (ticket_data.get(field) if isinstance(ticket_data, dict) else None)
                if val is None or (isinstance(val, str) and not val.strip()):
                    return False, f'Pflichtfeld fehlt: {field}', None
            
            # Fälligkeitsdatum formatieren
            due_date = ticket_data.get('due_date')
            if due_date:
                try:
                    due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                except ValueError:
                    due_date = None
            
            # Ticket-Daten vorbereiten
            ticket = {
                'title': ticket_data['title'],
                'description': ticket_data.get('description', ''),
                'priority': ticket_data.get('priority', 'normal'),
                'created_by': created_by,
                'category': category,
                'due_date': due_date,
                'estimated_time': ticket_data.get('estimated_time'),
                'status': 'offen',
                'department': current_department,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'ticket_number': get_next_ticket_number(),
                'version': 0
            }
            
            # Ticket in Datenbank speichern
            result = mongodb.insert_one('tickets', ticket)
            ticket_id = str(result)
            
            # History-Logging für Ticket-Erstellung
            try:
                from app.services.ticket_history_service import ticket_history_service
                ticket_history_service.log_creation(
                    ticket_id=ticket_id,
                    created_by=created_by,
                    ticket_data=ticket
                )
            except Exception as history_error:
                logger.error(f"Fehler beim History-Logging für Ticket-Erstellung: {history_error}")
            
            logger.info(f"Ticket erstellt: {ticket_id} von {created_by}")
            return True, 'Ticket wurde erfolgreich erstellt', ticket_id
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Tickets: [Interner Fehler]")
            return False, f'Fehler beim Erstellen des Tickets: [Interner Fehler]', None
    
    def get_tickets_by_user(self, username: str, role: str, handlungsfelder: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Holt Tickets basierend auf Benutzerrolle und Handlungsfeld-Zuweisungen
        
        Args:
            username: Benutzername
            role: Benutzerrolle
            handlungsfelder: Liste der zugewiesenen Handlungsfelder (Ticket-Kategorien)
            
        Returns:
            Dict: Verschiedene Ticket-Listen
        """
        try:
            logger.debug(f"Lade Tickets für Benutzer: {username}, Rolle: {role}, Handlungsfelder: {handlungsfelder}")
            
            # Debug: Prüfe alle Tickets in der Datenbank
            all_tickets_debug = list(mongodb.find('tickets', {}))
            logger.debug(f"Gesamtanzahl Tickets in DB: {len(all_tickets_debug)}")
            
            # Offene Tickets (nicht zugewiesene, offene Tickets)
            open_query = {
                '$and': [
                    {
                        '$or': [
                            {'assigned_to': None},
                            {'assigned_to': ''},
                            {'assigned_to': {'$exists': False}}
                        ]
                    },
                    {'status': 'offen'},
                    {'deleted': {'$ne': True}}
                ]
            }
            if getattr(g, 'current_department', None):
                open_query['$and'].append({'department': g.current_department})
            
            # Handlungsfeld-Filter für alle Rollen außer Admin
            if role != 'admin' and handlungsfelder:
                # Für alle Rollen außer Admin: Nur offene Tickets aus zugewiesenen Handlungsfeldern
                open_query['$and'].append({'category': {'$in': handlungsfelder}})
                logger.debug(f"Offene Tickets mit Handlungsfeld-Filter: {handlungsfelder}")
            
            logger.debug(f"Offene Tickets Query: {open_query}")
            open_tickets = mongodb.find('tickets', open_query)
            open_tickets = list(open_tickets)
            logger.debug(f"Offene Tickets gefunden: {len(open_tickets)}")
            
            # Zugewiesene Tickets (alle Stati, inkl. abgeschlossene)
            # 1) Legacy-Zuweisung über Feld "assigned_to"
            assigned_tickets_legacy_query = {
                '$and': [
                    {'assigned_to': username},
                    {'deleted': {'$ne': True}}
                ]
            }
            if getattr(g, 'current_department', None):
                assigned_tickets_legacy_query['$and'].append({
                    '$or': [
                        {'department': g.current_department},
                        {'department': {'$exists': False}}
                    ]
                })

            # Handlungsfeld-Filter für alle Rollen außer Admin
            # WICHTIG: Handlungsfelder NICHT für zugewiesene Tickets filtern –
            # ein Nutzer muss alle ihm zugewiesenen Tickets sehen, unabhängig vom Handlungsfeld

            logger.debug(f"Zugewiesene (Legacy) Tickets Query: {assigned_tickets_legacy_query}")
            assigned_tickets_legacy = list(mongodb.find('tickets', assigned_tickets_legacy_query))
            logger.debug(f"Zugewiesene (Legacy) Tickets gefunden: {len(assigned_tickets_legacy)}")

            # 2) Mehrfachzuweisungen über Collection "ticket_assignments"
            try:
                user_assignments = list(mongodb.find('ticket_assignments', {'assigned_to': username}))
                assignment_ticket_ids_raw = [ua.get('ticket_id') for ua in user_assignments if ua.get('ticket_id')]
                # Konvertiere IDs für die Ticketsuche
                assignment_ticket_ids = []
                for raw_id in assignment_ticket_ids_raw:
                    # Immer als String sammeln; die Datenbankschicht konvertiert bei Bedarf zu ObjectId
                    assignment_ticket_ids.append(str(raw_id))

                assigned_tickets_multi = []
                if assignment_ticket_ids:
                    assigned_tickets_multi_query = {
                        '$and': [
                            {'_id': {'$in': assignment_ticket_ids}},
                            {'deleted': {'$ne': True}}
                        ]
                    }
                    if getattr(g, 'current_department', None):
                        assigned_tickets_multi_query['$and'].append({
                            '$or': [
                                {'department': g.current_department},
                                {'department': {'$exists': False}}
                            ]
                        })
                    # WICHTIG: Handlungsfelder NICHT für zugewiesene Tickets filtern

                    logger.debug(f"Zugewiesene (Multi) Tickets Query: {assigned_tickets_multi_query}")
                    assigned_tickets_multi = list(mongodb.find('tickets', assigned_tickets_multi_query))
                else:
                    logger.debug("Keine Mehrfachzuweisungen für Benutzer gefunden.")
            except Exception as assign_err:
                logger.error(f"Fehler beim Laden der Mehrfachzuweisungen: {assign_err}")
                assigned_tickets_multi = []

            # 3) Tickets, für die der Nutzer verantwortlich ist, ergänzen
            responsible_query = {
                '$and': [
                    {'responsible': username},
                    {'deleted': {'$ne': True}}
                ]
            }
            if getattr(g, 'current_department', None):
                responsible_query['$and'].append({
                    '$or': [
                        {'department': g.current_department},
                        {'department': {'$exists': False}}
                    ]
                })
            responsible_tickets = list(mongodb.find('tickets', responsible_query))

            # 4) Zusammenführen und Duplikate entfernen
            assigned_tickets_map = {}
            for t in assigned_tickets_legacy + assigned_tickets_multi + responsible_tickets:
                try:
                    key = str(t.get('_id') or t.get('id'))
                    assigned_tickets_map[key] = t
                except Exception:
                    continue
            assigned_tickets = list(assigned_tickets_map.values())
            logger.debug(f"Zugewiesene Tickets gesamt (dedupliziert): {len(assigned_tickets)}")
            
            # Alle Tickets (nur für Admin)
            all_tickets = []
            if role == 'admin':
                all_query = {'deleted': {'$ne': True}}
                if getattr(g, 'current_department', None):
                    all_query['department'] = g.current_department
                logger.debug(f"Alle Tickets Query: {all_query}")
                all_tickets = mongodb.find('tickets', all_query)
                all_tickets = list(all_tickets)
                logger.debug(f"Alle Tickets gefunden: {len(all_tickets)}")
            
            # Nachrichtenanzahl und Auftragsdetails hinzufügen
            logger.debug(f"Verarbeite {len(open_tickets)} offene, {len(assigned_tickets)} zugewiesene, {len(all_tickets)} alle Tickets")
            
            for ticket_list in [open_tickets, assigned_tickets, all_tickets]:
                for ticket in ticket_list:
                    logger.debug(f"Verarbeite Ticket: {ticket.get('title', 'Kein Titel')} (ID: {ticket.get('_id')})")
                    
                    # ID-Feld für Template-Kompatibilität
                    ticket['id'] = str(ticket['_id'])
                    
                    # Nachrichtenanzahl laden (korrekte Collection)
                    # Unterstütze Messages, deren ticket_id als String oder ObjectId gespeichert ist
                    messages = mongodb.find('ticket_messages', {
                        '$or': [
                            {'ticket_id': str(ticket['_id'])},
                            {'ticket_id': ticket.get('_id')}
                        ]
                    })
                    ticket['message_count'] = len(list(messages))
                    
                    # Auftragsdetails laden (falls vorhanden)
                    if ticket.get('auftrag_details'):
                        ticket['has_auftrag_details'] = True
                    else:
                        ticket['has_auftrag_details'] = False
                    
                    # Datum-Formatierung
                    ticket = self._convert_datetime_fields(ticket)
            
            # Sortierung: Neueste zuerst
            def safe_sort_key(ticket):
                updated_at = ticket.get('updated_at')
                if isinstance(updated_at, str):
                    try:
                        return datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.warning(f"Fehler bei Datumskonvertierung updated_at: [Interner Fehler]")
                        return datetime.min
                elif isinstance(updated_at, datetime):
                    return updated_at
                else:
                    return datetime.min
            
            open_tickets.sort(key=safe_sort_key, reverse=True)
            assigned_tickets.sort(key=safe_sort_key, reverse=True)
            all_tickets.sort(key=safe_sort_key, reverse=True)
            
            return {
                'open_tickets': open_tickets,
                'assigned_tickets': assigned_tickets,
                'all_tickets': all_tickets
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Tickets: [Interner Fehler]")
            return {
                'open_tickets': [],
                'assigned_tickets': [],
                'all_tickets': []
            }
    
    def get_ticket_by_id(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt ein Ticket anhand der ID
        
        Args:
            ticket_id: Ticket-ID
            
        Returns:
            Optional[Dict]: Ticket-Daten oder None
        """
        try:
            # Versuche verschiedene ID-Formate
            ticket = None
            
            # Versuche zuerst mit String-ID
            try:
                ticket = mongodb.find_one('tickets', {'_id': ticket_id})
            except Exception as e:
                logger.warning(f"Fehler bei String-ID-Suche für Ticket {ticket_id}: [Interner Fehler]")
                pass
            
            # Falls nicht gefunden, versuche mit ObjectId
            if not ticket:
                try:
                    from bson import ObjectId
                    obj_id = ObjectId(ticket_id)
                    ticket = mongodb.find_one('tickets', {'_id': obj_id})
                except Exception as e:
                    logger.warning(f"Fehler bei ObjectId-Suche für Ticket {ticket_id}: [Interner Fehler]")
                    pass
            
            if ticket:
                ticket = self._convert_datetime_fields(ticket)
                ticket['id'] = str(ticket['_id'])
            return ticket
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Tickets {ticket_id}: [Interner Fehler]")
            return None
    
    def update_ticket_status(self, ticket_id: str, new_status: str, updated_by: str) -> Tuple[bool, str]:
        """
        Aktualisiert den Status eines Tickets
        
        Args:
            ticket_id: Ticket-ID
            new_status: Neuer Status
            updated_by: Benutzername des Aktualisierenden
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            # Validierung Status
            if new_status not in self.ALLOWED_STATUSES:
                return False, 'Ungültiger Status'
            # Speichere alten Status für History
            old_status = ticket.get('status', 'unbekannt')
            allowed_next = self.ALLOWED_TRANSITIONS.get(old_status, set())
            if new_status not in allowed_next:
                return False, f'Statuswechsel nicht erlaubt: {old_status} → {new_status}'
            
            # Status aktualisieren
            mongodb.update_one('tickets', 
                             {'_id': ticket_id}, 
                             {'$set': {
                                 'status': new_status,
                                 'updated_at': datetime.now(),
                                 'updated_by': updated_by
                             }})
            
            # History-Logging für Status-Änderung
            try:
                from app.services.ticket_history_service import ticket_history_service
                ticket_history_service.log_status_change(
                    ticket_id=str(ticket_id),
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=updated_by
                )
            except Exception as history_error:
                logger.error(f"Fehler beim History-Logging für Status-Änderung: {history_error}")
            
            # Benachrichtigung senden falls gewünscht
            if ticket.get('assigned_to') and ticket['assigned_to'] != updated_by:
                assigned_user = mongodb.find_one('users', {'username': ticket['assigned_to']})
                if assigned_user and assigned_user.get('email'):
                    self.notification_service.notify_ticket_update(ticket, assigned_user['email'])
            
            logger.info(f"Ticket-Status aktualisiert: {ticket_id} -> {new_status} von {updated_by}")
            return True, f'Status erfolgreich auf "{new_status}" geändert'
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Ticket-Status: [Interner Fehler]")
            return False, f'Fehler beim Aktualisieren: [Interner Fehler]'
    
    def assign_ticket(self, ticket_id: str, assigned_to: str, assigned_by: str) -> Tuple[bool, str]:
        """
        Weist ein Ticket einem Benutzer zu (Legacy-Methode für Einzelzuweisung)
        
        Args:
            ticket_id: Ticket-ID
            assigned_to: Benutzername des Zugewiesenen
            assigned_by: Benutzername des Zuweisenden
            
        Returns:
            Tuple: (success, message)
        """
        return self.assign_ticket_multiple(ticket_id, [assigned_to], assigned_by)
    
    def assign_ticket_multiple(self, ticket_id: str, assigned_users: List[str], assigned_by: str) -> Tuple[bool, str]:
        """
        Weist ein Ticket mehreren Benutzern zu
        
        Args:
            ticket_id: Ticket-ID
            assigned_users: Liste der Benutzernamen der Zugewiesenen
            assigned_by: Benutzername des Zuweisenden
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            # Prüfe ob alle Benutzer existieren
            valid_users = []
            for username in assigned_users:
                if username:  # Ignoriere leere Strings
                    user = mongodb.find_one('users', {'username': username})
                    if user:
                        valid_users.append(username)
                    else:
                        logger.warning(f"Benutzer {username} nicht gefunden")
            
            # Bestehende Zuweisungen auflösen: set‑basiert aktualisieren (idempotent)
            existing = list(mongodb.find('ticket_assignments', {
                '$or': [
                    {'ticket_id': ticket_id},
                    {'ticket_id': str(ticket_id)}
                ]
            }))
            existing_users = {a.get('assigned_to') for a in existing if a.get('assigned_to')}
            target_users = set(valid_users)
            to_add = target_users - existing_users
            to_remove = existing_users - target_users
            # Entfernen
            if to_remove:
                mongodb.delete_many('ticket_assignments', {
                    '$and': [
                        {'assigned_to': {'$in': list(to_remove)}},
                        {'$or': [
                            {'ticket_id': ticket_id},
                            {'ticket_id': str(ticket_id)}
                        ]}
                    ]
                })
            
            # Erstelle neue Zuweisungen
            for username in to_add:
                assignment = {
                    'ticket_id': ticket_id,
                    'assigned_to': username,
                    'assigned_by': assigned_by,
                    'assigned_at': datetime.now()
                }
                mongodb.insert_one('ticket_assignments', assignment)
            
            # Aktualisiere das Ticket mit der ersten Zuweisung (für Kompatibilität)
            primary_assignment = (list(target_users)[0] if target_users else None)
            mongodb.update_one('tickets', 
                             {'_id': ticket_id}, 
                             {'$set': {
                                 'assigned_to': primary_assignment,
                                 'updated_at': datetime.now(),
                                 'updated_by': assigned_by
                             }})
            
            # Wenn keine gültigen Zuweisungen existieren, Status auf 'offen' setzen (außer bei finalen Stati)
            if not valid_users:
                try:
                    if ticket.get('status') not in ['gelöst', 'geschlossen']:
                        mongodb.update_one('tickets',
                                         {'_id': ticket_id},
                                         {'$set': {
                                             'status': 'offen',
                                             'updated_at': datetime.now(),
                                             'updated_by': assigned_by
                                         }})
                except Exception as status_err:
                    logger.error(f"Fehler beim Zurücksetzen des Status für Ticket {ticket_id}: {status_err}")
            
            # Benachrichtigungen senden
            for username in valid_users:
                user = mongodb.find_one('users', {'username': username})
                if user and user.get('email'):
                    self.notification_service.notify_ticket_assignment(ticket, user['email'])
            
            logger.info(f"Ticket mehrfach zugewiesen: {ticket_id} -> {valid_users} von {assigned_by}")
            return True, f'Ticket erfolgreich {len(valid_users)} Benutzern zugewiesen'
            
        except Exception as e:
            logger.error(f"Fehler beim Mehrfachzuweisen des Tickets: [Interner Fehler]")
            return False, f'Fehler beim Zuweisen: [Interner Fehler]'
    
    def get_ticket_assignments(self, ticket_id: str) -> List[Dict[str, Any]]:
        """
        Holt alle Zuweisungen für ein Ticket
        
        Args:
            ticket_id: Ticket-ID
            
        Returns:
            Liste der Zuweisungen
        """
        try:
            assignments = mongodb.find('ticket_assignments', {'ticket_id': ticket_id})
            return list(assignments)
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Zuweisungen: [Interner Fehler]")
            return []
    
    def get_assigned_users(self, ticket_id: str) -> List[str]:
        """
        Holt alle zugewiesenen Benutzer für ein Ticket
        
        Args:
            ticket_id: Ticket-ID
            
        Returns:
            Liste der Benutzernamen
        """
        assignments = self.get_ticket_assignments(ticket_id)
        return [assignment['assigned_to'] for assignment in assignments]
    
    def add_message_to_ticket(self, ticket_id: str, message: str, author: str) -> Tuple[bool, str]:
        """
        Fügt eine Nachricht zu einem Ticket hinzu
        
        Args:
            ticket_id: Ticket-ID
            message: Nachricht
            author: Autor der Nachricht
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            # Nachricht erstellen
            message_data = {
                'ticket_id': ticket_id,
                'message': message,
                'author': author,
                'created_at': datetime.now()
            }
            
            mongodb.insert_one('ticket_messages', message_data)
            
            # Ticket aktualisieren
            mongodb.update_one('tickets', 
                             {'_id': self.utility_service.convert_id_for_query(ticket_id)}, 
                             {'$set': {'updated_at': datetime.now()}})
            
            logger.info(f"Nachricht zu Ticket hinzugefügt: {ticket_id} von {author}")
            return True, 'Nachricht erfolgreich hinzugefügt'
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Nachricht: [Interner Fehler]")
            return False, f'Fehler beim Hinzufügen: [Interner Fehler]'
    
    def get_ticket_messages(self, ticket_id: str) -> List[Dict[str, Any]]:
        """
        Holt alle Nachrichten zu einem Ticket
        
        Args:
            ticket_id: Ticket-ID
            
        Returns:
            List: Liste der Nachrichten
        """
        try:
            messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id})
            messages = list(messages)
            
            # Datetime-Felder konvertieren
            for message in messages:
                message = self._convert_datetime_fields(message)
            
            # Nach Datum sortieren
            messages.sort(key=lambda x: x.get('created_at', datetime.min))
            
            return messages
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Nachrichten: [Interner Fehler]")
            return []
    
    def delete_ticket(self, ticket_id: str, deleted_by: str, permanent: bool = False) -> Tuple[bool, str]:
        """
        Löscht ein Ticket (soft oder permanent)
        
        Args:
            ticket_id: Ticket-ID
            deleted_by: Benutzername des Löschers
            permanent: True für permanente Löschung
            
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'
            
            if permanent:
                # Permanente Löschung
                mongodb.delete_one('tickets', {'_id': self.utility_service.convert_id_for_query(ticket_id)})
                # Auch alle zugehörigen Nachrichten löschen
                mongodb.delete_many('ticket_messages', {'ticket_id': ticket_id})
                mongodb.delete_many('ticket_notes', {'ticket_id': ticket_id})
                mongodb.delete_many('auftrag_details', {'ticket_id': ticket_id})
                
                logger.info(f"Ticket permanent gelöscht: {ticket_id} von {deleted_by}")
                return True, 'Ticket permanent gelöscht'
            else:
                # Soft-Delete
                mongodb.update_one('tickets', 
                                 {'_id': self.utility_service.convert_id_for_query(ticket_id)}, 
                                 {'$set': {
                                     'deleted': True,
                                     'deleted_at': datetime.now(),
                                     'deleted_by': deleted_by
                                 }})
                
                logger.info(f"Ticket soft-gelöscht: {ticket_id} von {deleted_by}")
                return True, 'Ticket gelöscht'
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Tickets: [Interner Fehler]")
            return False, f'Fehler beim Löschen: [Interner Fehler]'
    
    def get_unassigned_ticket_count(self) -> int:
        """
        Gibt die Anzahl der nicht zugewiesenen Tickets zurück
        
        Returns:
            int: Anzahl der nicht zugewiesenen Tickets
        """
        try:
            count = mongodb.count_documents('tickets', {
                '$and': [
                    {
                        '$or': [
                            {'assigned_to': None},
                            {'assigned_to': ''},
                            {'assigned_to': {'$exists': False}}
                        ]
                    },
                    {'status': 'offen'},
                    {'deleted': {'$ne': True}}
                ]
            })
            return count
            
        except Exception as e:
            logger.error(f"Fehler beim Zählen der nicht zugewiesenen Tickets: [Interner Fehler]")
            return 0

    def update_responsible(self, ticket_id: str, responsible_username: Optional[str], updated_by: str) -> Tuple[bool, str]:
        """
        Setzt oder entfernt die verantwortliche Person (Ticket-Leitung)
        
        Args:
            ticket_id: Ticket-ID
            responsible_username: Benutzername der verantwortlichen Person oder None zum Entfernen
            updated_by: Benutzername der ändernden Person
        
        Returns:
            Tuple: (success, message)
        """
        try:
            ticket = self.get_ticket_by_id(ticket_id)
            if not ticket:
                return False, 'Ticket nicht gefunden'

            # Optional: Validierung des Users, falls gesetzt
            if responsible_username:
                user = mongodb.find_one('users', {'username': responsible_username})
                if not user:
                    return False, 'Verantwortliche Person nicht gefunden'

            mongodb.update_one('tickets',
                             {'_id': self.utility_service.convert_id_for_query(ticket_id)},
                             {'$set': {
                                 'responsible': responsible_username or None,
                                 'updated_at': datetime.now(),
                                 'updated_by': updated_by
                             }})

            # Wenn eine verantwortliche Person gesetzt wurde, stelle sicher, dass sie zugewiesen ist
            if responsible_username:
                try:
                    # Legacy-Feld setzen
                    mongodb.update_one('tickets',
                                     {'_id': self.utility_service.convert_id_for_query(ticket_id)},
                                     {'$set': {
                                         'assigned_to': responsible_username,
                                         'updated_at': datetime.now(),
                                         'updated_by': updated_by
                                     }})
                    # In Mehrfachzuweisungen hinzufügen, falls noch nicht vorhanden
                    ticket_id_for_assign = str(self.utility_service.convert_id_for_query(ticket_id))
                    existing = mongodb.find_one('ticket_assignments', {
                        '$and': [
                            {'assigned_to': responsible_username},
                            {'$or': [
                                {'ticket_id': ticket_id_for_assign},
                                {'ticket_id': ticket_id}
                            ]}
                        ]
                    })
                    if not existing:
                        mongodb.insert_one('ticket_assignments', {
                            'ticket_id': ticket_id_for_assign,
                            'assigned_to': responsible_username,
                            'assigned_by': updated_by,
                            'assigned_at': datetime.now()
                        })
                except Exception as assign_err:
                    logger.error(f"Fehler beim automatischen Zuweisen der verantwortlichen Person: {assign_err}")

            # History-Logging
            try:
                from app.services.ticket_history_service import ticket_history_service
                ticket_history_service.log_assignment(
                    ticket_id=str(ticket_id),
                    old_assignee=ticket.get('responsible') or 'Nicht gesetzt',
                    new_assignee=responsible_username or 'Nicht gesetzt',
                    changed_by=updated_by
                )
            except Exception as history_error:
                logger.error(f"Fehler beim History-Logging für Verantwortliche: {history_error}")

            return True, 'Verantwortliche Person wurde aktualisiert'
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der verantwortlichen Person: [Interner Fehler]")
            return False, f'Fehler beim Aktualisieren: [Interner Fehler]'
    
    def _convert_datetime_fields(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Konvertiert datetime-Strings zu datetime-Objekten
        
        Args:
            ticket: Ticket-Daten
            
        Returns:
            Dict: Ticket mit konvertierten Datetime-Feldern
        """
        date_fields = ['created_at', 'updated_at', 'due_date', 'deleted_at']
        for field in date_fields:
            if ticket.get(field):
                if isinstance(ticket[field], str):
                    try:
                        # Versuche verschiedene Datumsformate zu parsen
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                ticket[field] = datetime.strptime(ticket[field], fmt)
                                break
                            except ValueError:
                                continue
                    except:
                        # Wenn alle Formate fehlschlagen, setze auf None
                        ticket[field] = None
                elif isinstance(ticket[field], datetime):
                    # Bereits ein datetime-Objekt, nichts zu tun
                    pass
                else:
                    # Versuche es als datetime zu konvertieren
                    try:
                        ticket[field] = datetime.fromisoformat(str(ticket[field]))
                    except:
                        # Wenn Konvertierung fehlschlägt, setze auf None
                        ticket[field] = None
            else:
                # Feld ist None oder nicht vorhanden, setze auf None
                ticket[field] = None
        return ticket 