"""
Service für Handlungsfeld-Verwaltung

Dieser Service verwaltet Handlungsfelder (Ticket-Kategorien) pro Abteilung
und stellt sicher, dass Benutzer nur die Handlungsfelder ihrer Abteilung sehen.
"""

from typing import List, Dict, Any, Optional
from flask import g
import logging
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class HandlungsfeldService:
    """Service für department-scoped Handlungsfelder"""
    
    @classmethod
    def get_current_department(cls) -> Optional[str]:
        """Holt das aktuelle Department aus dem Request-Context"""
        try:
            return getattr(g, 'current_department', None)
        except Exception:
            return None
    
    @classmethod
    def get_handlungsfelder_for_department(cls, department: Optional[str] = None) -> List[str]:
        """
        Holt Handlungsfelder für eine bestimmte Abteilung
        
        Args:
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            Liste der Handlungsfelder für die Abteilung
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.warning("Kein Department verfügbar für Handlungsfelder")
            return []
        
        try:
            # Lade department-spezifische Ticket-Kategorien
            categories = mongodb.find('ticket_categories', {
                'department': department,
                'deleted': {'$ne': True}
            })
            
            # Nur strikt abteilungsgebundene Felder, keine Fallbacks
            handlungsfelder_set = set()
            for category in categories:
                name = (category.get('name') or '').strip()
                if name:
                    handlungsfelder_set.add(name)
            return sorted(handlungsfelder_set, key=str.casefold)
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Handlungsfelder für {department}: {e}")
            return []
    
    @classmethod
    def get_all_department_handlungsfelder(cls) -> Dict[str, List[str]]:
        """
        Holt alle Handlungsfelder für alle Abteilungen
        
        Returns:
            Dictionary mit Department -> Handlungsfelder-Liste
        """
        try:
            # Lade alle Abteilungen
            depts_setting = mongodb.find_one('settings', {'key': 'departments'})
            departments = depts_setting.get('value', []) if depts_setting else []
            
            result = {}
            for dept in departments:
                if isinstance(dept, str) and dept.strip():
                    result[dept] = cls.get_handlungsfelder_for_department(dept)
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aller Department-Handlungsfelder: {e}")
            return {}
    
    @classmethod
    def create_handlungsfeld(cls, name: str, department: Optional[str] = None) -> bool:
        """
        Erstellt ein neues Handlungsfeld für eine Abteilung
        
        Args:
            name: Name des Handlungsfelds
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Handlungsfeld-Erstellung")
            return False
        
        if not name or not name.strip():
            logger.error("Handlungsfeld-Name ist erforderlich")
            return False
        
        try:
            # Prüfe ob bereits existiert
            existing = mongodb.find_one('ticket_categories', {
                'name': name.strip(),
                'department': department,
                'deleted': {'$ne': True}
            })
            
            if existing:
                logger.warning(f"Handlungsfeld '{name}' existiert bereits in {department}")
                return False
            
            # Erstelle neues Handlungsfeld
            from datetime import datetime
            handlungsfeld_data = {
                'name': name.strip(),
                'department': department,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'deleted': False
            }
            
            mongodb.insert_one('ticket_categories', handlungsfeld_data)
            logger.info(f"Handlungsfeld '{name}' für {department} erstellt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Handlungsfelds '{name}' für {department}: {e}")
            return False
    
    @classmethod
    def update_handlungsfeld(cls, old_name: str, new_name: str, department: Optional[str] = None) -> bool:
        """
        Aktualisiert ein Handlungsfeld
        
        Args:
            old_name: Alter Name
            new_name: Neuer Name
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Handlungsfeld-Update")
            return False
        
        try:
            # Update Handlungsfeld
            from datetime import datetime
            result = mongodb.update_one('ticket_categories', 
                                      {'name': old_name, 'department': department, 'deleted': {'$ne': True}}, 
                                      {'$set': {
                                          'name': new_name.strip(),
                                          'updated_at': datetime.now()
                                      }})
            
            if result:
                logger.info(f"Handlungsfeld '{old_name}' zu '{new_name}' in {department} aktualisiert")
                return True
            else:
                logger.warning(f"Handlungsfeld '{old_name}' in {department} nicht gefunden")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Handlungsfelds '{old_name}' in {department}: {e}")
            return False
    
    @classmethod
    def delete_handlungsfeld(cls, name: str, department: Optional[str] = None) -> bool:
        """
        Löscht ein Handlungsfeld (Soft-Delete)
        
        Args:
            name: Name des Handlungsfelds
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Handlungsfeld-Löschung")
            return False
        
        try:
            # Soft-Delete Handlungsfeld
            from datetime import datetime
            result = mongodb.update_one('ticket_categories', 
                                      {'name': name, 'department': department, 'deleted': {'$ne': True}}, 
                                      {'$set': {
                                          'deleted': True,
                                          'deleted_at': datetime.now(),
                                          'updated_at': datetime.now()
                                      }})
            
            if result:
                logger.info(f"Handlungsfeld '{name}' in {department} gelöscht")
                return True
            else:
                logger.warning(f"Handlungsfeld '{name}' in {department} nicht gefunden")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Handlungsfelds '{name}' in {department}: {e}")
            return False
    
    @classmethod
    def copy_handlungsfelder_from_department(cls, source_department: str, target_department: str) -> bool:
        """
        Kopiert Handlungsfelder von einer Abteilung zu einer anderen
        
        Args:
            source_department: Quell-Abteilung
            target_department: Ziel-Abteilung
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            source_handlungsfelder = cls.get_handlungsfelder_for_department(source_department)
            
            if not source_handlungsfelder:
                logger.warning(f"Keine Handlungsfelder in {source_department} gefunden")
                return False
            
            copied_count = 0
            for handlungsfeld in source_handlungsfelder:
                if cls.create_handlungsfeld(handlungsfeld, target_department):
                    copied_count += 1
            
            logger.info(f"{copied_count} Handlungsfelder von {source_department} zu {target_department} kopiert")
            return copied_count > 0
            
        except Exception as e:
            logger.error(f"Fehler beim Kopieren der Handlungsfelder von {source_department} zu {target_department}: {e}")
            return False

# Globale Instanz für einfache Verwendung
handlungsfeld_service = HandlungsfeldService()
