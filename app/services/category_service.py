"""
Service für Kategorien-Verwaltung

Dieser Service verwaltet Kategorien pro Abteilung
und stellt sicher, dass Nutzende nur die Kategorien ihrer Abteilung sehen.
"""

from typing import List, Dict, Any, Optional
from flask import g
import logging
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class CategoryService:
    """Service für department-scoped Kategorien"""
    
    @classmethod
    def get_current_department(cls) -> Optional[str]:
        """Holt das aktuelle Department aus dem Request-Context"""
        try:
            return getattr(g, 'current_department', None)
        except Exception:
            return None
    
    @classmethod
    def get_categories_for_department(cls, department: Optional[str] = None) -> List[str]:
        """
        Holt Kategorien für eine bestimmte Abteilung
        
        Args:
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            Liste der Kategorien für die Abteilung
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.warning("Kein Department verfügbar für Kategorien")
            return []
        
        try:
            # Lade department-spezifische Kategorien
            categories = mongodb.find('categories', {
                'department': department,
                'deleted': {'$ne': True}
            })
            
            category_names = []
            for category in categories:
                name = category.get('name', '').strip()
                if name:
                    category_names.append(name)
            
            # Kein Fallback mehr: Kategorien sind strikt abteilungsgebunden
            
            return sorted(category_names, key=str.casefold)
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Kategorien für {department}: {e}")
            return []
    
    @classmethod
    def get_all_department_categories(cls) -> Dict[str, List[str]]:
        """
        Holt alle Kategorien für alle Abteilungen
        
        Returns:
            Dictionary mit Department -> Kategorien-Liste
        """
        try:
            # Lade alle Abteilungen
            depts_setting = mongodb.find_one('settings', {'key': 'departments'})
            departments = depts_setting.get('value', []) if depts_setting else []
            
            result = {}
            for dept in departments:
                if isinstance(dept, str) and dept.strip():
                    result[dept] = cls.get_categories_for_department(dept)
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aller Department-Kategorien: {e}")
            return {}
    
    @classmethod
    def create_category(cls, name: str, department: Optional[str] = None) -> bool:
        """
        Erstellt eine neue Kategorie für eine Abteilung
        
        Args:
            name: Name der Kategorie
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Kategorie-Erstellung")
            return False
        
        if not name or not name.strip():
            logger.error("Kategorie-Name ist erforderlich")
            return False
        
        try:
            # Prüfe ob bereits existiert
            existing = mongodb.find_one('categories', {
                'name': name.strip(),
                'department': department,
                'deleted': {'$ne': True}
            })
            
            if existing:
                logger.warning(f"Kategorie '{name}' existiert bereits in {department}")
                return False
            
            # Erstelle neue Kategorie
            from datetime import datetime
            category_data = {
                'name': name.strip(),
                'department': department,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'deleted': False
            }
            
            mongodb.insert_one('categories', category_data)
            logger.info(f"Kategorie '{name}' für {department} erstellt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Kategorie '{name}' für {department}: {e}")
            return False
    
    @classmethod
    def update_category(cls, old_name: str, new_name: str, department: Optional[str] = None) -> bool:
        """
        Aktualisiert eine Kategorie
        
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
            logger.error("Kein Department verfügbar für Kategorie-Update")
            return False
        
        try:
            # Update Kategorie
            from datetime import datetime
            result = mongodb.update_one('categories', 
                                      {'name': old_name, 'department': department, 'deleted': {'$ne': True}}, 
                                      {'$set': {
                                          'name': new_name.strip(),
                                          'updated_at': datetime.now()
                                      }})
            
            if result:
                logger.info(f"Kategorie '{old_name}' zu '{new_name}' in {department} aktualisiert")
                return True
            else:
                logger.warning(f"Kategorie '{old_name}' in {department} nicht gefunden")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Kategorie '{old_name}' in {department}: {e}")
            return False
    
    @classmethod
    def delete_category(cls, name: str, department: Optional[str] = None) -> bool:
        """
        Löscht eine Kategorie (Soft-Delete)
        
        Args:
            name: Name der Kategorie
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Kategorie-Löschung")
            return False
        
        try:
            # Soft-Delete Kategorie
            from datetime import datetime
            result = mongodb.update_one('categories', 
                                      {'name': name, 'department': department, 'deleted': {'$ne': True}}, 
                                      {'$set': {
                                          'deleted': True,
                                          'deleted_at': datetime.now(),
                                          'updated_at': datetime.now()
                                      }})
            
            if result:
                logger.info(f"Kategorie '{name}' in {department} gelöscht")
                return True
            else:
                logger.warning(f"Kategorie '{name}' in {department} nicht gefunden")
                return False
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Kategorie '{name}' in {department}: {e}")
            return False

# Globale Instanz für einfache Verwendung
category_service = CategoryService()
