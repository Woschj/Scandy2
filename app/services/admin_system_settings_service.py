"""
Admin System Settings Service

Dieser Service enthält alle Funktionen für System-Einstellungen,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app
from app.models.mongodb_database import mongodb
from app.utils.id_helpers import find_document_by_id

logger = logging.getLogger(__name__)

class AdminSystemSettingsService:
    """Service für Admin-System-Einstellungen"""
    
    @staticmethod
    def get_departments_from_settings() -> List[str]:
        """
        Holt alle Abteilungen aus den Einstellungen
        
        Returns:
            Liste der Abteilungen
        """
        try:
            settings = mongodb.find_one('settings', {'key': 'departments'})
            if settings and 'value' in settings:
                return settings['value']
            return []
        except Exception as e:
            logger.error(f"Fehler beim Laden der Abteilungen: {str(e)}")
            return []

    @staticmethod
    def get_categories_from_settings() -> List[str]:
        """
        Holt alle Kategorien aus den Einstellungen
        
        Returns:
            Liste der Kategorien
        """
        try:
            # Kategorien sind abteilungs-spezifisch
            settings = mongodb.find_one('settings', {'key': 'categories'})
            if settings and 'value' in settings:
                return settings['value']
            return []
        except Exception as e:
            logger.error(f"Fehler beim Laden der Kategorien: {str(e)}")
            return []

    @staticmethod
    def get_locations_from_settings() -> List[str]:
        """
        Holt alle Standorte aus den Einstellungen
        
        Returns:
            Liste der Standorte
        """
        try:
            # Standorte sind abteilungs-spezifisch
            settings = mongodb.find_one('settings', {'key': 'locations'})
            if settings and 'value' in settings:
                return settings['value']
            return []
        except Exception as e:
            logger.error(f"Fehler beim Laden der Standorte: {str(e)}")
            return []

    @staticmethod
    def get_ticket_categories_from_settings() -> List[str]:
        """
        Holt alle Ticket-Kategorien aus den Einstellungen
        
        Returns:
            Liste der Ticket-Kategorien
        """
        try:
            # Ticket-Kategorien sind abteilungs-spezifisch
            settings = mongodb.find_one('settings', {'key': 'ticket_categories'})
            if settings and 'value' in settings:
                return settings['value']
            return []
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Kategorien: {str(e)}")
            return []

    @staticmethod
    def add_department(name: str) -> Tuple[bool, str]:
        """
        Fügt eine neue Abteilung hinzu
        
        Args:
            name: Name der Abteilung
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Abteilungsname darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Abteilung bereits existiert
            departments = AdminSystemSettingsService.get_departments_from_settings()
            if name in departments:
                return False, f"Abteilung '{name}' existiert bereits"
            
            # Füge Abteilung hinzu
            departments.append(name)
            departments.sort()  # Sortiere alphabetisch
            
            # Update oder Insert Einstellung
            mongodb.update_one('settings', {'key': 'departments'}, {
                '$set': {
                    'value': departments,
                    'updated_at': datetime.now()
                }
            }, upsert=True)
            
            logger.info(f"Abteilung '{name}' erfolgreich hinzugefügt")
            return True, f"Abteilung '{name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Abteilung '{name}': {str(e)}")
            return False, f"Fehler beim Hinzufügen der Abteilung: {str(e)}"

    @staticmethod
    def delete_department(name: str) -> Tuple[bool, str]:
        """
        Löscht eine Abteilung
        
        Args:
            name: Name der Abteilung
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Abteilungsname darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Abteilung existiert
            departments = AdminSystemSettingsService.get_departments_from_settings()
            if name not in departments:
                return False, f"Abteilung '{name}' nicht gefunden"
            # Kaskadierendes Löschen aller Daten dieser Abteilung
            deleted_counts: Dict[str, int] = {}
            try:
                # 1) IDs der Tickets der Abteilung sammeln (für Messages/History)
                ticket_ids = [t['_id'] for t in mongodb.db.tickets.find({'department': name}, {'_id': 1})]

                # 2) Collections, die direkt das Feld 'department' tragen
                dept_collections = [
                    'tools', 'consumables', 'workers', 'lendings', 'consumable_usages',
                    'tickets', 'timesheets', 'homepage_notices',
                    'locations', 'categories', 'ticket_categories'
                ]
                for coll in dept_collections:
                    try:
                        res = mongodb.db[coll].delete_many({'department': name})
                        deleted_counts[coll] = getattr(res, 'deleted_count', 0)
                    except Exception as ce:
                        logger.warning(f"Konnte Collection '{coll}' nicht bereinigen: {ce}")
                        deleted_counts[coll] = 0

                # 3) Settings-Einträge der Abteilung entfernen (globale 'departments' bleibt unberührt, da ohne department-Feld)
                try:
                    res = mongodb.db.settings.delete_many({'department': name})
                    deleted_counts['settings'] = getattr(res, 'deleted_count', 0)
                except Exception as se:
                    logger.warning(f"Konnte Settings nicht bereinigen: {se}")
                    deleted_counts['settings'] = 0

                # 4) Ticket-Messages/-History/-Notes mit Bezug zu Tickets der Abteilung entfernen
                ref_collections = ['messages', 'ticket_history', 'ticket_messages', 'ticket_notes']
                for coll in ref_collections:
                    try:
                        res = mongodb.db[coll].delete_many({
                            '$or': [
                                {'department': name},
                                {'ticket_id': {'$in': ticket_ids}} if ticket_ids else {'_id': None}
                            ]
                        })
                        deleted_counts[coll] = getattr(res, 'deleted_count', 0)
                    except Exception as re:
                        logger.warning(f"Konnte referenzielle Collection '{coll}' nicht bereinigen: {re}")
                        deleted_counts[coll] = 0

                # 5) Nutzerberechtigungen bereinigen: Abteilung aus allowed_departments entfernen, default_department leeren
                try:
                    mongodb.db.users.update_many({}, {'$pull': {'allowed_departments': name}})
                    mongodb.db.users.update_many({'default_department': name}, {'$unset': {'default_department': ""}})
                except Exception as ue:
                    logger.warning(f"Konnte Nutzerberechtigungen nicht bereinigen: {ue}")
            except Exception as cascade_e:
                logger.error(f"Fehler beim kaskadierenden Löschen der Abteilung '{name}': {cascade_e}")
                return False, f"Fehler beim Löschen der Abteilung und zugehöriger Daten: {cascade_e}"

            # 6) Abteilung aus globaler Liste entfernen
            try:
                departments.remove(name)
                mongodb.update_one('settings', {'key': 'departments'}, {
                    '$set': {
                        'value': departments,
                        'updated_at': datetime.now()
                    }
                })
            except Exception as list_e:
                logger.warning(f"Abteilung aus Liste konnte nicht entfernt werden: {list_e}")

            summary = ", ".join([f"{k}: {v}" for k, v in deleted_counts.items()])
            logger.info(f"Abteilung '{name}' gelöscht. Gelöschte Dokumente – {summary}")
            return True, f"Abteilung '{name}' und alle zugehörigen Daten wurden gelöscht ({summary})."
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Abteilung '{name}': {str(e)}")
            return False, f"Fehler beim Löschen der Abteilung: {str(e)}"

    @staticmethod
    def rename_department(old_name: str, new_name: str) -> Tuple[bool, str]:
        """
        Bennent eine Abteilung um und migriert referenzierte Daten.

        Args:
            old_name: bisheriger Name
            new_name: neuer Name

        Returns:
            (success, message)
        """
        try:
            if not old_name or not old_name.strip() or not new_name or not new_name.strip():
                return False, "Alter und neuer Abteilungsname sind erforderlich"

            old_name = old_name.strip()
            new_name = new_name.strip()

            if old_name == new_name:
                return False, "Neuer Name ist identisch mit dem alten"

            departments = AdminSystemSettingsService.get_departments_from_settings()
            if old_name not in departments:
                return False, f"Abteilung '{old_name}' nicht gefunden"
            if new_name in departments:
                return False, f"Abteilung '{new_name}' existiert bereits"

            # 1) Globale Department-Liste aktualisieren
            try:
                departments = [new_name if d == old_name else d for d in departments]
                mongodb.update_one('settings', {'key': 'departments'}, {
                    '$set': {
                        'value': departments,
                        'updated_at': datetime.now()
                    }
                })
            except Exception as e:
                logger.error(f"Fehler beim Aktualisieren der Abteilungsliste: {e}")
                return False, f"Fehler beim Aktualisieren der Abteilungsliste: {e}"

            # 2) Collections mit direktem department-Feld migrieren
            direct_collections = [
                'tools', 'consumables', 'workers', 'lendings', 'consumable_usages',
                'tickets', 'timesheets', 'homepage_notices',
                'locations', 'categories', 'ticket_categories'
            ]
            changed_total = 0
            for coll in direct_collections:
                try:
                    res = mongodb.db[coll].update_many({'department': old_name}, {'$set': {'department': new_name}})
                    changed_total += getattr(res, 'modified_count', 0)
                except Exception as ce:
                    logger.warning(f"Konnte Collection '{coll}' nicht migrieren: {ce}")

            # 3) Feature-Settings migrieren
            try:
                res = mongodb.db.feature_settings.update_many({'department': old_name}, {'$set': {'department': new_name}})
                changed_total += getattr(res, 'modified_count', 0)
            except Exception as fe:
                logger.warning(f"Konnte feature_settings nicht migrieren: {fe}")

            # 3b) Settings-Einträge mit department migrieren (alle keys außer 'departments')
            try:
                res = mongodb.db.settings.update_many({'department': old_name}, {'$set': {'department': new_name}})
                changed_total += getattr(res, 'modified_count', 0)
            except Exception as se:
                logger.warning(f"Konnte settings nicht migrieren: {se}")

            # 4) Referenzen in Messages/History nach ticket_id und/oder department
            ref_collections = ['messages', 'ticket_history', 'ticket_messages', 'ticket_notes']
            # Ermittle betroffene Tickets (mit altem Namen!)
            ticket_ids = [t['_id'] for t in mongodb.db.tickets.find({'department': old_name}, {'_id': 1})]
            for coll in ref_collections:
                try:
                    # Setze department-Feld, falls vorhanden
                    mongodb.db[coll].update_many({'department': old_name}, {'$set': {'department': new_name}})
                    if ticket_ids:
                        mongodb.db[coll].update_many({'ticket_id': {'$in': ticket_ids}}, {'$set': {'department': new_name}})
                except Exception as re:
                    logger.warning(f"Konnte referenzielle Collection '{coll}' nicht migrieren: {re}")

            # 5) Nutzer-Defaults und -Berechtigungen
            try:
                mongodb.db.users.update_many({'default_department': old_name}, {'$set': {'default_department': new_name}})
                mongodb.db.users.update_many({'allowed_departments': old_name}, {'$addToSet': {'allowed_departments': new_name}})
                mongodb.db.users.update_many({}, {'$pull': {'allowed_departments': old_name}})
            except Exception as ue:
                logger.warning(f"Konnte Nutzerberechtigungen nicht migrieren: {ue}")

            logger.info(f"Abteilung '{old_name}' in '{new_name}' umbenannt. Betroffene Dokumente ~{changed_total}.")
            return True, f"Abteilung umbenannt von '{old_name}' in '{new_name}'."
        except Exception as e:
            logger.error(f"Fehler beim Umbenennen der Abteilung '{old_name}' in '{new_name}': {str(e)}")
            return False, f"Fehler beim Umbenennen der Abteilung: {str(e)}"

    @staticmethod
    def add_category(name: str) -> Tuple[bool, str]:
        """
        Fügt eine neue Kategorie hinzu
        
        Args:
            name: Name der Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Kategoriename darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Kategorie bereits existiert
            categories = AdminSystemSettingsService.get_categories_from_settings()
            if name in categories:
                return False, f"Kategorie '{name}' existiert bereits"
            
            # Füge Kategorie hinzu
            categories.append(name)
            categories.sort()  # Sortiere alphabetisch
            
            # Update oder Insert Einstellung
            mongodb.update_one('settings', {'key': 'categories'}, {
                '$set': {
                    'value': categories,
                    'updated_at': datetime.now()
                }
            }, upsert=True)
            
            logger.info(f"Kategorie '{name}' erfolgreich hinzugefügt")
            return True, f"Kategorie '{name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Kategorie '{name}': {str(e)}")
            return False, f"Fehler beim Hinzufügen der Kategorie: {str(e)}"

    @staticmethod
    def delete_category(name: str) -> Tuple[bool, str]:
        """
        Löscht eine Kategorie
        
        Args:
            name: Name der Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Kategoriename darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Kategorie existiert
            categories = AdminSystemSettingsService.get_categories_from_settings()
            if name not in categories:
                return False, f"Kategorie '{name}' nicht gefunden"
            
            # Prüfe ob Kategorie noch verwendet wird
            tools_count = mongodb.count_documents('tools', {
                'category': name,
                'deleted': {'$ne': True}
            })
            
            if tools_count > 0:
                return False, f"Kategorie '{name}' wird noch von {tools_count} Werkzeugen verwendet"
            
            # Entferne Kategorie
            categories.remove(name)
            
            # Update Einstellung
            mongodb.update_one('settings', {'key': 'categories'}, {
                '$set': {
                    'value': categories,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Kategorie '{name}' erfolgreich gelöscht")
            return True, f"Kategorie '{name}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Kategorie '{name}': {str(e)}")
            return False, f"Fehler beim Löschen der Kategorie: {str(e)}"

    @staticmethod
    def add_location(name: str) -> Tuple[bool, str]:
        """
        Fügt einen neuen Standort hinzu
        
        Args:
            name: Name des Standorts
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Standortname darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Standort bereits existiert
            locations = AdminSystemSettingsService.get_locations_from_settings()
            if name in locations:
                return False, f"Standort '{name}' existiert bereits"
            
            # Füge Standort hinzu
            locations.append(name)
            locations.sort()  # Sortiere alphabetisch
            
            # Update oder Insert Einstellung
            mongodb.update_one('settings', {'key': 'locations'}, {
                '$set': {
                    'value': locations,
                    'updated_at': datetime.now()
                }
            }, upsert=True)
            
            logger.info(f"Standort '{name}' erfolgreich hinzugefügt")
            return True, f"Standort '{name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen des Standorts '{name}': {str(e)}")
            return False, f"Fehler beim Hinzufügen des Standorts: {str(e)}"

    @staticmethod
    def delete_location(name: str) -> Tuple[bool, str]:
        """
        Löscht einen Standort
        
        Args:
            name: Name des Standorts
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Standortname darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Standort existiert
            locations = AdminSystemSettingsService.get_locations_from_settings()
            if name not in locations:
                return False, f"Standort '{name}' nicht gefunden"
            
            # Prüfe ob Standort noch verwendet wird
            tools_count = mongodb.count_documents('tools', {
                'location': name,
                'deleted': {'$ne': True}
            })
            
            if tools_count > 0:
                return False, f"Standort '{name}' wird noch von {tools_count} Werkzeugen verwendet"
            
            # Entferne Standort
            locations.remove(name)
            
            # Update Einstellung
            mongodb.update_one('settings', {'key': 'locations'}, {
                '$set': {
                    'value': locations,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Standort '{name}' erfolgreich gelöscht")
            return True, f"Standort '{name}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Standorts '{name}': {str(e)}")
            return False, f"Fehler beim Löschen des Standorts: {str(e)}"

    @staticmethod
    def add_ticket_category(name: str) -> Tuple[bool, str]:
        """
        Fügt eine neue Ticket-Kategorie hinzu
        
        Args:
            name: Name der Ticket-Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Ticket-Kategoriename darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Ticket-Kategorie bereits existiert
            ticket_categories = AdminSystemSettingsService.get_ticket_categories_from_settings()
            if name in ticket_categories:
                return False, f"Ticket-Kategorie '{name}' existiert bereits"
            
            # Füge Ticket-Kategorie hinzu
            ticket_categories.append(name)
            ticket_categories.sort()  # Sortiere alphabetisch
            
            # Update oder Insert Einstellung
            mongodb.update_one('settings', {'key': 'ticket_categories'}, {
                '$set': {
                    'value': ticket_categories,
                    'updated_at': datetime.now()
                }
            }, upsert=True)
            
            logger.info(f"Ticket-Kategorie '{name}' erfolgreich hinzugefügt")
            return True, f"Ticket-Kategorie '{name}' erfolgreich hinzugefügt"
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie '{name}': {str(e)}")
            return False, f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}"

    @staticmethod
    def delete_ticket_category(name: str) -> Tuple[bool, str]:
        """
        Löscht eine Ticket-Kategorie
        
        Args:
            name: Name der Ticket-Kategorie
            
        Returns:
            (success, message)
        """
        try:
            if not name or not name.strip():
                return False, "Ticket-Kategoriename darf nicht leer sein"
            
            name = name.strip()
            
            # Prüfe ob Ticket-Kategorie existiert
            ticket_categories = AdminSystemSettingsService.get_ticket_categories_from_settings()
            if name not in ticket_categories:
                return False, f"Ticket-Kategorie '{name}' nicht gefunden"
            
            # Prüfe ob Ticket-Kategorie noch verwendet wird
            tickets_count = mongodb.count_documents('tickets', {
                'category': name
            })
            
            if tickets_count > 0:
                return False, f"Ticket-Kategorie '{name}' wird noch von {tickets_count} Tickets verwendet"
            
            # Entferne Ticket-Kategorie
            ticket_categories.remove(name)
            
            # Update Einstellung
            mongodb.update_one('settings', {'key': 'ticket_categories'}, {
                '$set': {
                    'value': ticket_categories,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Ticket-Kategorie '{name}' erfolgreich gelöscht")
            return True, f"Ticket-Kategorie '{name}' erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Ticket-Kategorie '{name}': {str(e)}")
            return False, f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}"

    @staticmethod
    def get_system_settings_statistics() -> Dict[str, Any]:
        """
        Gibt Statistiken über alle System-Einstellungen zurück
        
        Returns:
            Dictionary mit System-Einstellungs-Statistiken
        """
        try:
            stats = {
                'departments': {
                    'count': 0,
                    'used_by_workers': 0
                },
                'categories': {
                    'count': 0,
                    'used_by_tools': 0
                },
                'locations': {
                    'count': 0,
                    'used_by_tools': 0
                },
                'ticket_categories': {
                    'count': 0,
                    'used_by_tickets': 0
                }
            }
            
            # Abteilungen
            departments = AdminSystemSettingsService.get_departments_from_settings()
            stats['departments']['count'] = len(departments)
            for dept in departments:
                workers_count = mongodb.count_documents('workers', {
                    'department': dept,
                    'deleted': {'$ne': True}
                })
                stats['departments']['used_by_workers'] += workers_count
            
            # Kategorien
            categories = AdminSystemSettingsService.get_categories_from_settings()
            stats['categories']['count'] = len(categories)
            for cat in categories:
                tools_count = mongodb.count_documents('tools', {
                    'category': cat,
                    'deleted': {'$ne': True}
                })
                stats['categories']['used_by_tools'] += tools_count
            
            # Standorte
            locations = AdminSystemSettingsService.get_locations_from_settings()
            stats['locations']['count'] = len(locations)
            for loc in locations:
                tools_count = mongodb.count_documents('tools', {
                    'location': loc,
                    'deleted': {'$ne': True}
                })
                stats['locations']['used_by_tools'] += tools_count
            
            # Ticket-Kategorien
            ticket_categories = AdminSystemSettingsService.get_ticket_categories_from_settings()
            stats['ticket_categories']['count'] = len(ticket_categories)
            for cat in ticket_categories:
                tickets_count = mongodb.count_documents('tickets', {
                    'category': cat
                })
                stats['ticket_categories']['used_by_tickets'] += tickets_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der System-Einstellungs-Statistiken: {str(e)}")
            return {
                'departments': {'count': 0, 'used_by_workers': 0},
                'categories': {'count': 0, 'used_by_tools': 0},
                'locations': {'count': 0, 'used_by_tools': 0},
                'ticket_categories': {'count': 0, 'used_by_tickets': 0}
            }

    @staticmethod
    def validate_system_settings() -> Dict[str, Any]:
        """
        Validiert alle System-Einstellungen auf Konsistenz
        
        Returns:
            Dictionary mit Validierungsergebnissen
        """
        try:
            validation_results = {
                'departments': {'valid': True, 'issues': []},
                'categories': {'valid': True, 'issues': []},
                'locations': {'valid': True, 'issues': []},
                'ticket_categories': {'valid': True, 'issues': []},
                'overall_valid': True
            }
            
            # Validiere Abteilungen
            departments = AdminSystemSettingsService.get_departments_from_settings()
            for dept in departments:
                if not dept or not dept.strip():
                    validation_results['departments']['issues'].append(f"Leere Abteilung gefunden")
                    validation_results['departments']['valid'] = False
            
            # Validiere Kategorien
            categories = AdminSystemSettingsService.get_categories_from_settings()
            for cat in categories:
                if not cat or not cat.strip():
                    validation_results['categories']['issues'].append(f"Leere Kategorie gefunden")
                    validation_results['categories']['valid'] = False
            
            # Validiere Standorte
            locations = AdminSystemSettingsService.get_locations_from_settings()
            for loc in locations:
                if not loc or not loc.strip():
                    validation_results['locations']['issues'].append(f"Leerer Standort gefunden")
                    validation_results['locations']['valid'] = False
            
            # Validiere Ticket-Kategorien
            ticket_categories = AdminSystemSettingsService.get_ticket_categories_from_settings()
            for cat in ticket_categories:
                if not cat or not cat.strip():
                    validation_results['ticket_categories']['issues'].append(f"Leere Ticket-Kategorie gefunden")
                    validation_results['ticket_categories']['valid'] = False
            
            # Gesamtvalidierung
            if not all([
                validation_results['departments']['valid'],
                validation_results['categories']['valid'],
                validation_results['locations']['valid'],
                validation_results['ticket_categories']['valid']
            ]):
                validation_results['overall_valid'] = False
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Fehler bei der System-Einstellungs-Validierung: {str(e)}")
            return {
                'departments': {'valid': False, 'issues': [f"Validierungsfehler: {str(e)}"]},
                'categories': {'valid': False, 'issues': [f"Validierungsfehler: {str(e)}"]},
                'locations': {'valid': False, 'issues': [f"Validierungsfehler: {str(e)}"]},
                'ticket_categories': {'valid': False, 'issues': [f"Validierungsfehler: {str(e)}"]},
                'overall_valid': False
            } 