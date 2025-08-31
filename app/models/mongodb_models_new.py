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
    from .mongodb_consumable_model import MongoDBConsumable
    from .mongodb_lending_model import MongoDBLending
    from .mongodb_consumable_usage_model import MongoDBConsumableUsage
    from .mongodb_user_model import MongoDBUser
    from .mongodb_ticket_model import MongoDBTicket
except ImportError as e:
    logger.warning(f"Einige Modelle konnten nicht importiert werden: {e}")
    # Fallback-Definitionen für kritische Fälle
    MongoDBTool = None
    MongoDBWorker = None
    MongoDBConsumable = None
    MongoDBLending = None
    MongoDBConsumableUsage = None
    MongoDBUser = None
    MongoDBTicket = None

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
