"""
Datenbank-Hilfsfunktionen für Scandy

Dieses Modul enthält zentrale Hilfsfunktionen für Datenbankoperationen,
insbesondere für das Laden und Verwalten von Einstellungen und Referenzdaten.

Hauptfunktionen:
- Laden von Einstellungen aus der settings Collection
- Verwaltung von Kategorien, Standorten und Abteilungen
- Ticket-Nummern-Generierung
- Migration alter Datenstrukturen
"""

from app.models.mongodb_database import mongodb
from flask import g
import logging
from datetime import datetime
from bson import ObjectId
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

def _extract_by_department(value, department):
    """Hilfsfunktion: Extrahiert eine Liste für ein Department aus settings.value.
    Unterstützt sowohl List[str] (global) als auch Dict[str, List[str]] (per Department).
    """
    if isinstance(value, dict):
        if department and value.get(department):
            return value.get(department) or []
        # Fallbacks: 'GLOBAL' oder '*'
        for key in ('GLOBAL', '*', 'default'):
            if key in value and isinstance(value[key], list):
                return value[key]
        # Oder alle Werte zusammenführen
        merged = []
        for lst in value.values():
            if isinstance(lst, list):
                merged.extend(lst)
        return merged
    # List[str]
    return value if isinstance(value, list) else []


def get_setting_value(setting_key, fallback_collection=None, fallback_field='name'):
    """
    Generische Funktion zum Laden von Settings-Werten.
    
    Versucht zuerst die settings Collection, falls nicht vorhanden
    wird auf die ursprüngliche Collection zurückgegriffen.
    
    Args:
        setting_key: Schlüssel in der settings Collection
        fallback_collection: Fallback-Collection falls settings nicht existiert
        fallback_field: Feldname in der Fallback-Collection
        
    Returns:
        list: Liste der Werte oder leere Liste bei Fehler
        
    Example:
        >>> get_setting_value('categories', 'categories', 'name')
        ['Werkzeuge', 'Elektronik', 'Büro']
    """
    try:
        # Versuche zuerst die settings Collection
        settings_doc = mongodb.find_one('settings', {'key': setting_key})
        if settings_doc and 'value' in settings_doc:
            value = settings_doc['value']
            # String (Legacy)
            if isinstance(value, str):
                return [item.strip() for item in value.split(',') if item.strip()]
            # Department-sensitiv extrahieren
            current_dept = getattr(g, 'current_department', None)
            return _extract_by_department(value, current_dept)
        
        # Fallback: Verwende die ursprüngliche Collection
        if fallback_collection:
            items = mongodb.find(fallback_collection, {'deleted': {'$ne': True}})
            return [item[fallback_field] for item in items if fallback_field in item]
        
        return []
        
    except Exception as e:
        logger.error(f"Fehler beim Laden der Settings für '{setting_key}': {str(e)}")
        return []

def get_ticket_categories_from_settings():
    """
    Lädt Ticket-Kategorien aus der settings Collection.
    
    Returns:
        list: Liste der Ticket-Kategorien
    """
    return get_setting_value('ticket_categories')

def get_setting_map(setting_key) -> dict:
    """Liest settings.value roh und liefert immer ein Mapping {dept: [..]}.

    - Wenn value eine Liste ist, wird {'GLOBAL': value} zurückgegeben
    - Wenn value ein Mapping ist, wird es direkt zurückgegeben
    - Sonst ein leeres Mapping
    """
    try:
        settings_doc = mongodb.find_one('settings', {'key': setting_key})
        if not settings_doc:
            return {}
        value = settings_doc.get('value', [])
        if isinstance(value, list):
            return {'GLOBAL': value}
        if isinstance(value, dict):
            return value
        return {}
    except Exception:
        return {}

def get_ticket_categories_map() -> dict:
    return get_setting_map('ticket_categories')

def get_categories_from_settings():
    """
    Lädt Kategorien aus der settings Collection oder der categories Collection.
    
    Returns:
        list: Liste der Kategorien
    """
    return get_setting_value('categories', 'categories', 'name')

def get_locations_from_settings():
    """
    Lädt Standorte aus der settings Collection oder der locations Collection.
    
    Returns:
        list: Liste der Standorte
    """
    return get_setting_value('locations', 'locations', 'name')

