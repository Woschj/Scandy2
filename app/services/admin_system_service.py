"""
Admin System Service

Dieser Service enthält alle Funktionen für die Systemverwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.models.mongodb_database import mongodb
from app.utils.database_helpers import get_categories_from_settings, get_ticket_categories_from_settings, get_departments_from_settings, get_locations_from_settings

logger = logging.getLogger(__name__)

class AdminSystemService:
    """Service für Admin-Systemverwaltungs-Funktionen"""
    
    @staticmethod
    def get_system_settings() -> Dict[str, Any]:
        """Hole alle Systemeinstellungen"""
        try:
            settings = {}
            rows = mongodb.find('settings', {})
            
            for row in rows:
                settings[row['key']] = row['value']
            
            return settings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Systemeinstellungen: {str(e)}")
            return {}

    @staticmethod
    def update_system_settings(settings_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert Systemeinstellungen
        
        Args:
            settings_data: Neue Einstellungen
            
        Returns:
            (success, message)
        """
        try:
            for key, value in settings_data.items():
                mongodb.update_one('settings', 
                                 {'key': key}, 
                                 {'$set': {'value': value}}, 
                                 upsert=True)
            
            logger.info("Systemeinstellungen aktualisiert")
            return True, "Systemeinstellungen erfolgreich gespeichert"
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Systemeinstellungen: {str(e)}")
            return False, f"Fehler beim Speichern der Systemeinstellungen: {str(e)}"

    @staticmethod
    def get_departments() -> List[str]:
        """Hole alle Abteilungen"""
        try:
            return get_departments_from_settings()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Abteilungen: {str(e)}")
            return []

    @staticmethod
    def add_department(department_name: str) -> Tuple[bool, str]:
        """
        Fügt eine neue Abteilung hinzu
        
        Args:
            department_name: Name der neuen Abteilung
            
        Returns:
            (success, message)
        """
        try:
            if not department_name or not department_name.strip():
                return False, "Abteilungsname ist erforderlich"
            
            department_name = department_name.strip()
            
            # Prüfe ob Abteilung bereits existiert
            departments = get_departments_from_settings()
            if department_name in departments:
                return False, f"Abteilung '{department_name}' existiert bereits"
            
            # Füge Abteilung hinzu
            departments.append(department_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'departments'}, 
                             {'$set': {'value': departments}}, 
                             upsert=True)
            
            logger.info(f"Neue Abteilung hinzugefügt: {department_name}")
            return True, f"Abteilung '{department_name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Abteilung {department_name}: {str(e)}")
            return False, f"Fehler beim Hinzufügen der Abteilung: {str(e)}"

    @staticmethod
    def delete_department(department_name: str) -> Tuple[bool, str]:
        """
        Löscht eine Abteilung
        
        Args:
            department_name: Name der zu löschenden Abteilung
            
        Returns:
            (success, message)
        """
        try:
            if not department_name:
                return False, "Abteilungsname ist erforderlich"
            
            # Prüfe ob Abteilung existiert
            departments = get_departments_from_settings()
            if department_name not in departments:
                return False, f"Abteilung '{department_name}' existiert nicht"
            
            # Prüfe ob Abteilung noch verwendet wird
            workers_with_dept = mongodb.count_documents('workers', {'department': department_name})
            if workers_with_dept > 0:
                return False, f"Abteilung '{department_name}' wird noch von {workers_with_dept} Mitarbeitern verwendet"
            
            # Entferne Abteilung
            departments.remove(department_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'departments'}, 
                             {'$set': {'value': departments}}, 
                             upsert=True)
            
            logger.info(f"Abteilung gelöscht: {department_name}")
            return True, f"Abteilung '{department_name}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Abteilung {department_name}: {str(e)}")
            return False, f"Fehler beim Löschen der Abteilung: {str(e)}"

    @staticmethod
    def get_categories() -> List[str]:
        """Hole alle Kategorien"""
        try:
            return get_categories_from_settings()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Kategorien: {str(e)}")
            return []

    @staticmethod
    def add_category(category_name: str) -> Tuple[bool, str]:
        """
        Fügt eine neue Kategorie hinzu
        
        Args:
            category_name: Name der neuen Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not category_name or not category_name.strip():
                return False, "Kategoriename ist erforderlich"
            
            category_name = category_name.strip()
            
            # Prüfe ob Kategorie bereits existiert
            categories = get_categories_from_settings()
            if category_name in categories:
                return False, f"Kategorie '{category_name}' existiert bereits"
            
            # Füge Kategorie hinzu
            categories.append(category_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'categories'}, 
                             {'$set': {'value': categories}}, 
                             upsert=True)
            
            logger.info(f"Neue Kategorie hinzugefügt: {category_name}")
            return True, f"Kategorie '{category_name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Kategorie {category_name}: {str(e)}")
            return False, f"Fehler beim Hinzufügen der Kategorie: {str(e)}"

    @staticmethod
    def delete_category(category_name: str) -> Tuple[bool, str]:
        """
        Löscht eine Kategorie
        
        Args:
            category_name: Name der zu löschenden Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not category_name:
                return False, "Kategoriename ist erforderlich"
            
            # Prüfe ob Kategorie existiert
            categories = get_categories_from_settings()
            if category_name not in categories:
                return False, f"Kategorie '{category_name}' existiert nicht"
            
            # Prüfe ob Kategorie noch verwendet wird
            tools_with_cat = mongodb.count_documents('tools', {'category': category_name})
            consumables_with_cat = mongodb.count_documents('consumables', {'category': category_name})
            
            if tools_with_cat > 0 or consumables_with_cat > 0:
                return False, f"Kategorie '{category_name}' wird noch verwendet ({tools_with_cat} Werkzeuge, {consumables_with_cat} Verbrauchsmaterialien)"
            
            # Entferne Kategorie
            categories.remove(category_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'categories'}, 
                             {'$set': {'value': categories}}, 
                             upsert=True)
            
            logger.info(f"Kategorie gelöscht: {category_name}")
            return True, f"Kategorie '{category_name}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Kategorie {category_name}: {str(e)}")
            return False, f"Fehler beim Löschen der Kategorie: {str(e)}"

    @staticmethod
    def get_locations() -> List[str]:
        """Hole alle Standorte"""
        try:
            return get_locations_from_settings()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Standorte: {str(e)}")
            return []

    @staticmethod
    def add_location(location_name: str) -> Tuple[bool, str]:
        """
        Fügt einen neuen Standort hinzu
        
        Args:
            location_name: Name des neuen Standorts
            
        Returns:
            (success, message)
        """
        try:
            if not location_name or not location_name.strip():
                return False, "Standortname ist erforderlich"
            
            location_name = location_name.strip()
            
            # Prüfe ob Standort bereits existiert
            locations = get_locations_from_settings()
            if location_name in locations:
                return False, f"Standort '{location_name}' existiert bereits"
            
            # Füge Standort hinzu
            locations.append(location_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'locations'}, 
                             {'$set': {'value': locations}}, 
                             upsert=True)
            
            logger.info(f"Neuer Standort hinzugefügt: {location_name}")
            return True, f"Standort '{location_name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Standorts {location_name}: {str(e)}")
            return False, f"Fehler beim Hinzufügen des Standorts: {str(e)}"

    @staticmethod
    def delete_location(location_name: str) -> Tuple[bool, str]:
        """
        Löscht einen Standort
        
        Args:
            location_name: Name des zu löschenden Standorts
            
        Returns:
            (success, message)
        """
        try:
            if not location_name:
                return False, "Standortname ist erforderlich"
            
            # Prüfe ob Standort existiert
            locations = get_locations_from_settings()
            if location_name not in locations:
                return False, f"Standort '{location_name}' existiert nicht"
            
            # Prüfe ob Standort noch verwendet wird
            tools_with_loc = mongodb.count_documents('tools', {'location': location_name})
            consumables_with_loc = mongodb.count_documents('consumables', {'location': location_name})
            
            if tools_with_loc > 0 or consumables_with_loc > 0:
                return False, f"Standort '{location_name}' wird noch verwendet ({tools_with_loc} Werkzeuge, {consumables_with_loc} Verbrauchsmaterialien)"
            
            # Entferne Standort
            locations.remove(location_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'locations'}, 
                             {'$set': {'value': locations}}, 
                             upsert=True)
            
            logger.info(f"Standort gelöscht: {location_name}")
            return True, f"Standort '{location_name}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Standorts {location_name}: {str(e)}")
            return False, f"Fehler beim Löschen des Standorts: {str(e)}"

    @staticmethod
    def get_ticket_categories() -> List[str]:
        """Hole alle Ticket-Kategorien"""
        try:
            return get_ticket_categories_from_settings()
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Kategorien: {str(e)}")
            return []

    @staticmethod
    def add_ticket_category(category_name: str) -> Tuple[bool, str]:
        """
        Fügt eine neue Ticket-Kategorie hinzu
        
        Args:
            category_name: Name der neuen Ticket-Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not category_name or not category_name.strip():
                return False, "Kategoriename ist erforderlich"
            
            category_name = category_name.strip()
            
            # Prüfe ob Kategorie bereits existiert
            categories = get_ticket_categories_from_settings()
            if category_name in categories:
                return False, f"Ticket-Kategorie '{category_name}' existiert bereits"
            
            # Füge Kategorie hinzu
            categories.append(category_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'ticket_categories'}, 
                             {'$set': {'value': categories}}, 
                             upsert=True)
            
            logger.info(f"Neue Ticket-Kategorie hinzugefügt: {category_name}")
            return True, f"Ticket-Kategorie '{category_name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie {category_name}: {str(e)}")
            return False, f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}"

    @staticmethod
    def delete_ticket_category(category_name: str) -> Tuple[bool, str]:
        """
        Löscht eine Ticket-Kategorie
        
        Args:
            category_name: Name der zu löschenden Ticket-Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not category_name:
                return False, "Kategoriename ist erforderlich"
            
            # Prüfe ob Kategorie existiert
            categories = get_ticket_categories_from_settings()
            if category_name not in categories:
                return False, f"Ticket-Kategorie '{category_name}' existiert nicht"
            
            # Prüfe ob Kategorie noch verwendet wird
            tickets_with_cat = mongodb.count_documents('tickets', {'category': category_name})
            
            if tickets_with_cat > 0:
                return False, f"Ticket-Kategorie '{category_name}' wird noch von {tickets_with_cat} Tickets verwendet"
            
            # Entferne Kategorie
            categories.remove(category_name)
            
            # Speichere in Datenbank
            mongodb.update_one('settings', 
                             {'key': 'ticket_categories'}, 
                             {'$set': {'value': categories}}, 
                             upsert=True)
            
            logger.info(f"Ticket-Kategorie gelöscht: {category_name}")
            return True, f"Ticket-Kategorie '{category_name}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Ticket-Kategorie {category_name}: {str(e)}")
            return False, f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}"

    @staticmethod
    def get_system_statistics() -> Dict[str, Any]:
        """Hole Systemstatistiken"""
        try:
            # Zähle verschiedene Datentypen
            total_tools = mongodb.count_documents('tools', {'deleted': {'$ne': True}})
            total_consumables = mongodb.count_documents('consumables', {'deleted': {'$ne': True}})
            total_workers = mongodb.count_documents('workers', {'deleted': {'$ne': True}})
            total_users = mongodb.count_documents('users', {})
            total_tickets = mongodb.count_documents('tickets', {})
            
            # Zähle aktive Ausleihen
            active_lendings = mongodb.count_documents('lendings', {'returned_at': None})
            
            # Zähle defekte Werkzeuge
            defect_tools = mongodb.count_documents('tools', {'status': 'defekt', 'deleted': {'$ne': True}})
            
            # Zähle Verbrauchsmaterial mit niedrigem Bestand
            low_stock_consumables = mongodb.count_documents('consumables', {
                'quantity': {'$lt': 5},
                'deleted': {'$ne': True}
            })
            
            return {
                'total_tools': total_tools,
                'total_consumables': total_consumables,
                'total_workers': total_workers,
                'total_users': total_users,
                'total_tickets': total_tickets,
                'active_lendings': active_lendings,
                'defect_tools': defect_tools,
                'low_stock_consumables': low_stock_consumables
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Systemstatistiken: {str(e)}")
            return {
                'total_tools': 0,
                'total_consumables': 0,
                'total_workers': 0,
                'total_users': 0,
                'total_tickets': 0,
                'active_lendings': 0,
                'defect_tools': 0,
                'low_stock_consumables': 0
            }

    @staticmethod
    def get_system_data() -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Gibt Systemeinstellungen und App-Labels zurück
        
        Returns:
            (settings, app_labels)
        """
        try:
            # Hole alle Systemeinstellungen
            settings = AdminSystemService.get_system_settings()
            
            # Hole App-Labels (beide Systeme berücksichtigen)
            app_labels = {
                'tools': {
                    'name': settings.get('app_label_tools_name') or settings.get('label_tools_name', 'Werkzeuge'),
                    'icon': settings.get('app_label_tools_icon') or settings.get('label_tools_icon', 'fas fa-tools')
                },
                'consumables': {
                    'name': settings.get('app_label_consumables_name') or settings.get('label_consumables_name', 'Verbrauchsmaterial'),
                    'icon': settings.get('app_label_consumables_icon') or settings.get('label_consumables_icon', 'fas fa-box')
                },
                'tickets': {
                    'name': settings.get('app_label_tickets_name') or settings.get('label_tickets_name', 'Tickets'),
                    'icon': settings.get('app_label_tickets_icon') or settings.get('label_tickets_icon', 'fas fa-ticket-alt')
                }
            }
            
            return settings, app_labels
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Systemdaten: {str(e)}")
            return {}, {
                'tools': {'name': 'Werkzeuge', 'icon': 'fas fa-tools'},
                'consumables': {'name': 'Verbrauchsmaterial', 'icon': 'fas fa-box'},
                'tickets': {'name': 'Tickets', 'icon': 'fas fa-ticket-alt'}
            }

    @staticmethod
    def save_app_labels(app_labels: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Speichert App-Labels
        
        Args:
            app_labels: App-Labels zum Speichern
            
        Returns:
            (success, message)
        """
        try:
            # Mappe App-Labels auf Datenbankfelder (beide Systeme synchron halten)
            settings_data = {}
            
            for category, data in app_labels.items():
                if 'name' in data:
                    # Neue Keys für Systemeinstellungen
                    settings_data[f'app_label_{category}_name'] = data['name']
                    # Alte Keys für Kompatibilität
                    settings_data[f'label_{category}_name'] = data['name']
                if 'icon' in data:
                    # Neue Keys für Systemeinstellungen
                    settings_data[f'app_label_{category}_icon'] = data['icon']
                    # Alte Keys für Kompatibilität
                    settings_data[f'label_{category}_icon'] = data['icon']
            
            success, message = AdminSystemService.update_system_settings(settings_data)
            return success, message
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der App-Labels: {str(e)}")
            return False, f"Fehler beim Speichern der App-Labels: {str(e)}"

    @staticmethod
    def get_available_logos() -> List[Dict[str, str]]:
        """
        Gibt verfügbare Logos zurück
        
        Returns:
            Liste der verfügbaren Logos
        """
        try:
            import os
            from flask import current_app
            
            logos = []
            logo_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
            
            if os.path.exists(logo_dir):
                for filename in os.listdir(logo_dir):
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                        logos.append({
                            'filename': filename,
                            'url': f'/static/uploads/logos/{filename}'
                        })
            
            return logos
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der verfügbaren Logos: {str(e)}")
            return [] 