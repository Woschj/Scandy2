"""
Hilfsfunktionen für Datenverarbeitung und -formatierung
"""
import logging

logger = logging.getLogger(__name__)

def resolve_user_group_names(group_ids):
    """
    Löst Nutzergruppen-IDs zu Namen auf
    
    Args:
        group_ids: Liste von Group-IDs (ObjectIds oder Strings)
        
    Returns:
        str: Kommagetrennte Namen der Nutzergruppen
    """
    try:
        if not group_ids:
            return ''
        
        group_names = []
        for group_id in group_ids:
            try:
                from bson import ObjectId
                from app.models.mongodb_database import mongodb
                
                # Versuche ObjectId Konvertierung
                query_id = group_id
                if isinstance(group_id, str) and len(group_id) == 24:
                    try:
                        query_id = ObjectId(group_id)
                    except Exception as e:
                        logger.warning(f"Fehler bei ObjectId-Konvertierung für group_id {group_id}: [Interner Fehler]")
                        query_id = group_id
                
                # Lade Nutzergruppe aus Datenbank
                group = mongodb.find_one('user_groups', {'_id': query_id})
                if group:
                    group_names.append(group.get('name', str(group_id)))
                else:
                    group_names.append(str(group_id))
            except Exception as e:
                logger.warning(f"Fehler bei Gruppenverarbeitung für group_id {group_id}: [Interner Fehler]")
                group_names.append(str(group_id))
        
        return ', '.join(group_names)
    except Exception as e:
        logger.error(f"Fehler bei Gruppenverarbeitung: [Interner Fehler]")
        return ', '.join([str(gid) for gid in group_ids]) if group_ids else ''

def format_software_list(software_list):
    """
    Formatiert Software-Liste für Anzeige
    
    Args:
        software_list: Liste von Software-Namen
        
    Returns:
        str: Kommagetrennte Software-Namen
    """
    try:
        if not software_list:
            return ''
        return ', '.join(software_list)
    except Exception as e:
        logger.warning(f"Fehler bei Software-Listen-Formatierung: [Interner Fehler]")
        return ''

def format_boolean_field(value, true_text="Ja", false_text="Nein"):
    """
    Formatiert Boolean-Werte für Anzeige
    
    Args:
        value: Boolean-Wert
        true_text: Text für True
        false_text: Text für False
        
    Returns:
        str: Formatierter Text
    """
    try:
        if isinstance(value, bool):
            return true_text if value else false_text
        return str(value) if value is not None else ''
    except Exception as e:
        logger.warning(f"Fehler bei Boolean-Feld-Formatierung: [Interner Fehler]")
        return ''