def get_categories_scoped() -> list:
    """Liefert Kategorien strikt abteilungsweise aus der dedizierten Collection.
    Ignoriert settings vollständig (harte Trennung der Abteilungen).
    """
    try:
        current_dept = getattr(g, 'current_department', None)
        if not current_dept:
            return []
        items = mongodb.find('categories', {
            'deleted': {'$ne': True},
            'department': current_dept
        })
        raw_names = [item.get('name') for item in items]
        # Case-insensitive deduplizieren, Trim, stabile Reihenfolge beibehalten
        seen_lower = set()
        unique = []
        for n in raw_names:
            if not n:
                continue
            s = str(n).strip()
            if not s:
                continue
            key = s.lower()
            if key in seen_lower:
                continue
            seen_lower.add(key)
            unique.append(s)
        return sorted(unique, key=str.casefold)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Kategorien (scoped): {str(e)}")
        return []

def get_locations_scoped() -> list:
    """Liefert Standorte strikt abteilungsweise aus der dedizierten Collection.
    Ignoriert settings vollständig (harte Trennung der Abteilungen).
    """
    try:
        current_dept = getattr(g, 'current_department', None)
        if not current_dept:
            return []
        items = mongodb.find('locations', {
            'deleted': {'$ne': True},
            'department': current_dept
        })
        raw_names = [item.get('name') for item in items]
        # Case-insensitive deduplizieren, Trim, stabile Reihenfolge beibehalten
        seen_lower = set()
        unique = []
        for n in raw_names:
            if not n:
                continue
            s = str(n).strip()
            if not s:
                continue
            key = s.lower()
            if key in seen_lower:
                continue
            seen_lower.add(key)
            unique.append(s)
        return sorted(unique, key=str.casefold)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Standorte (scoped): {str(e)}")
        return []

def get_departments_from_settings():
    """
    Lädt Abteilungen aus der settings Collection oder der departments Collection.
    
    Returns:
        list: Liste der Abteilungen
    """
    return get_setting_value('departments', 'departments', 'name')

def ensure_default_settings():
    """
    Stellt sicher, dass die settings Collection existiert.

    Wichtig:
    - KEINE globalen Kategorien/Standorte mehr initialisieren (müssen pro Abteilung angelegt werden)
    - Nur Abteilungen- und Ticket-Kategorien-Keys vorbereiten

    Raises:
        Exception: Bei Fehlern während der Initialisierung
    """
    try:
        # Prüfe und erstelle leere Abteilungen-Collection
        if not mongodb.find_one('settings', {"key": "departments"}):
            mongodb.insert_one('settings', {
                "key": "departments",
                "value": []
            })
            logger.info("Abteilungen-Collection initialisiert")

        # Prüfe und erstelle leere Ticket-Kategorien-Collection
        if not mongodb.find_one('settings', {"key": "ticket_categories"}):
            mongodb.insert_one('settings', {
                "key": "ticket_categories",
                "value": []
            })
            logger.info("Ticket-Kategorien-Collection initialisiert")

    except Exception as e:
        logger.error(f"Fehler beim Initialisieren der Settings Collections: {str(e)}")
        raise

def validate_reference_data():
    """
    Validiert und gibt Referenzdaten zurück.
    
    Lädt alle wichtigen Referenzdaten und gibt sie in einem
    strukturierten Dictionary zurück.
    
    Returns:
        dict: Dictionary mit Kategorien, Standorten und Abteilungen
              Falls Fehler: Leere Listen für alle Felder
    """
    try:
        categories = get_categories_from_settings()
        locations = get_locations_from_settings()
        departments = get_departments_from_settings()
        
        return {
            'categories': categories,
            'locations': locations,
            'departments': departments
        }
    except Exception as e:
        logger.error(f"Fehler bei der Validierung der Referenzdaten: {str(e)}")
        return {
            'categories': [],
            'locations': [],
            'departments': []
        }

