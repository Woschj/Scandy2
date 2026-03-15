from app.utils.id_helpers import convert_id_for_query
"""
MongoDB-Modelle für Scandy - Vollständige Implementierung
"""
from app.models.mongodb_database import mongodb
from app.config.config import config
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)



class BaseModel:
    """Basis-Klasse für MongoDB-Modelle"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def to_dict(self):
        """Konvertiert das Objekt in ein Dictionary"""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                data[key] = value
        return data

class MongoDBTool:
    """MongoDB-Modell für Werkzeuge"""
    
    COLLECTION_NAME = 'tools'
    
    @classmethod
    def create(cls, tool_data: Dict[str, Any]) -> str:
        """Erstellt ein neues Werkzeug"""
        return mongodb.insert_one(cls.COLLECTION_NAME, tool_data)
    
    @classmethod
    def get_by_id(cls, tool_id: str) -> Optional[Dict[str, Any]]:
        """Holt ein Werkzeug anhand der ID"""
        converted_id = convert_id_for_query(tool_id)
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': converted_id})
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Holt ein Werkzeug anhand des Barcodes"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'barcode': barcode})
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Werkzeuge"""
        return mongodb.find(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def get_all_with_status(cls) -> List[Dict[str, Any]]:
        """Holt alle Werkzeuge mit Ausleihstatus"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$lookup': {
                    'from': 'lendings',
                    'let': {'tool_barcode': '$barcode'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$tool_barcode', '$$tool_barcode']},
                                        {'$eq': ['$returned_at', None]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'active_lending'
                }
            },
            {
                '$lookup': {
                    'from': 'workers',
                    'let': {'worker_barcode': {'$arrayElemAt': ['$active_lending.worker_barcode', 0]}},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {'$eq': ['$barcode', '$$worker_barcode']}
                            }
                        }
                    ],
                    'as': 'current_borrower'
                }
            },
            {
                '$addFields': {
                    'current_borrower_name': {
                        '$concat': [
                            {'$arrayElemAt': ['$current_borrower.firstname', 0]},
                            ' ',
                            {'$arrayElemAt': ['$current_borrower.lastname', 0]}
                        ]
                    },
                    'is_lent': {'$gt': [{'$size': '$active_lending'}, 0]}
                }
            },
            {'$sort': {'name': 1}}
        ]
        
        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)
    
    @classmethod
    def update(cls, tool_id: str, update_data: Dict[str, Any]) -> bool:
        """Aktualisiert ein Werkzeug"""
        converted_id = convert_id_for_query(tool_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, update_data)
    
    @classmethod
    def delete(cls, tool_id: str) -> bool:
        """Löscht ein Werkzeug (Soft Delete)"""
        converted_id = convert_id_for_query(tool_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, {'deleted': True})
    
    @classmethod
    def count_active(cls) -> int:
        """Zählt aktive Werkzeuge"""
        return mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def search(cls, search_term: str) -> List[Dict[str, Any]]:
        """Sucht nach Werkzeugen"""
        filter_dict = {
            'deleted': {'$ne': True},
            '$or': [
                {'name': {'$regex': search_term, '$options': 'i'}},
                {'description': {'$regex': search_term, '$options': 'i'}},
                {'barcode': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        return mongodb.find(cls.COLLECTION_NAME, filter_dict)
    
    @classmethod
    def get_lending_history(cls, barcode: str) -> List[Dict[str, Any]]:
        """Holt die Ausleihhistorie für ein Werkzeug"""
        pipeline = [
            {'$match': {'tool_barcode': barcode}},
            {
                '$lookup': {
                    'from': 'workers',
                    'localField': 'worker_barcode',
                    'foreignField': 'barcode',
                    'as': 'worker'
                }
            },
            {
                '$addFields': {
                    'worker_name': {
                        '$concat': [
                            {'$arrayElemAt': ['$worker.firstname', 0]},
                            ' ',
                            {'$arrayElemAt': ['$worker.lastname', 0]}
                        ]
                    },
                    'action': {
                        '$cond': {
                            'if': {'$eq': ['$returned_at', None]},
                            'then': 'Ausgeliehen',
                            'else': 'Zurückgegeben'
                        }
                    },
                    'action_type': 'Ausleihe/Rückgabe',
                    'formatted_lent_at': {
                        '$dateToString': {
                            'format': '%d.%m.%Y %H:%M',
                            'date': '$lent_at'
                        }
                    },
                    'formatted_returned_at': {
                        '$dateToString': {
                            'format': '%d.%m.%Y %H:%M',
                            'date': '$returned_at'
                        }
                    }
                }
            },
            {'$sort': {'_id': -1}}
        ]
        
        return mongodb.aggregate('lendings', pipeline)

    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """Holt Statistiken für das Dashboard"""
        try:
            # Stelle sicher, dass die MongoDB-Verbindung verfügbar ist
            if mongodb.db is None:
                logger.error("MongoDB-Verbindung nicht verfügbar")
                raise Exception("MongoDB-Verbindung nicht verfügbar")
            
            # Debug: Teste die Verbindung
            try:
                mongodb._client.admin.command('ping')
                logger.info("MongoDB-Verbindung erfolgreich getestet")
            except Exception as e:
                logger.error(f"MongoDB-Ping fehlgeschlagen: [Interner Fehler]")
                raise Exception(f"MongoDB-Verbindung fehlgeschlagen: [Interner Fehler]")
            
            # Tool-Statistiken - verwende die tatsächlichen Status-Werte
            tool_stats = {
                'total': mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}}),
                'available': mongodb.count_documents(cls.COLLECTION_NAME, {
                    'deleted': {'$ne': True},
                    '$or': [
                        {'status': 'available'},
                        {'status': 'verfügbar'},
                        {'status': 'Available'},
                        {'status': {'$exists': False}}  # Fallback für Tools ohne Status
                    ]
                }),
                'lent': mongodb.count_documents(cls.COLLECTION_NAME, {
                    'deleted': {'$ne': True},
                    '$or': [
                        {'status': 'lent'},
                        {'status': 'ausgeliehen'},
                        {'status': 'Lent'},
                        {'status': 'Ausgeliehen'}
                    ]
                }),
                'defect': mongodb.count_documents(cls.COLLECTION_NAME, {
                    'deleted': {'$ne': True},
                    '$or': [
                        {'status': 'defect'},
                        {'status': 'defekt'},
                        {'status': 'Defect'},
                        {'status': 'Defekt'}
                    ]
                })
            }
            
            # Consumable-Statistiken
            consumable_stats = {
                'total': mongodb.count_documents('consumables', {'deleted': {'$ne': True}}),
                'sufficient': mongodb.count_documents('consumables', {
                    'deleted': {'$ne': True},
                    '$expr': {'$gt': ['$quantity', '$min_quantity']}
                }),
                'warning': mongodb.count_documents('consumables', {
                    'deleted': {'$ne': True},
                    '$expr': {'$lte': ['$quantity', '$min_quantity']}
                }),
                'critical': mongodb.count_documents('consumables', {
                    'deleted': {'$ne': True},
                    'quantity': 0
                })
            }
            
            # Worker-Statistiken
            worker_stats = {
                'total': mongodb.count_documents('workers', {'deleted': {'$ne': True}}),
                'by_department': []
            }
            
            # Worker nach Abteilung gruppieren
            pipeline = [
                {'$match': {'deleted': {'$ne': True}}},
                {
                    '$group': {
                        '_id': '$department',
                        'count': {'$sum': 1}
                    }
                },
                {'$sort': {'count': -1}}
            ]
            
            dept_stats = mongodb.aggregate('workers', pipeline)
            for dept in dept_stats:
                worker_stats['by_department'].append({
                    'name': dept['_id'] or 'Ohne Abteilung',
                    'count': dept['count']
                })
            
            # Aktuelle Ausleihen
            current_lendings = mongodb.count_documents('lendings', {'returned_at': {'$exists': False}})
            
            return {
                'tool_stats': tool_stats,
                'consumable_stats': consumable_stats,
                'worker_stats': worker_stats,
                'current_lendings': current_lendings
            }
        except Exception as e:
            # Fallback bei Fehlern
            logger.error(f"Fehler in get_statistics: [Interner Fehler]")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'tool_stats': {'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                'consumable_stats': {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                'worker_stats': {'total': 0, 'by_department': []},
                'current_lendings': 0
            }

    @classmethod
    def get_consumables_forecast(cls) -> List[Dict[str, Any]]:
        """Berechnet die Bestandsprognose für Verbrauchsmaterialien"""
        from datetime import timedelta
        
        pipeline = [
            {
                '$lookup': {
                    'from': 'consumable_usages',
                    'localField': 'barcode',
                    'foreignField': 'consumable_barcode',
                    'as': 'usages'
                }
            },
            {
                '$addFields': {
                    'recent_usages': {
                        '$filter': {
                            'input': '$usages',
                            'cond': {
                                '$gte': [
                                    '$$this.used_at',
                                    datetime.now() - timedelta(days=30)
                                ]
                            }
                        }
                    }
                }
            },
            {
                '$addFields': {
                    'avg_daily_usage': {
                        '$cond': {
                            'if': {'$gt': [{'$size': '$recent_usages'}, 0]},
                            'then': {
                                '$divide': [
                                    {'$sum': '$recent_usages.quantity'},
                                    30
                                ]
                            },
                            'else': 0
                        }
                    }
                }
            },
            {
                '$addFields': {
                    'days_remaining': {
                        '$cond': {
                            'if': {'$gt': ['$avg_daily_usage', 0]},
                            'then': {'$divide': ['$quantity', '$avg_daily_usage']},
                            'else': 999
                        }
                    }
                }
            },
            {
                '$match': {
                    'deleted': {'$ne': True},
                    'quantity': {'$gt': 0}
                }
            },
            {
                '$sort': {'days_remaining': 1}
            },
            {
                '$limit': 6
            },
            {
                '$project': {
                    'name': 1,
                    'current_amount': '$quantity',
                    'avg_daily_usage': {'$round': ['$avg_daily_usage', 2]},
                    'days_remaining': {'$round': ['$days_remaining']}
                }
            }
        ]
        
        return mongodb.aggregate('consumables', pipeline)

    @classmethod
    def get_duplicate_barcodes(cls) -> List[Dict[str, Any]]:
        """Prüft auf doppelte Barcodes in Tools und Consumables"""
        # App-Labels aus der Datenbank laden
        tools_label = mongodb.find_one('settings', {'key': 'label_tools_name'})
        consumables_label = mongodb.find_one('settings', {'key': 'label_consumables_name'})
        
        # Fallback-Werte falls keine Labels in der DB gefunden werden
        tools_type = tools_label.get('value', 'Werkzeuge') if tools_label else 'Werkzeuge'
        consumables_type = consumables_label.get('value', 'Verbrauchsmaterial') if consumables_label else 'Verbrauchsmaterial'
        
        # Alle Barcodes sammeln
        tool_barcodes = list(mongodb.find(cls.COLLECTION_NAME, {
            'deleted': {'$ne': True},
            'barcode': {'$exists': True, '$ne': None}
        }, projection={'barcode': 1, 'name': 1}))
        
        consumable_barcodes = list(mongodb.find('consumables', {
            'deleted': {'$ne': True},
            'barcode': {'$exists': True, '$ne': None}
        }, projection={'barcode': 1, 'name': 1}))
        
        # Barcode-Zählung
        barcode_count = {}
        barcode_entries = {}
        
        # Tools hinzufügen
        for tool in tool_barcodes:
            bc = tool.get('barcode')
            if bc:
                if bc not in barcode_count:
                    barcode_count[bc] = 0
                    barcode_entries[bc] = []
                barcode_count[bc] += 1
                barcode_entries[bc].append({
                    'type': tools_type,
                    'name': tool.get('name', 'Unbekannt'),
                    'id': str(tool.get('_id'))
                })
        
        # Consumables hinzufügen
        for consumable in consumable_barcodes:
            bc = consumable.get('barcode')
            if bc:
                if bc not in barcode_count:
                    barcode_count[bc] = 0
                    barcode_entries[bc] = []
                barcode_count[bc] += 1
                barcode_entries[bc].append({
                    'type': consumables_type,
                    'name': consumable.get('name', 'Unbekannt'),
                    'id': str(consumable.get('_id'))
                })
        
        # Duplikate finden
        duplicates = []
        for barcode, count in barcode_count.items():
            if count > 1:
                duplicates.append({
                    'barcode': barcode,
                    'count': count,
                    'entries': barcode_entries[barcode]
                })
        
        return duplicates

class MongoDBWorker:
    """MongoDB-Modell für Mitarbeiter"""
    
    COLLECTION_NAME = 'workers'
    
    @classmethod
    def create(cls, worker_data: Dict[str, Any]) -> str:
        """Erstellt einen neuen Mitarbeiter"""
        return mongodb.insert_one(cls.COLLECTION_NAME, worker_data)
    
    @classmethod
    def get_by_id(cls, worker_id: str) -> Optional[Dict[str, Any]]:
        """Holt einen Mitarbeiter anhand der ID"""
        converted_id = convert_id_for_query(worker_id)
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': converted_id})
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Holt einen Mitarbeiter anhand des Barcodes"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'barcode': barcode})
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Mitarbeiter"""
        return mongodb.find(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def get_all_with_lendings(cls) -> List[Dict[str, Any]]:
        """Holt alle Mitarbeiter mit aktiven Ausleihen"""
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
        """Aktualisiert einen Mitarbeiter"""
        converted_id = convert_id_for_query(worker_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, update_data)
    
    @classmethod
    def delete(cls, worker_id: str) -> bool:
        """Löscht einen Mitarbeiter (Soft Delete)"""
        converted_id = convert_id_for_query(worker_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, {'deleted': True})
    
    @classmethod
    def count_active(cls) -> int:
        """Zählt aktive Mitarbeiter"""
        return mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def search(cls, search_term: str) -> List[Dict[str, Any]]:
        """Sucht nach Mitarbeitern"""
        filter_dict = {
            'deleted': {'$ne': True},
            '$or': [
                {'firstname': {'$regex': search_term, '$options': 'i'}},
                {'lastname': {'$regex': search_term, '$options': 'i'}},
                {'barcode': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        return mongodb.find(cls.COLLECTION_NAME, filter_dict)

class MongoDBConsumable:
    """MongoDB-Modell für Verbrauchsmaterialien"""
    
    COLLECTION_NAME = 'consumables'
    
    @classmethod
    def create(cls, consumable_data: Dict[str, Any]) -> str:
        """Erstellt ein neues Verbrauchsmaterial"""
        return mongodb.insert_one(cls.COLLECTION_NAME, consumable_data)
    
    @classmethod
    def get_by_id(cls, consumable_id: str) -> Optional[Dict[str, Any]]:
        """Holt ein Verbrauchsmaterial anhand der ID"""
        converted_id = convert_id_for_query(consumable_id)
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': converted_id})
    
    @classmethod
    def get_by_barcode(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Holt ein Verbrauchsmaterial anhand des Barcodes"""
        return mongodb.find_one(cls.COLLECTION_NAME, {'barcode': barcode})
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Verbrauchsmaterialien"""
        return mongodb.find(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """Holt alle Verbrauchsmaterialien mit Bestandsstatus"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$addFields': {
                    'stock_status': {
                        '$cond': {
                            'if': {'$lte': ['$quantity', '$min_quantity']},
                            'then': 'Nachbestellen',
                            'else': 'OK'
                        }
                    }
                }
            },
            {'$sort': {'name': 1}}
        ]
        
        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)
    
    @classmethod
    def get_forecast(cls) -> List[Dict[str, Any]]:
        """Berechnet die Bestandsprognose für Verbrauchsmaterialien"""
        pipeline = [
            {'$match': {'deleted': {'$ne': True}, 'quantity': {'$gt': 0}}},
            {
                '$lookup': {
                    'from': 'consumable_usages',
                    'let': {'consumable_barcode': '$barcode'},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$consumable_barcode', '$$consumable_barcode']},
                                        {'$gte': ['$used_at', {'$dateSubtract': {'startDate': '$$NOW', 'unit': 'day', 'amount': 30}}]}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'recent_usage'
                }
            },
            {
                '$addFields': {
                    'avg_daily_usage': {
                        '$divide': [
                            {'$sum': '$recent_usage.quantity'},
                            30
                        ]
                    }
                }
            },
            {
                '$addFields': {
                    'days_remaining': {
                        '$cond': {
                            'if': {'$gt': ['$avg_daily_usage', 0]},
                            'then': {'$divide': ['$quantity', '$avg_daily_usage']},
                            'else': 999
                        }
                    }
                }
            },
            {'$sort': {'days_remaining': 1}},
            {'$limit': 10}
        ]
        
        return mongodb.aggregate(cls.COLLECTION_NAME, pipeline)
    
    @classmethod
    def update(cls, consumable_id: str, update_data: Dict[str, Any]) -> bool:
        """Aktualisiert ein Verbrauchsmaterial"""
        converted_id = convert_id_for_query(consumable_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, update_data)
    
    @classmethod
    def delete(cls, consumable_id: str) -> bool:
        """Löscht ein Verbrauchsmaterial (Soft Delete)"""
        converted_id = convert_id_for_query(consumable_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, {'deleted': True})
    
    @classmethod
    def count_active(cls) -> int:
        """Zählt aktive Verbrauchsmaterialien"""
        return mongodb.count_documents(cls.COLLECTION_NAME, {'deleted': {'$ne': True}})
    
    @classmethod
    def search(cls, search_term: str) -> List[Dict[str, Any]]:
        """Sucht nach Verbrauchsmaterialien"""
        filter_dict = {
            'deleted': {'$ne': True},
            '$or': [
                {'name': {'$regex': search_term, '$options': 'i'}},
                {'description': {'$regex': search_term, '$options': 'i'}},
                {'barcode': {'$regex': search_term, '$options': 'i'}}
            ]
        }
        return mongodb.find(cls.COLLECTION_NAME, filter_dict)

class MongoDBLending:
    """MongoDB-Modell für Ausleihen"""
    
    COLLECTION_NAME = 'lendings'
    
    @classmethod
    def create(cls, lending_data: Dict[str, Any]) -> str:
        """Erstellt eine neue Ausleihe"""
        return mongodb.insert_one(cls.COLLECTION_NAME, lending_data)
    
    @classmethod
    def get_by_id(cls, lending_id: str) -> Optional[Dict[str, Any]]:
        """Holt eine Ausleihe anhand der ID"""
        converted_id = convert_id_for_query(lending_id)
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': converted_id})
    
    @classmethod
    def get_active_by_tool(cls, tool_id: str) -> Optional[Dict[str, Any]]:
        """Holt die aktive Ausleihe für ein Werkzeug"""
        return mongodb.find_one(cls.COLLECTION_NAME, {
            'tool_id': tool_id,
            'returned_at': {'$exists': False}
        })
    
    @classmethod
    def get_active_by_worker(cls, worker_id: str) -> List[Dict[str, Any]]:
        """Holt alle aktiven Ausleihen eines Mitarbeiters"""
        return mongodb.find(cls.COLLECTION_NAME, {
            'worker_id': worker_id,
            'returned_at': {'$exists': False}
        })
    
    @classmethod
    def get_active_lendings(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Ausleihen"""
        return mongodb.find(cls.COLLECTION_NAME, {'returned_at': {'$exists': False}})
    
    @classmethod
    def get_lendings_by_worker(cls, worker_barcode: str) -> List[Dict[str, Any]]:
        """Holt alle Ausleihen eines Mitarbeiters"""
        return mongodb.find(cls.COLLECTION_NAME, {'worker_barcode': worker_barcode})
    
    @classmethod
    def get_lendings_by_tool(cls, tool_barcode: str) -> List[Dict[str, Any]]:
        """Holt alle Ausleihen eines Werkzeugs"""
        return mongodb.find(cls.COLLECTION_NAME, {'tool_barcode': tool_barcode})
    
    @classmethod
    def return_tool(cls, lending_id: str) -> bool:
        """Gibt ein Werkzeug zurück"""
        converted_id = convert_id_for_query(lending_id)
        return mongodb.update_one(cls.COLLECTION_NAME, {'_id': converted_id}, {
            'returned_at': datetime.now()
        })
    
    @classmethod
    def get_all_active(cls) -> List[Dict[str, Any]]:
        """Holt alle aktiven Ausleihen"""
        return mongodb.find(cls.COLLECTION_NAME, {'returned_at': {'$exists': False}})

class MongoDBConsumableUsage:
    """MongoDB-Modell für Verbrauchsmaterial-Verwendung"""
    
    COLLECTION_NAME = 'consumable_usages'
    
    @classmethod
    def create(cls, usage_data: Dict[str, Any]) -> str:
        """Erstellt einen neuen Verbrauchsmaterial-Verbrauch"""
        return mongodb.insert_one(cls.COLLECTION_NAME, usage_data)
    
    @classmethod
    def get_by_consumable(cls, consumable_id: str) -> List[Dict[str, Any]]:
        """Holt alle Verwendungen eines Verbrauchsmaterials"""
        return mongodb.find(cls.COLLECTION_NAME, {'consumable_id': consumable_id})
    
    @classmethod
    def get_by_worker(cls, worker_id: str) -> List[Dict[str, Any]]:
        """Holt alle Verwendungen eines Mitarbeiters"""
        return mongodb.find(cls.COLLECTION_NAME, {'worker_id': worker_id})
    
    @classmethod
    def get_usage_by_worker(cls, worker_barcode: str, days: int = 30) -> List[Dict[str, Any]]:
        """Holt den Verbrauch eines Mitarbeiters"""
        from datetime import timedelta
        
        start_date = datetime.now() - timedelta(days=days)
        
        return mongodb.find(
            cls.COLLECTION_NAME, 
            {
                'worker_barcode': worker_barcode,
                'used_at': {'$gte': start_date}
            }
        )

class MongoDBUser:
    """MongoDB-Modell für Benutzer"""
    
    COLLECTION_NAME = 'users'
    
    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """Holt einen Benutzer anhand der ID"""
        try:
            print(f"DEBUG: Suche User mit ID: {user_id}")
            
            # Versuche zuerst mit String-ID
            user_data = mongodb.find_one(cls.COLLECTION_NAME, {'_id': user_id})
            if user_data:
                print(f"DEBUG: User mit String-ID gefunden: {user_data.get('username', 'Unknown')}")
                return user_data
            
            # Versuche mit ObjectId
            try:
                from bson import ObjectId
                obj_id = ObjectId(user_id)
                user_data = mongodb.find_one(cls.COLLECTION_NAME, {'_id': obj_id})
                if user_data:
                    print(f"DEBUG: User mit ObjectId gefunden: {user_data.get('username', 'Unknown')}")
                    return user_data
            except Exception as e:
                print(f"DEBUG: ObjectId-Konvertierung fehlgeschlagen: [Interner Fehler]")
            
            # Versuche mit convert_id_for_query als Fallback
            try:
                converted_id = convert_id_for_query(user_id)
                user_data = mongodb.find_one(cls.COLLECTION_NAME, {'_id': converted_id})
                if user_data:
                    print(f"DEBUG: User mit convert_id_for_query gefunden: {user_data.get('username', 'Unknown')}")
                    return user_data
            except Exception as e:
                print(f"DEBUG: convert_id_for_query fehlgeschlagen: [Interner Fehler]")
            
            print(f"DEBUG: Kein User gefunden für ID: {user_id}")
            return None
                
        except Exception as e:
            print(f"DEBUG: Fehler beim Laden des Users mit ID {user_id}: [Interner Fehler]")
            return None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional[Dict[str, Any]]:
        """Holt einen Benutzer anhand des Benutzernamens (case-insensitive)"""
        # Verwende case-insensitive Suche mit MongoDB regex
        return mongodb.find_one(cls.COLLECTION_NAME, {'username': {'$regex': f'^{username}$', '$options': 'i'}})
    
    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """Holt alle Benutzer"""
        return mongodb.find(cls.COLLECTION_NAME, {})

class MongoDBTicket:
    """MongoDB-Modell für Tickets"""
    
    COLLECTION_NAME = 'tickets'
    
    @classmethod
    def get_by_status(cls, status: str) -> List[Dict[str, Any]]:
        """Holt Tickets nach Status"""
        return mongodb.find(cls.COLLECTION_NAME, {'status': status, 'deleted': {'$ne': True}})
    
    @classmethod
    def get_by_assignee(cls, assigned_to: str) -> List[Dict[str, Any]]:
        """Holt Tickets nach Zuweisung"""
        return mongodb.find(cls.COLLECTION_NAME, {'assigned_to': assigned_to, 'deleted': {'$ne': True}})

def create_mongodb_indexes():
    """Erstellt alle notwendigen MongoDB-Indizes und initialisiert die Datenbank"""
    try:
        # Prüfe ob Indizes bereits erstellt wurden (schneller Start)
        try:
            from app.models.mongodb_database import mongodb
            # Teste einen bekannten Index
            collection = mongodb.get_collection('tools')
            existing_indexes = list(collection.list_indexes())
            index_names = [idx.get('name', '') for idx in existing_indexes]

            # Wenn wichtige Indizes bereits existieren, überspringe die Erstellung
            if 'name_1' in index_names and 'barcode_1' in index_names:
                logger.info("MongoDB-Indizes sind bereits vorhanden, überspringe Erstellung")
                return
        except Exception:
            # Bei Fehlern fahre mit normaler Index-Erstellung fort
            pass
        # Legacy-Index-Bereinigung: entferne eindeutige Barcode-Indexe ohne Department
        def _drop_legacy_barcode_unique(collection_name: str):
            try:
                coll = mongodb.get_collection(collection_name)
                for idx in coll.list_indexes():
                    # Erkenne Single-Field-Index auf barcode
                    if idx.get('name') == 'barcode_1' and idx.get('unique'):
                        try:
                            coll.drop_index('barcode_1')
                        except Exception:
                            pass
            except Exception:
                pass

        for coll_name in [MongoDBTool.COLLECTION_NAME, MongoDBWorker.COLLECTION_NAME, MongoDBConsumable.COLLECTION_NAME]:
            _drop_legacy_barcode_unique(coll_name)

        # Werkzeuge-Indizes (Unique pro Abteilung statt global)
        # Entferne evtl. existierende globale Unique-Index-Konflikte NICHT aggressiv; create_index ist idempotent
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, [('department', 1), ('barcode', 1)], unique=True, sparse=True)
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'name')
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'category')
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'location')
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, 'status')
        # Compound-Index für Status + Kategorie (häufige Abfrage)
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, [('status', 1), ('category', 1)])
        # Compound-Index für Standort + Status
        mongodb.create_index(MongoDBTool.COLLECTION_NAME, [('location', 1), ('status', 1)])
        
        # Mitarbeiter-Indizes (Unique pro Abteilung)
        mongodb.create_index(MongoDBWorker.COLLECTION_NAME, [('department', 1), ('barcode', 1)], unique=True, sparse=True)
        mongodb.create_index(MongoDBWorker.COLLECTION_NAME, 'lastname')
        mongodb.create_index(MongoDBWorker.COLLECTION_NAME, 'department')
        # Compound-Index für Abteilung + Name
        mongodb.create_index(MongoDBWorker.COLLECTION_NAME, [('department', 1), ('lastname', 1)])
        # TTL für geplante Löschung von Workern (falls mit User gekoppelt)
        try:
            mongodb.create_index(MongoDBWorker.COLLECTION_NAME, 'delete_at', expireAfterSeconds=0)
        except Exception:
            pass
        
        # Verbrauchsmaterial-Indizes (Unique pro Abteilung)
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, [('department', 1), ('barcode', 1)], unique=True, sparse=True)
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, 'name')
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, 'category')
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, 'location')
        # Compound-Index für Kategorie + Status
        mongodb.create_index(MongoDBConsumable.COLLECTION_NAME, [('category', 1), ('quantity', 1)])
        
        # Ausleihen-Indizes
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, 'tool_barcode')
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, 'worker_barcode')
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, 'lent_at')
        # Compound-Index für aktive Ausleihen
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, [('status', 1), ('due_date', 1)])
        # Compound-Index für Worker + Status
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, [('worker_barcode', 1), ('status', 1)])
        # Compound-Index für Tool + Status
        mongodb.create_index(MongoDBLending.COLLECTION_NAME, [('tool_barcode', 1), ('status', 1)])
        
        # Verbrauchsmaterial-Verwendung-Indizes
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, 'consumable_barcode')
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, 'worker_barcode')
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, 'used_at')
        # Compound-Index für Verbrauchsmaterial + Datum
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, [('consumable_barcode', 1), ('used_at', -1)])
        # Compound-Index für Worker + Datum
        mongodb.create_index(MongoDBConsumableUsage.COLLECTION_NAME, [('worker_barcode', 1), ('used_at', -1)])
        
        # Benutzer-Indizes
        mongodb.create_index(MongoDBUser.COLLECTION_NAME, 'username', unique=True)
        mongodb.create_index(MongoDBUser.COLLECTION_NAME, 'email')
        # Compound-Index für Rolle + Aktivität
        mongodb.create_index(MongoDBUser.COLLECTION_NAME, [('role', 1), ('is_active', 1)])
        # TTL für geplante Löschung (löscht Dokumente automatisch nach Erreichen von delete_at)
        # Hinweis: delete_at muss als echtes Date-Feld gespeichert werden
        try:
            mongodb.create_index(MongoDBUser.COLLECTION_NAME, 'delete_at', expireAfterSeconds=0)
        except Exception:
            pass
        
        # Ticket-Indizes
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, 'status')
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, 'assigned_to')
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, 'created_at')
        # Compound-Index für Status + Kategorie (häufige Abfrage)
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, [('status', 1), ('category', 1)])
        # Compound-Index für Zuweisung + Status
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, [('assigned_to', 1), ('status', 1)])
        # Compound-Index für Ersteller + Datum
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, [('created_by', 1), ('created_at', -1)])
        # Compound-Index für Priorität + Status
        mongodb.create_index(MongoDBTicket.COLLECTION_NAME, [('priority', 1), ('status', 1)])
        
        # Settings-Indizes (Key pro Abteilung), aber der Schlüssel 'departments' bleibt global
        mongodb.create_index('settings', [('department', 1), ('key', 1)], unique=True, sparse=True)
        
        # Timesheets-Indizes
        mongodb.create_index('timesheets', 'user_id')
        mongodb.create_index('timesheets', 'year')
        mongodb.create_index('timesheets', 'kw')
        # Compound-Index für User + Jahr + KW
        mongodb.create_index('timesheets', [('user_id', 1), ('year', 1), ('kw', 1)], unique=True)
        
        # Homepage-Notices-Indizes
        mongodb.create_index('homepage_notices', 'is_active')
        mongodb.create_index('homepage_notices', 'priority')
        mongodb.create_index('homepage_notices', 'created_at')
        # Compound-Index für aktive Notices nach Priorität
        mongodb.create_index('homepage_notices', [('is_active', 1), ('priority', -1), ('created_at', -1)])
        
        # Messages-Indizes
        mongodb.create_index('messages', 'ticket_id')
        mongodb.create_index('messages', 'created_at')
        # Compound-Index für Ticket + Datum
        mongodb.create_index('messages', [('ticket_id', 1), ('created_at', -1)])
        
        # Ticket-History-Indizes
        mongodb.create_index('ticket_history', 'ticket_id')
        mongodb.create_index('ticket_history', 'created_at')
        # Compound-Index für Ticket + Datum
        mongodb.create_index('ticket_history', [('ticket_id', 1), ('created_at', -1)])
        
        # System-Locks (Auto-Backup Koordination)
        try:
            mongodb.create_index('system_locks', 'created_at', expireAfterSeconds=3600)
        except Exception:
            pass
        try:
            mongodb.create_index('system_locks', 'key')
        except Exception:
            pass
        
        # Backup-Runs Protokoll
        try:
            mongodb.create_index('backup_runs', 'created_at')
        except Exception:
            pass
        
        logger.info("MongoDB-Indizes erfolgreich erstellt")
        
        # Datenbankinitialisierung
        from app.utils.database_helpers import ensure_default_settings, migrate_old_data_to_settings
        
        # Stelle sicher, dass die settings Collections existieren
        ensure_default_settings()
        
        # Migriere alte Daten (falls vorhanden)
        migrate_old_data_to_settings()
        
        logger.info("Datenbankinitialisierung abgeschlossen")
        
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der MongoDB-Indizes: [Interner Fehler]")
        raise   