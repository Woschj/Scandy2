"""
Verbessertes Feature-System für Scandy

Dieses Modul implementiert ein department-scoped Feature-System,
das Features pro Abteilung verwaltet und persistent speichert.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from flask import g
import logging
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class FeatureSystem:
    """Department-scoped Feature-System"""
    
    # Kern-Features, die immer aktiviert sein sollten
    CORE_FEATURES = {
        'tools', 'consumables', 'workers', 'lending_system'
    }
    
    # Standard-Feature-Einstellungen
    DEFAULT_FEATURES = {
        'tools': True,
        'consumables': True,
        'workers': True,
        'lending_system': True,
        'ticket_system': True,
        'timesheet': True,
        'media_management': True,
        'software_management': False,
        'job_board': True,
        'weekly_reports': False,
        'canteen_plan': False,
        # Werkzeug-Felder
        'tool_field_serial_number': True,
        'tool_field_invoice_number': True,
        'tool_field_mac_address': True,
        'tool_field_mac_address_wlan': True,
        'tool_field_user_groups': True,
        'tool_field_software': True
    }
    
    @classmethod
    def get_current_department(cls) -> Optional[str]:
        """Holt das aktuelle Department aus dem Request-Context"""
        try:
            return getattr(g, 'current_department', None)
        except Exception:
            return None
    
    @classmethod
    def get_feature_settings(cls, department: Optional[str] = None) -> Dict[str, bool]:
        """
        Holt Feature-Einstellungen für eine bestimmte Abteilung
        
        Args:
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            Dictionary mit Feature-Name -> Enabled-Status
        """
        if department is None:
            department = cls.get_current_department()
        
        try:
            # Lade department-spezifische Features
            if department:
                settings = {}
                rows = mongodb.find('feature_settings', {'department': department})
                
                for row in rows:
                    feature_name = row.get('feature_name')
                    if feature_name:
                        settings[feature_name] = row.get('enabled', False)
                
                # Kombiniere mit Standard-Einstellungen
                result = cls.DEFAULT_FEATURES.copy()
                result.update(settings)
                
                # Kern-Features immer aktiviert
                for feature in cls.CORE_FEATURES:
                    result[feature] = True
                
                return result
            else:
                # Kein Department: Standard-Einstellungen
                return cls.DEFAULT_FEATURES.copy()
                
        except Exception as e:
            logger.error(f"Fehler beim Laden der Feature-Einstellungen für {department}: [Interner Fehler]")
            return cls.DEFAULT_FEATURES.copy()
    
    @classmethod
    def set_feature_setting(cls, feature_name: str, enabled: bool, department: Optional[str] = None) -> bool:
        """
        Setzt eine Feature-Einstellung für eine bestimmte Abteilung
        
        Args:
            feature_name: Name des Features
            enabled: Aktiviert/Deaktiviert
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.error("Kein Department verfügbar für Feature-Einstellung")
            return False
        
        try:
            # Prüfe ob Feature bereits existiert
            existing = mongodb.find_one('feature_settings', {
                'feature_name': feature_name,
                'department': department
            })
            
            if existing:
                # Update bestehende Einstellung
                mongodb.update_one('feature_settings', 
                                 {'_id': existing['_id']}, 
                                 {'$set': {'enabled': enabled, 'updated_at': datetime.now()}})
            else:
                # Neue Einstellung erstellen
                mongodb.insert_one('feature_settings', {
                    'feature_name': feature_name,
                    'department': department,
                    'enabled': enabled,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
            
            logger.info(f"Feature {feature_name} für {department} auf {enabled} gesetzt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Setzen der Feature-Einstellung {feature_name} für {department}: [Interner Fehler]")
            return False
    
    @classmethod
    def is_feature_enabled(cls, feature_name: str, department: Optional[str] = None) -> bool:
        """
        Prüft ob ein Feature für eine bestimmte Abteilung aktiviert ist
        
        Args:
            feature_name: Name des Features
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            True wenn aktiviert, False sonst
        """
        if department is None:
            department = cls.get_current_department()
        
        # Kern-Features sind immer aktiviert
        if feature_name in cls.CORE_FEATURES:
            return True
        
        try:
            if department:
                # Lade department-spezifische Einstellung
                setting = mongodb.find_one('feature_settings', {
                    'feature_name': feature_name,
                    'department': department
                })
                
                if setting is not None:
                    return setting.get('enabled', False)
            
            # Fallback zu Standard-Einstellung
            return cls.DEFAULT_FEATURES.get(feature_name, False)
            
        except Exception as e:
            logger.error(f"Fehler beim Prüfen der Feature-Einstellung {feature_name} für {department}: [Interner Fehler]")
            return cls.DEFAULT_FEATURES.get(feature_name, False)
    
    @classmethod
    def get_all_department_features(cls) -> Dict[str, Dict[str, bool]]:
        """
        Holt alle Feature-Einstellungen für alle Abteilungen
        
        Returns:
            Dictionary mit Department -> Feature-Name -> Enabled-Status
        """
        try:
            # Lade alle Abteilungen
            depts_setting = mongodb.find_one('settings', {'key': 'departments'})
            departments = depts_setting.get('value', []) if depts_setting else []
            
            result = {}
            for dept in departments:
                if isinstance(dept, str) and dept.strip():
                    result[dept] = cls.get_feature_settings(dept)
            
            return result
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aller Department-Features: [Interner Fehler]")
            return {}
    
    @classmethod
    def reset_department_features(cls, department: str) -> bool:
        """
        Setzt alle Features einer Abteilung auf Standard-Werte zurück
        
        Args:
            department: Abteilung
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            # Lösche alle bestehenden Einstellungen für diese Abteilung
            mongodb.delete_many('feature_settings', {'department': department})
            
            logger.info(f"Features für {department} auf Standard-Werte zurückgesetzt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Zurücksetzen der Features für {department}: [Interner Fehler]")
            return False
    
    @classmethod
    def copy_features_from_department(cls, source_department: str, target_department: str) -> bool:
        """
        Kopiert Feature-Einstellungen von einer Abteilung zu einer anderen
        
        Args:
            source_department: Quell-Abteilung
            target_department: Ziel-Abteilung
            
        Returns:
            True wenn erfolgreich, False sonst
        """
        try:
            # Lade Features der Quell-Abteilung
            source_features = cls.get_feature_settings(source_department)
            
            # Kopiere zu Ziel-Abteilung
            for feature_name, enabled in source_features.items():
                if feature_name not in cls.CORE_FEATURES:  # Kern-Features nicht kopieren
                    cls.set_feature_setting(feature_name, enabled, target_department)
            
            logger.info(f"Features von {source_department} zu {target_department} kopiert")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Kopieren der Features von {source_department} zu {target_department}: [Interner Fehler]")
            return False

# Globale Instanz für einfache Verwendung
feature_system = FeatureSystem()

# Kompatibilitätsfunktionen für bestehenden Code
def get_feature_settings(department: Optional[str] = None) -> Dict[str, bool]:
    """Kompatibilitätsfunktion für bestehenden Code"""
    return FeatureSystem.get_feature_settings(department)

def set_feature_setting(feature_name: str, enabled: bool, department: Optional[str] = None) -> bool:
    """Kompatibilitätsfunktion für bestehenden Code"""
    return FeatureSystem.set_feature_setting(feature_name, enabled, department)

def is_feature_enabled(feature_name: str, department: Optional[str] = None) -> bool:
    """Kompatibilitätsfunktion für bestehenden Code"""
    return FeatureSystem.is_feature_enabled(feature_name, department)
