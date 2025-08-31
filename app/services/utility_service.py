"""
Zentraler Utility Service für Scandy
Häufig verwendete Hilfsfunktionen an einem Ort
"""
from typing import Dict, Any, List, Union, Tuple
from datetime import datetime
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class UtilityService:
    """Zentraler Service für Utility-Funktionen"""
    
    # Import der zentralen ID-Helper-Funktionen
    from app.utils.id_helpers import convert_id_for_query
    
    @staticmethod
    def safe_date_key(item: Dict[str, Any], date_field: str = 'created_at') -> datetime:
        """
        Sichere Sortierung für Datumsfelder mit None-Behandlung
        
        Args:
            item: Dictionary mit Datumsfeld
            date_field: Name des Datumsfeldes
            
        Returns:
            datetime: Datum oder datetime.min für None-Werte
        """
        date_value = item.get(date_field)
        if isinstance(date_value, str):
            try:
                # Versuche verschiedene Datumsformate zu parsen
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except ValueError:
                        continue
            except Exception as e:
                logger.warning(f"Fehler bei Datumskonvertierung: {e}")
                pass
        elif isinstance(date_value, datetime):
            return date_value
        
        return datetime.min
    
    @staticmethod
    def ensure_datetime_fields(item: Dict[str, Any], fields: List[str] = None) -> Dict[str, Any]:
        """
        Stellt sicher, dass alle datetime-Felder korrekt sind
        
        Args:
            item: Dictionary mit zu prüfenden Feldern
            fields: Liste der zu prüfenden Felder
            
        Returns:
            Dict: Item mit korrigierten datetime-Feldern
        """
        if fields is None:
            fields = ['created_at', 'updated_at', 'due_date']
        
        for field in fields:
            if field in item and not isinstance(item[field], (datetime, type(None))):
                item[field] = None
        
        return item
    
    @staticmethod
    def convert_datetime_fields(item: Dict[str, Any], fields: List[str] = None) -> Dict[str, Any]:
        """
        Konvertiert String-Datumsfelder zu datetime-Objekten
        
        Args:
            item: Dictionary mit zu konvertierenden Feldern
            fields: Liste der zu konvertierenden Felder
            
        Returns:
            Dict: Item mit konvertierten datetime-Feldern
        """
        if fields is None:
            fields = ['created_at', 'updated_at', 'due_date']
        
        for field in fields:
            if item.get(field):
                if isinstance(item[field], str):
                    try:
                        # Versuche verschiedene Datumsformate zu parsen
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                item[field] = datetime.strptime(item[field], fmt)
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Fehler bei Datumskonvertierung für Feld {field}: {e}")
                        # Wenn alle Formate fehlschlagen, setze auf None
                        item[field] = None
                elif isinstance(item[field], datetime):
                    # Bereits ein datetime-Objekt, nichts zu tun
                    pass
                else:
                    # Versuche es als datetime zu konvertieren
                    try:
                        item[field] = datetime.fromisoformat(str(item[field]))
                    except Exception as e:
                        logger.warning(f"Fehler bei ISO-Datumskonvertierung für Feld {field}: {e}")
                        # Wenn Konvertierung fehlschlägt, setze auf None
                        item[field] = None
            else:
                # Feld ist None oder nicht vorhanden, setze auf None
                item[field] = None
        
        return item
    
    @staticmethod
    def format_worker_name(worker: Dict[str, Any]) -> str:
        """
        Formatiert einen Mitarbeitendenamen
        
        Args:
            worker: Worker-Dictionary
            
        Returns:
            str: Formatierter Name
        """
        if not worker:
            return "Unbekannt"
        
        firstname = worker.get('firstname', '').strip()
        lastname = worker.get('lastname', '').strip()
        
        if firstname and lastname:
            return f"{firstname} {lastname}"
        elif firstname:
            return firstname
        elif lastname:
            return lastname
        else:
            return "Unbekannt"
    
    @staticmethod
    def get_form_data_dict(request_form) -> Dict[str, Any]:
        """
        Konvertiert Flask request.form zu einem Dictionary
        
        Args:
            request_form: Flask request.form
            
        Returns:
            Dict: Formulardaten als Dictionary
        """
        return request_form.to_dict()
    
    @staticmethod
    def collect_list_data(request_form, field_names: List[str]) -> List[Dict[str, Any]]:
        """
        Sammelt Listen-Daten aus einem Formular (z.B. Materialliste, Arbeitsliste)
        
        Args:
            request_form: Flask request.form
            field_names: Liste der Feldnamen für jede Zeile
            
        Returns:
            List: Liste der gesammelten Daten
        """
        collected_data = []
        
        # Hole alle Werte für jedes Feld
        field_values = {}
        for field_name in field_names:
            field_values[field_name] = request_form.getlist(field_name)
        
        # Bestimme die maximale Länge
        max_length = max(len(values) for values in field_values.values()) if field_values else 0
        
        # Sammle die Daten zeilenweise
        for i in range(max_length):
            row_data = {}
            has_data = False
            
            for field_name in field_names:
                value = field_values[field_name][i] if i < len(field_values[field_name]) else ''
                row_data[field_name] = value.strip()
                if value.strip():
                    has_data = True
            
            # Nur Zeilen mit mindestens einem Wert hinzufügen
            if has_data:
                collected_data.append(row_data)
        
        return collected_data
    
    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, List[str]]:
        """
        Validiert Pflichtfelder
        
        Args:
            data: Zu validierende Daten
            required_fields: Liste der Pflichtfelder
            
        Returns:
            Tuple: (is_valid, error_messages)
        """
        errors = []
        
        for field in required_fields:
            value = data.get(field, '').strip() if isinstance(data.get(field), str) else data.get(field)
            if not value:
                errors.append(f'{field} ist erforderlich')
        
        return len(errors) == 0, errors
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = None) -> str:
        """
        Bereinigt einen String
        
        Args:
            value: Zu bereinigender String
            max_length: Maximale Länge (optional)
            
        Returns:
            str: Bereinigter String
        """
        if not value:
            return ''
        
        # Entferne Whitespace am Anfang und Ende
        cleaned = str(value).strip()
        
        # Begrenze Länge falls angegeben
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        return cleaned
    
    @staticmethod
    def safe_int_conversion(value: Any, default: int = 0) -> int:
        """
        Sichere Konvertierung zu Integer
        
        Args:
            value: Zu konvertierender Wert
            default: Standardwert bei Fehlern
            
        Returns:
            int: Konvertierter Wert oder Standardwert
        """
        try:
            if value is None or value == '':
                return default
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_float_conversion(value: Any, default: float = 0.0) -> float:
        """
        Sichere Konvertierung zu Float
        
        Args:
            value: Zu konvertierender Wert
            default: Standardwert bei Fehlern
            
        Returns:
            float: Konvertierter Wert oder Standardwert
        """
        try:
            if value is None or value == '':
                return default
            return float(value)
        except (ValueError, TypeError):
            return default 