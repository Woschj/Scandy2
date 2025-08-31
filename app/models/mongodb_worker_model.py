"""
MongoDB-Modell für Mitarbeitende
"""
from app.models.mongodb_database import mongodb
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import der zentralen ID-Helper-Funktionen
from app.utils.id_helpers import convert_id_for_query

class MongoDBWorker:
    """MongoDB-Modell für Mitarbeitende"""

    COLLECTION_NAME = 'workers'

    @classmethod
    def create(cls, worker_data: Dict[str, Any]) -> str:
        """Erstellt einen neuen Mitarbeitende"""
        return mongodb.insert_one(cls.COLLECTION_NAME, worker_data)

    @classmethod
    def get_by_id(cls, worker_id: str) -> Optional[Dict[str, Any]]:
        """Holt einen Mitarbeitende anhand der ID"""
        converted_id = convert_id_for_query(worker_id)
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': converted_id})

    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Holt einen Mitarbeitende anhand des Barcodes"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'barcode': barcode})

    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Mitarbeitende"""
        return mongodb.find(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})

    @classmethod
    def get_all_with_lendings(cls) -> List[Dict[str, Any]]:
        """Holt alle Mitarbeitende mit aktiven Ausleihen"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$lookup': {
                    'from': 'lendings',
                    'let': {'worker_barcode': '$barcode'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$worker_barcode', '$$worker_barcode']},
                                        {'$eq': ['$returned_at', None]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'active_lendings'
                }
            },
            {
                '$addFields': {
                    'active_lendings_count': {'$size': '$active_lendings'}
                }
            },
            {'$sort': {'lastname': 1, 'firstname': 1}}
        ]

        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)

    @classmethod
    def update(cls, worker_id: str, update_data: Dict[str, Any]) -> bool:
        """Aktualisiert einen Mitarbeitende"""
        converted_id = convert_id_for_query(worker_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, update_data)

    @classmethod
    def delete(cls, worker_id: str) -> bool:
        """Löscht einen Mitarbeitende (Soft Delete)"""
        converted_id = convert_id_for_query(worker_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, {'deleted': True})

    @classmethod
    def count_active(cls) -> int:
        """Zählt aktive Mitarbeitende"""
        return mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})

    @classmethod
    def search(cls, search_term: str) -> List[Dict[str, Any]]:
        """Sucht nach Mitarbeitenden"""
        filter_dict = {
            'deleted': {'$ne': True},
            '$or': [
                {'firstname': {'$regex': search_term, '$options': 'i'}},
                {'lastname': {'$regex': search_term, '$options': 'i'}},
                {'barcode': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        return mongodb.find(cls.COLLECTION_NAME, filter_dict)
