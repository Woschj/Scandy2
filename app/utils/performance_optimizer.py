"""
Performance Optimizer für Scandy App
Optimiert Datenbank-Indizes und Query-Performance
"""

import logging
from typing import Dict, Any, List
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)


class IndexOptimizer:
    """Optimiert Datenbank-Indizes für bessere Performance"""
    
    @staticmethod
    def ensure_indexes():
        """Stellt sicher, dass alle wichtigen Indizes existieren"""
        try:
            logger.info("Starting index optimization...")
            
            # Werkzeuge-Indizes
            IndexOptimizer._ensure_tool_indexes()
            
            # Mitarbeiter-Indizes  
            IndexOptimizer._ensure_worker_indexes()
            
            # Verbrauchsmaterial-Indizes
            IndexOptimizer._ensure_consumable_indexes()
            
            # Ausleihen-Indizes
            IndexOptimizer._ensure_lending_indexes()
            
            # Ticket-Indizes
            IndexOptimizer._ensure_ticket_indexes()
            
            # System-Indizes
            IndexOptimizer._ensure_system_indexes()

            # Job-Indizes (Bolt ⚡)
            IndexOptimizer._ensure_job_indexes()
            
            logger.info("Index optimization completed successfully")
            
        except Exception as e:
            logger.error(f"Error during index optimization: [Interner Fehler]")
            raise
    
    @staticmethod
    def _ensure_tool_indexes():
        """Werkzeuge-Indizes optimieren"""
        try:
            # Basis-Indizes
            mongodb.create_index('tools', [('department', 1), ('barcode', 1)], unique=True, sparse=True)
            mongodb.create_index('tools', 'name')
            mongodb.create_index('tools', 'category')
            mongodb.create_index('tools', 'location')
            mongodb.create_index('tools', 'status')
            mongodb.create_index('tools', 'deleted')
            
            # Compound-Indizes für häufige Queries
            mongodb.create_index('tools', [('status', 1), ('category', 1)])
            mongodb.create_index('tools', [('location', 1), ('status', 1)])
            mongodb.create_index('tools', [('deleted', 1), ('status', 1)])
            mongodb.create_index('tools', [('department', 1), ('status', 1)])
            
            # Dashboard-spezifische Indizes
            mongodb.create_index('tools', [('deleted', 1), ('status', 1), ('category', 1)])
            
            logger.info("Tool indexes optimized")
            
        except Exception as e:
            logger.error(f"Error optimizing tool indexes: [Interner Fehler]")
    
    @staticmethod
    def _ensure_worker_indexes():
        """Mitarbeiter-Indizes optimieren"""
        try:
            # Basis-Indizes
            mongodb.create_index('workers', [('department', 1), ('barcode', 1)], unique=True, sparse=True)
            mongodb.create_index('workers', 'lastname')
            mongodb.create_index('workers', 'department')
            mongodb.create_index('workers', 'deleted')
            
            # Compound-Indizes
            mongodb.create_index('workers', [('department', 1), ('lastname', 1)])
            mongodb.create_index('workers', [('deleted', 1), ('department', 1)])
            
            logger.info("Worker indexes optimized")
            
        except Exception as e:
            logger.error(f"Error optimizing worker indexes: [Interner Fehler]")
    
    @staticmethod
    def _ensure_consumable_indexes():
        """Verbrauchsmaterial-Indizes optimieren"""
        try:
            # Basis-Indizes
            mongodb.create_index('consumables', [('department', 1), ('barcode', 1)], unique=True, sparse=True)
            mongodb.create_index('consumables', 'name')
            mongodb.create_index('consumables', 'category')
            mongodb.create_index('consumables', 'location')
            mongodb.create_index('consumables', 'quantity')
            mongodb.create_index('consumables', 'deleted')
            
            # Compound-Indizes für Dashboard-Queries
            mongodb.create_index('consumables', [('deleted', 1), ('quantity', 1)])
            mongodb.create_index('consumables', [('category', 1), ('quantity', 1)])
            mongodb.create_index('consumables', [('deleted', 1), ('category', 1)])
            
            # Spezielle Indizes für Stock-Status
            mongodb.create_index('consumables', [('deleted', 1), ('quantity', 1), ('min_quantity', 1)])
            
            logger.info("Consumable indexes optimized")
            
        except Exception as e:
            logger.error(f"Error optimizing consumable indexes: [Interner Fehler]")
    
    @staticmethod
    def _ensure_lending_indexes():
        """Ausleihen-Indizes optimieren"""
        try:
            # Basis-Indizes
            mongodb.create_index('lendings', 'tool_barcode')
            mongodb.create_index('lendings', 'worker_barcode')
            mongodb.create_index('lendings', 'lent_at')
            mongodb.create_index('lendings', 'returned_at')
            
            # Compound-Indizes für häufige Queries
            mongodb.create_index('lendings', [('returned_at', 1), ('lent_at', 1)])
            mongodb.create_index('lendings', [('worker_barcode', 1), ('returned_at', 1)])
            mongodb.create_index('lendings', [('tool_barcode', 1), ('returned_at', 1)])
            
            # Dashboard-spezifische Indizes
            mongodb.create_index('lendings', [('returned_at', 1)])  # Für aktive Ausleihen
            
            logger.info("Lending indexes optimized")
            
        except Exception as e:
            logger.error(f"Error optimizing lending indexes: [Interner Fehler]")
    
    @staticmethod
    def _ensure_ticket_indexes():
        """Ticket-Indizes optimieren"""
        try:
            # Basis-Indizes
            mongodb.create_index('tickets', 'status')
            mongodb.create_index('tickets', 'assigned_to')
            mongodb.create_index('tickets', 'created_at')
            mongodb.create_index('tickets', 'priority')
            mongodb.create_index('tickets', 'deleted')
            
            # Compound-Indizes
            mongodb.create_index('tickets', [('status', 1), ('category', 1)])
            mongodb.create_index('tickets', [('assigned_to', 1), ('status', 1)])
            mongodb.create_index('tickets', [('deleted', 1), ('status', 1)])
            mongodb.create_index('tickets', [('priority', 1), ('status', 1)])
            
            logger.info("Ticket indexes optimized")
            
        except Exception as e:
            logger.error(f"Error optimizing ticket indexes: [Interner Fehler]")
    
    @staticmethod
    def _ensure_system_indexes():
        """System-Indizes optimieren"""
        try:
            # Benutzer-Indizes
            mongodb.create_index('users', 'username', unique=True)
            mongodb.create_index('users', 'email')
            mongodb.create_index('users', [('role', 1), ('is_active', 1)])
            
            # Settings-Indizes
            mongodb.create_index('settings', [('department', 1), ('key', 1)], unique=True, sparse=True)
            
            # Verbrauchsmaterial-Verwendung
            mongodb.create_index('consumable_usages', 'consumable_barcode')
            mongodb.create_index('consumable_usages', 'worker_barcode')
            mongodb.create_index('consumable_usages', 'used_at')
            mongodb.create_index('consumable_usages', [('consumable_barcode', 1), ('used_at', -1)])
            
            logger.info("System indexes optimized")
            
        except Exception as e:
            logger.error(f"Error optimizing system indexes: [Interner Fehler]")

    @staticmethod
    def _ensure_job_indexes():
        """Job-Indizes optimieren (Bolt ⚡)"""
        try:
            # Basis-Indizes
            mongodb.create_index('jobs', 'job_number', unique=True)
            mongodb.create_index('jobs', 'created_at')
            mongodb.create_index('jobs', 'is_active')

            # Such-Indizes
            mongodb.create_index('jobs', 'title')
            mongodb.create_index('jobs', 'company')

            logger.info("Job indexes optimized")

        except Exception as e:
            logger.error(f"Error optimizing job indexes: {e}")