def migrate_old_data_to_settings():
    """
    Migriert alte Daten zu settings Collection.
    
    Prüft ob alte Collections (categories, locations, departments, ticket_categories)
    existieren und migriert deren Daten in die neue settings Collection.
    
    Raises:
        Exception: Bei Fehlern während der Migration
    """
    try:
        # Prüfe ob alte Collections existieren und migriere sie
        old_categories = mongodb.find('categories', {})
        old_locations = mongodb.find('locations', {})
        old_departments = mongodb.find('departments', {})
        old_ticket_categories = mongodb.find('ticket_categories', {})
        
        # Migriere Kategorien
        if old_categories:
            categories_data = []
            for cat in old_categories:
                if 'name' in cat:
                    categories_data.append(cat['name'])
            
            if categories_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'categories'},
                    {'$set': {'value': categories_data}},
                    upsert=True
                )
        
        # Migriere Standorte
        if old_locations:
            locations_data = []
            for loc in old_locations:
                if 'name' in loc:
                    locations_data.append(loc['name'])
            
            if locations_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'locations'},
                    {'$set': {'value': locations_data}},
                    upsert=True
                )
        
        # Migriere Abteilungen
        if old_departments:
            departments_data = []
            for dept in old_departments:
                if 'name' in dept:
                    departments_data.append(dept['name'])
            
            if departments_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'departments'},
                    {'$set': {'value': departments_data}},
                    upsert=True
                )
        
        # Migriere Ticket-Kategorien
        if old_ticket_categories:
            ticket_categories_data = []
            for cat in old_ticket_categories:
                if 'name' in cat:
                    ticket_categories_data.append(cat['name'])
            
            if ticket_categories_data:
                mongodb.update_one(
                    'settings',
                    {'key': 'ticket_categories'},
                    {'$set': {'value': ticket_categories_data}},
                    upsert=True
                )
                
        logger.info("Migration der alten Daten abgeschlossen")
        
    except Exception as e:
        logger.error(f"Fehler bei der Migration der alten Daten: {str(e)}")
        raise

def get_next_ticket_number():
    """
    Generiert die nächste Auftragsnummer im Format YYMM-XXX.
    
    Die Nummer setzt sich zusammen aus:
    - YY: Letzte 2 Ziffern des Jahres
    - MM: Monat mit führender Null
    - XXX: Fortlaufende Nummer für diesen Monat
    
    Returns:
        str: Nächste verfügbare Auftragsnummer
        
    Example:
        >>> get_next_ticket_number()
        '2506-001'
    """
    current_date = datetime.now()
    year_suffix = str(current_date.year)[-2:]  # Letzte 2 Ziffern des Jahres
    month = f"{current_date.month:02d}"  # Monat mit führender Null
    
    # Basis für die Nummer (z.B. "2506")
    base_number = f"{year_suffix}{month}"
    
    # Finde die höchste Nummer für diesen Monat
    existing_tickets = mongodb.find('tickets', {
        'ticket_number': {'$regex': f'^{base_number}-[0-9]+$'}
    })
    
    max_number = 0
    for ticket in existing_tickets:
        if ticket.get('ticket_number'):
            try:
                # Extrahiere die Nummer nach dem Bindestrich
                number_part = ticket['ticket_number'].split('-')[1]
                ticket_num = int(number_part)
                max_number = max(max_number, ticket_num)
            except (ValueError, IndexError):
                continue
    
    # Nächste Nummer
    next_number = max_number + 1
    
    return f"{base_number}-{next_number:03d}"

def normalize_id_for_database(id_value):
    """
    Normalisiert eine ID für die Datenbank - konvertiert alles zu String.
    Diese Funktion kann in allen Teilen der Anwendung verwendet werden.
    
    Args:
        id_value: ID-Wert (kann String, ObjectId oder andere Typen sein)
        
    Returns:
        str: Normalisierte String-ID
    """
    if isinstance(id_value, ObjectId):
        return str(id_value)
    elif isinstance(id_value, str):
        return id_value
    else:
        return str(id_value)

def ensure_consistent_ids():
    """
    Stellt sicher, dass alle IDs in der Datenbank konsistent sind.
    Kann manuell aufgerufen werden, um ID-Probleme zu beheben.
    """
    try:
        collections_to_normalize = [
            'tickets', 'users', 'tools', 'consumables', 'workers',
            'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit'
        ]
        
        total_updated = 0
        
        for collection_name in collections_to_normalize:
            try:
                documents = mongodb.find(collection_name, {})
                updated_count = 0
                
                for doc in documents:
                    doc_id = doc.get('_id')
                    
                    # Falls die ID ein ObjectId ist, konvertiere sie zu String
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)
                        
                        # Erstelle ein neues Dokument mit String-ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id
                        
                        # Lösche das alte Dokument und füge das neue ein
                        mongodb.delete_one(collection_name, {'_id': doc_id})
                        mongodb.insert_one(collection_name, new_doc)
                        
                        updated_count += 1
                
                if updated_count > 0:
                    print(f"Collection {collection_name}: {updated_count} IDs normalisiert")
                total_updated += updated_count
                
            except Exception as e:
                print(f"Fehler bei ID-Normalisierung in Collection {collection_name}: {str(e)}")
        
        if total_updated > 0:
            print(f"ID-Normalisierung abgeschlossen: {total_updated} IDs in allen Collections normalisiert")
        else:
            print("ID-Normalisierung: Alle IDs sind bereits normalisiert")
            
        return total_updated
            
    except Exception as e:
        print(f"Fehler bei ID-Normalisierung: {str(e)}")
        return 0 