#!/usr/bin/env python3
"""
Ticket-History-Service für Scandy
Protokolliert alle Änderungen an Tickets für eine vollständige Historie
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)


class TicketHistoryService:
    """Service für die Verwaltung der Ticket-Historie"""
    
    def __init__(self):
        """Initialisiert den Ticket-History-Service"""
        self.collection_name = 'ticket_history'
    
    def log_change(self, ticket_id: str, field: str, old_value: Any, new_value: Any, 
                   changed_by: str, change_type: str = 'update', note: Optional[str] = None) -> bool:
        """
        Protokolliert eine Änderung an einem Ticket
        
        Args:
            ticket_id: ID des Tickets
            field: Geändertes Feld
            old_value: Alter Wert
            new_value: Neuer Wert
            changed_by: Benutzer der die Änderung vorgenommen hat
            change_type: Art der Änderung (create, update, delete, status_change, assign, etc.)
            note: Optionale Notiz zur Änderung
            
        Returns:
            bool: True wenn erfolgreich, False bei Fehler
        """
        try:
            # Konvertiere Werte zu String für einheitliche Speicherung
            old_str = self._format_value(old_value)
            new_str = self._format_value(new_value)
            
            # Überspringe Änderung wenn beide Werte identisch sind
            if old_str == new_str and change_type == 'update':
                return True
            
            history_entry = {
                'ticket_id': ticket_id,
                'field': field,
                'old_value': old_str,
                'new_value': new_str,
                'changed_by': changed_by,
                'change_type': change_type,
                'note': note,
                'changed_at': datetime.now(),
                'created_at': datetime.now()
            }
            
            result = mongodb.insert_one(self.collection_name, history_entry)
            if result:
                logger.info(f"Ticket-History erfasst: {ticket_id} - {field}: {old_str} -> {new_str} von {changed_by}")
                return True
            else:
                logger.error(f"Fehler beim Speichern der Ticket-History für {ticket_id}")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Protokollieren der Ticket-Änderung: {str(e)}", exc_info=True)
            return False
    
    def log_status_change(self, ticket_id: str, old_status: str, new_status: str, 
                         changed_by: str, note: Optional[str] = None) -> bool:
        """
        Protokolliert eine Status-Änderung
        
        Args:
            ticket_id: ID des Tickets
            old_status: Alter Status
            new_status: Neuer Status
            changed_by: Benutzer der die Änderung vorgenommen hat
            note: Optionale Notiz
            
        Returns:
            bool: True wenn erfolgreich
        """
        return self.log_change(
            ticket_id=ticket_id,
            field='status',
            old_value=old_status,
            new_value=new_status,
            changed_by=changed_by,
            change_type='status_change',
            note=note
        )
    
    def log_assignment(self, ticket_id: str, old_assignee: Optional[str], new_assignee: Optional[str], 
                      changed_by: str, note: Optional[str] = None) -> bool:
        """
        Protokolliert eine Zuweisungsänderung
        
        Args:
            ticket_id: ID des Tickets
            old_assignee: Alter Zugewiesener
            new_assignee: Neuer Zugewiesener
            changed_by: Benutzer der die Änderung vorgenommen hat
            note: Optionale Notiz
            
        Returns:
            bool: True wenn erfolgreich
        """
        return self.log_change(
            ticket_id=ticket_id,
            field='assigned_to',
            old_value=old_assignee or 'Nicht zugewiesen',
            new_value=new_assignee or 'Nicht zugewiesen',
            changed_by=changed_by,
            change_type='assignment',
            note=note
        )
    
    def log_creation(self, ticket_id: str, created_by: str, ticket_data: Dict[str, Any]) -> bool:
        """
        Protokolliert die Erstellung eines Tickets
        
        Args:
            ticket_id: ID des Tickets
            created_by: Ersteller des Tickets
            ticket_data: Ticket-Daten
            
        Returns:
            bool: True wenn erfolgreich
        """
        return self.log_change(
            ticket_id=ticket_id,
            field='ticket',
            old_value=None,
            new_value=f"Ticket erstellt: {ticket_data.get('title', 'Unbekannt')}",
            changed_by=created_by,
            change_type='create',
            note=f"Kategorie: {ticket_data.get('category', 'Unbekannt')}, Priorität: {ticket_data.get('priority', 'Normal')}"
        )
    
    def log_message_added(self, ticket_id: str, message: str, added_by: str) -> bool:
        """
        Protokolliert das Hinzufügen einer Nachricht
        
        Args:
            ticket_id: ID des Tickets
            message: Nachricht (gekürzt für History)
            added_by: Benutzer der die Nachricht hinzugefügt hat
            
        Returns:
            bool: True wenn erfolgreich
        """
        # Kürze Nachricht für History
        short_message = (message[:100] + '...') if len(message) > 100 else message
        
        return self.log_change(
            ticket_id=ticket_id,
            field='messages',
            old_value=None,
            new_value=f"Nachricht hinzugefügt: {short_message}",
            changed_by=added_by,
            change_type='message_added'
        )
    
    def log_note_added(self, ticket_id: str, note: str, added_by: str) -> bool:
        """
        Protokolliert das Hinzufügen einer Notiz
        
        Args:
            ticket_id: ID des Tickets
            note: Notiz (gekürzt für History)
            added_by: Benutzer der die Notiz hinzugefügt hat
            
        Returns:
            bool: True wenn erfolgreich
        """
        # Kürze Notiz für History
        short_note = (note[:100] + '...') if len(note) > 100 else note
        
        return self.log_change(
            ticket_id=ticket_id,
            field='notes',
            old_value=None,
            new_value=f"Notiz hinzugefügt: {short_note}",
            changed_by=added_by,
            change_type='note_added'
        )
    
    def log_bulk_update(self, ticket_id: str, updates: Dict[str, Any], 
                       old_values: Dict[str, Any], changed_by: str) -> bool:
        """
        Protokolliert mehrere Änderungen auf einmal
        
        Args:
            ticket_id: ID des Tickets
            updates: Neue Werte
            old_values: Alte Werte
            changed_by: Benutzer der die Änderungen vorgenommen hat
            
        Returns:
            bool: True wenn erfolgreich
        """
        success = True
        
        # Spezielle Behandlung für verschiedene Felder
        field_translations = {
            'title': 'Titel',
            'description': 'Beschreibung',
            'category': 'Kategorie',
            'priority': 'Priorität',
            'status': 'Status',
            'assigned_to': 'Zugewiesen an',
            'due_date': 'Fälligkeitsdatum',
            'estimated_time': 'Geschätzte Zeit'
        }
        
        for field, new_value in updates.items():
            if field in ['updated_at', 'updated_by']:  # Ignoriere Meta-Felder
                continue
                
            old_value = old_values.get(field)
            display_field = field_translations.get(field, field)
            
            if not self.log_change(ticket_id, display_field, old_value, new_value, changed_by):
                success = False
                
        return success
    
    def get_ticket_history(self, ticket_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Holt die Historie eines Tickets
        
        Args:
            ticket_id: ID des Tickets
            limit: Maximale Anzahl der Einträge
            
        Returns:
            Liste der History-Einträge (neueste zuerst)
        """
        try:
            history = list(mongodb.find(
                self.collection_name,
                {'ticket_id': ticket_id},
                sort=[('changed_at', -1)],
                limit=limit
            ))
            
            # Formatiere die Einträge für die Anzeige
            formatted_history = []
            for entry in history:
                formatted_entry = {
                    'id': str(entry.get('_id', '')),
                    'field': entry.get('field', ''),
                    'old_value': entry.get('old_value', ''),
                    'new_value': entry.get('new_value', ''),
                    'changed_by': entry.get('changed_by', ''),
                    'change_type': entry.get('change_type', 'update'),
                    'note': entry.get('note', ''),
                    'changed_at': entry.get('changed_at', datetime.now()),
                    'formatted_date': entry.get('changed_at', datetime.now()).strftime('%d.%m.%Y %H:%M')
                }
                formatted_history.append(formatted_entry)
            
            return formatted_history
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Ticket-Historie für {ticket_id}: {str(e)}")
            return []
    
    def _format_value(self, value: Any) -> str:
        """
        Formatiert einen Wert für die Anzeige in der Historie
        
        Args:
            value: Zu formatierender Wert
            
        Returns:
            Formatierter String
        """
        if value is None:
            return 'Leer'
        elif isinstance(value, bool):
            return 'Ja' if value else 'Nein'
        elif isinstance(value, datetime):
            return value.strftime('%d.%m.%Y %H:%M')
        elif isinstance(value, (list, tuple)):
            return ', '.join(str(v) for v in value)
        elif isinstance(value, dict):
            return str(value)
        else:
            return str(value)
    
    def get_user_activity(self, username: str, days: int = 30, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Holt die Aktivitäten eines Benutzers
        
        Args:
            username: Benutzername
            days: Anzahl der Tage rückwirkend
            limit: Maximale Anzahl der Einträge
            
        Returns:
            Liste der Aktivitäten des Benutzers
        """
        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)
            
            activity = list(mongodb.find(
                self.collection_name,
                {
                    'changed_by': username,
                    'changed_at': {'$gte': start_date}
                },
                sort=[('changed_at', -1)],
                limit=limit
            ))
            
            return activity
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Benutzer-Aktivitäten für {username}: {str(e)}")
            return []


# Globale Instanz
ticket_history_service = TicketHistoryService() 