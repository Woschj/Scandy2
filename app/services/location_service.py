"""
Service für Standorte-Verwaltung

Dieser Service verwaltet Standorte pro Abteilung
und stellt sicher, dass Benutzer nur die Standorte ihrer Abteilung sehen.
"""

from typing import List, Dict, Any, Optional
from flask import g
import logging
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class LocationService:
    """Service für department-scoped Standorte"""
    
    @classmethod
    def get_current_department(cls) -> Optional[str]:
        """Holt das aktuelle Department aus dem Request-Context"""
        try:
            return getattr(g, 'current_department', None)
        except Exception:
            return None
    
    @classmethod
    def get_locations_for_department(cls, department: Optional[str] = None) -> List[str]:
        """
        Holt Standorte für eine bestimmte Abteilung
        
        Args:
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            Liste der Standorte für die Abteilung
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.warning("Kein Department verfügbar für Standorte")
            return []
        
        try:
            # Lade department-spezifische Standorte
            locations = mongodb.find('locations', {
                'department': department,
                'deleted': {'$ne': True}
            })
            
            location_names = []
            for location in locations:
                name = location.get('name', '').strip()
                if name:
                    location_names.append(name)
            
            # Kein Fallback mehr: Standorte sind strikt abteilungsgebunden
            
            return sorted(location_names, key=str.casefold)
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Standorte für {department}: {str(e)}")
            return []
    
    @classmethod
    def get_all_department_locations(cls) -> Dict[str, List[str]]:
        """
        Holt alle Standorte für alle Abteilungen
        
        Returns:
            Dictionary mit Department -> Standorte-Liste
        """
        try:
            # Lade alle Abteilungen
            depts_setting = mongodb.find_one('settings', {'key': 'departments'})
            departments = depts_setting.get('value', []) if depts_setting else []
            
            result = {}
            for dept in departments:
                if isinstance(dept, str) and dept.strip():
                    result[dept] = cls.get_locations_for_department(dept)
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aller Department-Standorte: {str(e)}")
            return {}
    
    @classmethod
    def create_location(cls, name: str, department: Optional[str] = None) -> bool:
        """
        Erstellt einen neuen Standort für eine Abteilung
        
        Args:
            name: Name des Standorts
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Standort-Erstellung")
            return False
        
        if not name or not name.strip():
            logger.error("Standort-Name ist erforderlich")
            return False
        
        try:
            # Prüfe ob bereits existiert
            existing = mongodb.find_one('locations', {
                'name': name.strip(),
                'department': department,
                'deleted': {'$ne': True}
            })
            
            if existing:
                logger.warning(f"Standort '{name}' existiert bereits in {department}")
                return False
            
            # Erstelle neuen Standort
            from datetime import datetime
            location_data = {
                'name': name.strip(),
                'department': department,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'deleted': False
            }
            
            mongodb.insert_one('locations', location_data)
            logger.info(f"Standort '{name}' für {department} erstellt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Standorts '{name}' für {department}: {str(e)}")
            return False
    
    @classmethod
    def update_location(cls, old_name: str, new_name: str, department: Optional[str] = None) -> bool:
        """
        Aktualisiert einen Standort
        
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
            logger.error("Kein Department verfügbar für Standort-Update")
            return False
        
        try:
            # Update Standort
            from datetime import datetime
            result = mongodb.update_one('locations', 
                                      {'name': old_name, 'department': department, 'deleted': {'$ne': True}}, 
                                      {'$set': {
                                          'name': new_name.strip(),
                                          'updated_at': datetime.now()
                                      }})
            
            if result:
                logger.info(f"Standort '{old_name}' zu '{new_name}' in {department} aktualisiert")
                return True
            else:
                logger.warning(f"Standort '{old_name}' in {department} nicht gefunden")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Standorts '{old_name}' in {department}: {str(e)}")
            return False
    
    @classmethod
    def delete_location(cls, name: str, department: Optional[str] = None) -> bool:
        """
        Löscht einen Standort (Soft-Delete)
        
        Args:
            name: Name des Standorts
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Standort-Löschung")
            return False
        
        try:
            # Soft-Delete Standort
            from datetime import datetime
            result = mongodb.update_one('locations', 
                                      {'name': name, 'department': department, 'deleted': {'$ne': True}}, 
                                      {'$set': {
                                          'deleted': True,
                                          'deleted_at': datetime.now(),
                                          'updated_at': datetime.now()
                                      }})
            
            if result:
                logger.info(f"Standort '{name}' in {department} gelöscht")
                return True
            else:
                logger.warning(f"Standort '{name}' in {department} nicht gefunden")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Standorts '{name}' in {department}: {str(e)}")
            return False

# Globale Instanz für einfache Verwendung
location_service = LocationService()
