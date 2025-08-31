"""
MongoDB-Modell für Werkzeuge
"""
from app.models.mongodb_database import mongodb
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Import der zentralen ID-Helper-Funktionen
from app.utils.id_helpers import convert_id_for_query

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
                logger.error(f"MongoDB-Ping fehlgeschlagen: {e}")
                raise Exception(f"MongoDB-Verbindung fehlgeschlagen: {e}")

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
            logger.error(f"Fehler in get_statistics: {e}")
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
        }, {'barcode': 1, 'name': 1}))

        consumable_barcodes = list(mongodb.find('consumables', {
            'deleted': {'$ne': True},
            'barcode': {'$exists': True, '$ne': None}
        }, {'barcode': 1, 'name': 1}))

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
