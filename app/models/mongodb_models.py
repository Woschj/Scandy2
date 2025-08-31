"""
MongoDB-Modelle für Scandy - Zentrales Modul

Dieses Modul dient als zentraler Einstiegspunkt für alle MongoDB-Modelle.
Alle spezifischen Modelle wurden in separate Dateien ausgelagert für bessere
Wartbarkeit und Übersichtlichkeit.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import der zentralen ID-Helper-Funktionen
from app.utils.id_helpers import convert_id_for_query, find_document_by_id, normalize_id_for_database

# Import aller separaten Modelle
try:
    from .mongodb_tool_model import MongoDBTool
    from .mongodb_worker_model import MongoDBWorker
except ImportError as e:
    logger.warning(f"Einige Modelle konnten nicht importiert werden: {e}")
    # Fallback-Definitionen für kritische Fälle
    MongoDBTool = None
    MongoDBWorker = None

# Temporäre Fallback-Modelle für noch nicht implementierte Modelle
class MongoDBConsumable:
    COLLECTION_NAME = 'consumables'

class MongoDBLending:
    COLLECTION_NAME = 'lendings'

class MongoDBConsumableUsage:
    COLLECTION_NAME = 'consumable_usages'

class MongoDBUser:
    """Temporäre MongoDBUser-Klasse mit den benötigten Methoden"""
    COLLECTION_NAME = 'users'

    @classmethod
    def get_all(cls):
        """Holt alle Nutzende"""
        from app.models.mongodb_database import mongodb
        return list(mongodb.find(cls.COLLECTION_NAME, {}))

    @classmethod
    def get_by_id(cls, user_id):
        """Holt einen Nutzende anhand der ID"""
        from app.models.mongodb_database import mongodb
        from app.utils.id_helpers import convert_id_for_query
        converted_id = convert_id_for_query(user_id)
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': converted_id})

    @classmethod
    def get_by_username(cls, username):
        """Holt einen Nutzende anhand des Nutzendename"""
        from app.models.mongodb_database import mongodb
        return mongodb.find_one(cls.COLLECTION_NAME, {'username': username})

class MongoDBTicket:
    COLLECTION_NAME = 'tickets'

class BaseModel:
    """Basis-Klasse für alle MongoDB-Modelle"""
    
    def __init__(self, **kwargs):
        """Initialisiert das Modell mit den übergebenen Daten"""
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert das Objekt in ein Dictionary"""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                data[key] = value
        return data
    
    @classmethod
    def get_collection_name(cls) -> str:
        """Gibt den Namen der MongoDB-Collection zurück"""
        return getattr(cls, 'COLLECTION_NAME', cls.__name__.lower() + 's')

# Kompatibilitätsfunktionen für bestehende Imports
def get_tool_model():
    """Gibt das Tool-Modell zurück"""
    return MongoDBTool

def get_worker_model():
    """Gibt das Worker-Modell zurück"""
    return MongoDBWorker

def get_consumable_model():
    """Gibt das Consumable-Modell zurück"""
    return MongoDBConsumable

def get_lending_model():
    """Gibt das Lending-Modell zurück"""
    return MongoDBLending

def get_user_model():
    """Gibt das User-Modell zurück"""
    return MongoDBUser

def get_ticket_model():
    """Gibt das Ticket-Modell zurück"""
    return MongoDBTicket

# Kompatibilitätsfunktionen für bestehende Imports
def create_mongodb_indexes():
    """
    Erstellt alle notwendigen MongoDB-Indizes.
    Diese Funktion wird beim Start der Anwendung aufgerufen.
    """
    try:
        from app.utils.performance_optimizer import IndexOptimizer
        IndexOptimizer.ensure_indexes()
        logger.info("MongoDB-Indizes erfolgreich erstellt")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der MongoDB-Indizes: {e}")
        raise
