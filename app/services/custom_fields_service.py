"""
Service für benutzerdefinierte Felder (Custom Fields)

Dieser Service ermöglicht das Erstellen und Verwalten dynamischer Felder für Werkzeuge und Verbrauchsgüter.
Die benutzerdefinierten Felder werden in der MongoDB 'custom_fields' Collection gespeichert und können
über Context Processors in allen Templates verfügbar gemacht werden.

Unterstützte Feldtypen:
- text: Einzeiliger Text
- textarea: Mehrzeiliger Text
- number: Numerische Werte
- date: Datumsfelder
- select: Auswahlliste mit vordefinierten Optionen
- checkbox: Ja/Nein Checkboxen
- email: E-Mail-Adressen mit Validierung
- url: URLs mit Validierung

Zieltypen:
- tools: Nur für Werkzeuge
- consumables: Nur für Verbrauchsgüter
- both: Für beide Typen verfügbar
"""
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime
from app.models.mongodb_database import mongodb
import logging

logger = logging.getLogger(__name__)

class CustomFieldsService:
    """Service für die Verwaltung benutzerdefinierter Felder"""
    
    FIELD_TYPES = {
        'text': 'Text (einzeilig)',
        'textarea': 'Text (mehrzeilig)', 
        'number': 'Zahl',
        'date': 'Datum',
        'select': 'Auswahlliste',
        'checkbox': 'Ja/Nein',
        'email': 'E-Mail',
        'url': 'URL'
    }
    
    TARGET_TYPES = {
        'tools': 'Werkzeuge',
        'consumables': 'Verbrauchsgüter',
        'both': 'Werkzeuge und Verbrauchsgüter'
    }
    
    @staticmethod
    def get_all_custom_fields() -> List[Dict[str, Any]]:
        """Holt alle benutzerdefinierten Felder"""
        try:
            fields = list(mongodb.find('custom_fields', {'deleted': {'$ne': True}}))
            # Sortiere nach Erstellungsdatum
            return sorted(fields, key=lambda x: x.get('created_at', datetime.min))
        except Exception as e:
            logger.error(f"Fehler beim Laden der benutzerdefinierten Felder: {str(e)}")
            return []
    
    @staticmethod
    def get_custom_fields_for_target(target_type: str) -> List[Dict[str, Any]]:
        """Holt benutzerdefinierte Felder für einen bestimmten Zieltyp (tools, consumables)"""
        try:
            # Felder die für den spezifischen Typ oder 'both' gelten
            query = {
                'deleted': {'$ne': True},
                'target_type': {'$in': [target_type, 'both']}
            }
            fields = list(mongodb.find('custom_fields', query))
            return sorted(fields, key=lambda x: x.get('sort_order', 999))
        except Exception as e:
            logger.error(f"Fehler beim Laden der Felder für {target_type}: {str(e)}")
            return []
    
    @staticmethod
    def create_custom_field(data: Dict[str, Any]) -> Tuple[bool, str]:
        """Erstellt ein neues benutzerdefiniertes Feld"""
        try:
            # Validierung
            if not data.get('name'):
                return False, 'Name ist erforderlich'
            
            if not data.get('field_type') or data['field_type'] not in CustomFieldsService.FIELD_TYPES:
                return False, 'Ungültiger Feldtyp'
            
            if not data.get('target_type') or data['target_type'] not in CustomFieldsService.TARGET_TYPES:
                return False, 'Ungültiger Zieltyp'
            
            # Prüfe auf doppelte Feldnamen pro Zieltyp
            existing = mongodb.find_one('custom_fields', {
                'name': data['name'],
                'target_type': {'$in': [data['target_type'], 'both']},
                'deleted': {'$ne': True}
            })
            if existing:
                return False, 'Ein Feld mit diesem Namen existiert bereits für diesen Bereich'
            
            # Generiere field_key aus dem Namen
            field_key = CustomFieldsService._generate_field_key(data['name'])
            
            # Prüfe ob field_key bereits existiert
            existing_key = mongodb.find_one('custom_fields', {
                'field_key': field_key,
                'deleted': {'$ne': True}
            })
            if existing_key:
                return False, 'Ein Feld mit diesem Schlüssel existiert bereits'
            
            field_data = {
                'name': data['name'].strip(),
                'field_key': field_key,
                'field_type': data['field_type'],
                'target_type': data['target_type'],
                'description': data.get('description', '').strip(),
                'required': data.get('required', False),
                'default_value': data.get('default_value', ''),
                'sort_order': data.get('sort_order', 999),
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'deleted': False
            }
            
            # Spezielle Behandlung für select-Felder
            if data['field_type'] == 'select':
                options = data.get('select_options', '').strip()
                if not options:
                    return False, 'Auswahloptionen sind für Auswahllisten erforderlich'
                # Optionen als Liste speichern (getrennt durch Zeilenwechsel)
                field_data['select_options'] = [opt.strip() for opt in options.split('\n') if opt.strip()]
            
            result = mongodb.insert_one('custom_fields', field_data)
            if result:
                return True, 'Benutzerdefiniertes Feld wurde erfolgreich erstellt'
            else:
                return False, 'Fehler beim Speichern des Feldes'
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des benutzerdefinierten Feldes: {str(e)}")
            return False, f'Fehler beim Erstellen des Feldes: {str(e)}'
    
    @staticmethod
    def update_custom_field(field_id: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Aktualisiert ein benutzerdefiniertes Feld"""
        try:
            # Feld finden
            field = mongodb.find_one('custom_fields', {'_id': field_id, 'deleted': {'$ne': True}})
            if not field:
                return False, 'Feld nicht gefunden'
            
            # Validierung
            if not data.get('name'):
                return False, 'Name ist erforderlich'
            
            # Prüfe auf doppelte Namen (außer dem aktuellen Feld)
            existing = mongodb.find_one('custom_fields', {
                'name': data['name'],
                'target_type': {'$in': [data['target_type'], 'both']},
                '_id': {'$ne': field_id},
                'deleted': {'$ne': True}
            })
            if existing:
                return False, 'Ein anderes Feld mit diesem Namen existiert bereits'
            
            update_data = {
                'name': data['name'].strip(),
                'field_type': data['field_type'],
                'target_type': data['target_type'],
                'description': data.get('description', '').strip(),
                'required': data.get('required', False),
                'default_value': data.get('default_value', ''),
                'sort_order': data.get('sort_order', 999),
                'updated_at': datetime.now()
            }
            
            # Spezielle Behandlung für select-Felder
            if data['field_type'] == 'select':
                options = data.get('select_options', '').strip()
                if not options:
                    return False, 'Auswahloptionen sind für Auswahllisten erforderlich'
                update_data['select_options'] = [opt.strip() for opt in options.split('\n') if opt.strip()]
            else:
                # Entferne select_options wenn Feldtyp geändert wurde
                update_data['$unset'] = {'select_options': 1}
            
            result = mongodb.update_one('custom_fields', {'_id': field_id}, {'$set': update_data})
            if result:
                return True, 'Feld wurde erfolgreich aktualisiert'
            else:
                return False, 'Fehler beim Aktualisieren des Feldes'
                
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des benutzerdefinierten Feldes: {str(e)}")
            return False, f'Fehler beim Aktualisieren: {str(e)}'
    
    @staticmethod
    def delete_custom_field(field_id: str) -> Tuple[bool, str]:
        """Löscht ein benutzerdefiniertes Feld (soft delete)"""
        try:
            field = mongodb.find_one('custom_fields', {'_id': field_id, 'deleted': {'$ne': True}})
            if not field:
                return False, 'Feld nicht gefunden'
            
            # Soft Delete
            result = mongodb.update_one('custom_fields', 
                                     {'_id': field_id}, 
                                     {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
            
            if result:
                return True, 'Feld wurde erfolgreich gelöscht'
            else:
                return False, 'Fehler beim Löschen des Feldes'
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen des benutzerdefinierten Feldes: {str(e)}")
            return False, f'Fehler beim Löschen: {str(e)}'
    
    @staticmethod
    def get_custom_field_by_id(field_id: str) -> Optional[Dict[str, Any]]:
        """Holt ein spezifisches benutzerdefiniertes Feld"""
        try:
            return mongodb.find_one('custom_fields', {'_id': field_id, 'deleted': {'$ne': True}})
        except Exception as e:
            logger.error(f"Fehler beim Laden des Feldes {field_id}: {str(e)}")
            return None
    
    @staticmethod
    def validate_custom_field_value(field: Dict[str, Any], value: Any) -> Tuple[bool, str, Any]:
        """Validiert einen Wert für ein benutzerdefiniertes Feld"""
        try:
            field_type = field.get('field_type')
            is_required = field.get('required', False)
            
            # Prüfe ob erforderliches Feld leer ist
            if is_required and (value is None or str(value).strip() == ''):
                return False, f"Das Feld '{field['name']}' ist erforderlich", None
            
            # Wenn Wert leer und nicht erforderlich, ist das OK
            if value is None or str(value).strip() == '':
                return True, '', None
            
            # Typ-spezifische Validierung
            if field_type == 'number':
                try:
                    converted_value = float(value)
                    return True, '', converted_value
                except (ValueError, TypeError):
                    return False, f"'{field['name']}' muss eine gültige Zahl sein", None
            
            elif field_type == 'email':
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, str(value)):
                    return False, f"'{field['name']}' muss eine gültige E-Mail-Adresse sein", None
            
            elif field_type == 'url':
                import re
                url_pattern = r'^https?://.+'
                if not re.match(url_pattern, str(value)):
                    return False, f"'{field['name']}' muss eine gültige URL sein (http:// oder https://)", None
            
            elif field_type == 'select':
                options = field.get('select_options', [])
                if str(value) not in options:
                    return False, f"'{value}' ist keine gültige Option für '{field['name']}'", None
            
            elif field_type == 'checkbox':
                # Konvertiere zu Boolean
                if isinstance(value, str):
                    converted_value = value.lower() in ['true', '1', 'on', 'yes', 'ja']
                else:
                    converted_value = bool(value)
                return True, '', converted_value
            
            # Für text, textarea, date geben wir den String-Wert zurück
            return True, '', str(value).strip()
            
        except Exception as e:
            logger.error(f"Fehler bei der Validierung von Feld {field.get('name', 'unbekannt')}: {str(e)}")
            return False, f"Validierungsfehler für '{field.get('name', 'unbekannt')}'", None
    
    @staticmethod
    def process_custom_fields_from_form(target_type: str, form_data: Dict) -> Tuple[bool, str, Dict[str, Any]]:
        """Verarbeitet benutzerdefinierte Felder aus einem Formular"""
        try:
            custom_fields = CustomFieldsService.get_custom_fields_for_target(target_type)
            processed_values = {}
            errors = []
            
            for field in custom_fields:
                field_key = field['field_key']
                form_value = form_data.get(f'custom_{field_key}')
                
                # Spezielle Behandlung für Checkboxen
                if field['field_type'] == 'checkbox':
                    # Checkbox ist aktiviert, wenn sie im Formular vorhanden ist
                    processed_values[field_key] = form_value is not None
                    continue
                
                # Validiere den Wert für andere Feldtypen
                is_valid, error_msg, processed_value = CustomFieldsService.validate_custom_field_value(field, form_value)
                
                if not is_valid:
                    errors.append(error_msg)
                    continue
                
                # Speichere nur nicht-leere Werte für andere Feldtypen
                if processed_value is not None and str(processed_value).strip() != '':
                    processed_values[field_key] = processed_value
            
            if errors:
                return False, '; '.join(errors), {}
            
            return True, '', processed_values
            
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der benutzerdefinierten Felder: {str(e)}")
            return False, f'Fehler beim Verarbeiten der Felder: {str(e)}', {}
    
    @staticmethod
    def _generate_field_key(name: str) -> str:
        """Generiert einen eindeutigen Schlüssel aus einem Feldnamen"""
        import re
        # Entferne Sonderzeichen und ersetze Leerzeichen
        key = re.sub(r'[^a-zA-Z0-9_\s]', '', name)
        key = re.sub(r'\s+', '_', key.strip())
        return key.lower()
    
    @staticmethod
    def get_custom_field_display_value(field: Dict[str, Any], value: Any) -> str:
        """Bereitet einen Wert für die Anzeige vor"""
        try:
            if value is None or str(value).strip() == '':
                return ''
            
            field_type = field.get('field_type')
            
            if field_type == 'checkbox':
                return 'Ja' if value else 'Nein'
            elif field_type == 'number':
                try:
                    # Formatiere Zahlen schön
                    if isinstance(value, (int, float)):
                        if value == int(value):
                            return str(int(value))
                        else:
                            return f"{value:.2f}".rstrip('0').rstrip('.')
                    return str(value)
                except:
                    return str(value)
            else:
                return str(value)
                
        except Exception as e:
            logger.error(f"Fehler beim Formatieren des Anzeigewerts: {str(e)}")
            return str(value) if value is not None else ''