class QueryOptimizer:
    """Optimiert spezifische Queries für bessere Performance"""
    
    @staticmethod
    def get_dashboard_statistics_optimized() -> Dict[str, Any]:
        """Optimierte Dashboard-Statistiken mit gezielten Aggregationen (Bolt ⚡)"""
        try:
            # 1. Tool-Statistiken (Status-Zählung)
            tool_pipeline = [{'$match': {'deleted': {'$ne': True}}}, {'$group': {
                '_id': None, 'total': {'$sum': 1},
                'available': {'$sum': {'$cond': [{'$in': [{'$toLower': {'$ifNull': ['$status', 'available']}}, ['available', 'verfügbar', 'bereit']]}, 1, 0]}},
                'lent': {'$sum': {'$cond': [{'$in': [{'$toLower': {'$ifNull': ['$status', '']}}, ['lent', 'ausgeliehen']]}, 1, 0]}},
                'defect': {'$sum': {'$cond': [{'$in': [{'$toLower': {'$ifNull': ['$status', '']}}, ['defect', 'defekt']]}, 1, 0]}}
            }}]
            tool_res = list(mongodb.aggregate('tools', tool_pipeline))
            tool_stats = tool_res[0] if tool_res else {'total': 0, 'available': 0, 'lent': 0, 'defect': 0}
            tool_stats.pop('_id', None)

            # 2. Consumable-Statistiken
            cons_pipeline = [{'$match': {'deleted': {'$ne': True}}}, {'$group': {
                '_id': None, 'total': {'$sum': 1},
                'sufficient': {'$sum': {'$cond': [{'$gt': ['$quantity', '$min_quantity']}, 1, 0]}},
                'warning': {'$sum': {'$cond': [{'$and': [{'$lte': ['$quantity', '$min_quantity']}, {'$gt': ['$quantity', 0]}]}, 1, 0]}},
                'critical': {'$sum': {'$cond': [{'$eq': ['$quantity', 0]}, 1, 0]}}
            }}]
            cons_res = list(mongodb.aggregate('consumables', cons_pipeline))
            cons_stats = cons_res[0] if cons_res else {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0}
            cons_stats.pop('_id', None)

            # 3. Worker-Statistiken (inkl. Abteilungs-Breakdown für Home-Page)
            worker_pipeline = [{'$match': {'deleted': {'$ne': True}}}, {'$facet': {
                'total': [{'$count': 'count'}],
                'by_dept': [{'$group': {'_id': '$department', 'count': {'$sum': 1}}}, {'$sort': {'count': -1}}]
            }}]
            worker_res = list(mongodb.aggregate('workers', worker_pipeline))
            if worker_res:
                wr = worker_res[0]
                worker_stats = {
                    'total': wr['total'][0]['count'] if wr['total'] else 0,
                    'by_department': [{'name': d['_id'] or 'Ohne Abteilung', 'count': d['count']} for d in wr['by_dept']]
                }
            else:
                worker_stats = {'total': 0, 'by_department': []}

            return {
                'tool_stats': tool_stats, 'consumable_stats': cons_stats, 'worker_stats': worker_stats,
                'lending_stats': {'active': mongodb.count_documents('lendings', {'returned_at': None})}
            }
        except Exception as e:
            logger.error(f"Error in optimized dashboard statistics: {e}")
            return QueryOptimizer._get_dashboard_statistics_fallback()
    
    @staticmethod
    def _get_dashboard_statistics_fallback() -> Dict[str, Any]:
        """Fallback-Methode mit ursprünglichen count_documents"""
        try:
            tool_stats = {
                'total': mongodb.count_documents('tools', {'deleted': {'$ne': True}}),
                'available': mongodb.count_documents('tools', {
                    'deleted': {'$ne': True},
                    '$or': [{'status': 'available'}, {'status': 'bereit'}]
                }),
                'lent': mongodb.count_documents('tools', {
                    'deleted': {'$ne': True},
                    '$or': [{'status': 'lent'}, {'status': 'ausgeliehen'}]
                }),
                'defect': mongodb.count_documents('tools', {
                    'deleted': {'$ne': True},
                    '$or': [{'status': 'defect'}, {'status': 'defekt'}]
                })
            }
            
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
            
            worker_stats = {
                'total': mongodb.count_documents('workers', {'deleted': {'$ne': True}})
            }
            
            lending_stats = {
                'active': mongodb.count_documents('lendings', {'returned_at': {'$exists': False}})
            }
            
            return {
                'tool_stats': tool_stats,
                'consumable_stats': consumable_stats,
                'worker_stats': worker_stats,
                'lending_stats': lending_stats
            }
            
        except Exception as e:
            logger.error(f"Error in fallback dashboard statistics: [Interner Fehler]")
            return {
                'tool_stats': {'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
                'consumable_stats': {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
                'worker_stats': {'total': 0},
                'lending_stats': {'active': 0}
            }
