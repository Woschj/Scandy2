"""
ID-Helper-Funktionen für robuste Datenbankabfragen

Diese Module enthält Hilfsfunktionen für die Behandlung von MongoDB-IDs,
die sowohl String-IDs als auch ObjectIds unterstützen.
"""

from typing import Union
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

def convert_id_for_query(id_value: str) -> Union[str, ObjectId]:
    """
    Konvertiert eine ID für Datenbankabfragen.
    Versucht zuerst mit String-ID, dann mit ObjectId.
    
    Args:
        id_value: Die zu konvertierende ID
        
    Returns:
        Die konvertierte ID (String oder ObjectId)
    """
    try:
        # Wenn die ID ein String ist und 24 Zeichen lang (wie eine ObjectId)
        if isinstance(id_value, str) and len(id_value) == 24:
            try:
                return ObjectId(id_value)
            except Exception as e:
                logger.warning(f"Fehler bei ObjectId-Konvertierung: {e}")
                # Falls die Konvertierung fehlschlägt, gib die ursprüngliche ID zurück
                return id_value
        else:
            # Für andere IDs (z.B. Barcodes) gib die ursprüngliche ID zurück
            return id_value
    except Exception as e:
        logger.warning(f"Fehler bei ID-Behandlung: {e}")
        # Falls etwas schiefgeht, gib die ursprüngliche ID zurück
        return id_value

def normalize_id_for_database(id_value):
    """
    Normalisiert eine ID für die Datenbank - konvertiert alles zu String
    
    Args:
        id_value: Die zu normalisierende ID
        
    Returns:
        Die normalisierte ID als String
    """
    if isinstance(id_value, ObjectId):
        return str(id_value)
    elif isinstance(id_value, str):
        return id_value
    else:
        return str(id_value)

def find_document_by_id(collection: str, id_value: str, mongodb_instance=None):
    """
    Findet ein Dokument in einer Collection mit robuster ID-Behandlung.
    Unterstützt String-IDs und ObjectIds.
    
    Args:
        collection: Name der MongoDB-Collection
        id_value: Die zu suchende ID
        mongodb_instance: MongoDB-Instanz (optional)
        
    Returns:
        Das gefundene Dokument oder None
    """
    try:
        # MongoDB-Instanz holen falls nicht übergeben
        if mongodb_instance is None:
            from app.models.mongodb_database import mongodb
            mongodb_instance = mongodb
        
        logger.debug(f"Suche Dokument in Collection '{collection}' mit ID: {id_value}")
        
        # Versuche zuerst mit String-ID
        doc = mongodb_instance.find_one(collection, {'_id': id_value})
        if doc:
            logger.debug(f"Dokument mit String-ID gefunden: {doc.get('title', doc.get('name', 'Unknown'))}")
            return doc
        
        # Falls nicht gefunden, versuche mit ObjectId
        try:
            obj_id = ObjectId(id_value)
            doc = mongodb_instance.find_one(collection, {'_id': obj_id})
            if doc:
                logger.debug(f"Dokument mit ObjectId gefunden: {doc.get('title', doc.get('name', 'Unknown'))}")
                return doc
        except Exception as e:
            logger.debug(f"ObjectId-Konvertierung fehlgeschlagen: {e}")
        
        # Falls immer noch nicht gefunden, versuche mit convert_id_for_query
        converted_id = convert_id_for_query(id_value)
        doc = mongodb_instance.find_one(collection, {'_id': converted_id})
        if doc:
            logger.debug(f"Dokument mit convert_id_for_query gefunden: {doc.get('title', doc.get('name', 'Unknown'))}")
        else:
            logger.debug(f"Kein Dokument gefunden für ID: {id_value}")
        
        return doc
        
    except Exception as e:
        logger.error(f"Fehler beim Suchen von Dokument {id_value} in Collection {collection}: {str(e)}")
        return None

def find_user_by_id(user_id: str, mongodb_instance=None):
    """
    Spezielle Funktion zum Finden von Nutzenden mit robuster ID-Behandlung.
    Unterstützt String-IDs und ObjectIds.
    
    Args:
        user_id: Die zu suchende Nutzende-ID
        mongodb_instance: MongoDB-Instanz (optional)
        
    Returns:
        Der gefundene Nutzende oder None
    """
    try:
        logger.debug(f"Suche User mit ID: {user_id}")
        
        # Verwende convert_id_for_query für robuste ID-Konvertierung
        converted_id = convert_id_for_query(user_id)
        
        # MongoDB-Instanz holen falls nicht übergeben
        if mongodb_instance is None:
            from app.models.mongodb_database import mongodb
            mongodb_instance = mongodb
        
        user = mongodb_instance.find_one('users', {'_id': converted_id})
        
        if user:
            logger.debug(f"User gefunden: {user.get('username', 'Unknown')}")
            return user
        
        logger.debug(f"Kein User gefunden für ID: {user_id}")
        return None
                
    except Exception as e:
        logger.error(f"Fehler beim Laden des Users mit ID {user_id}: {e}")
        return None

def normalize_all_ids_in_collection(collection_name: str, mongodb_instance=None):
    """
    Normalisiert alle IDs in einer Collection zu Strings
    
    Args:
        collection_name: Name der Collection
        mongodb_instance: MongoDB-Instanz (optional)
        
    Returns:
        Anzahl der normalisierten Dokumente
    """
    try:
        # MongoDB-Instanz holen falls nicht übergeben
        if mongodb_instance is None:
            from app.models.mongodb_database import mongodb
            mongodb_instance = mongodb
        
        all_documents = mongodb_instance.find(collection_name, {})
        updated_count = 0
        
        for doc in all_documents:
            doc_id = doc.get('_id')
            
            # Falls die ID ein ObjectId ist, konvertiere sie zu String
            if isinstance(doc_id, ObjectId):
                string_id = str(doc_id)
                
                # Erstelle ein neues Dokument mit String-ID
                new_doc = doc.copy()
                new_doc['_id'] = string_id
                
                # Lösche das alte Dokument und füge das neue ein
                mongodb_instance.delete_one(collection_name, {'_id': doc_id})
                mongodb_instance.insert_one(collection_name, new_doc)
                
                updated_count += 1
                logger.info(f"ID normalisiert in {collection_name}: {doc.get('title', doc.get('name', 'Unknown'))} von {doc_id} zu {string_id}")
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Fehler beim Normalisieren der IDs in Collection {collection_name}: {str(e)}")
        return 0 