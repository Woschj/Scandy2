"""
Zentraler Statistics Service für Scandy
Berechnet alle Statistiken an einem Ort und macht sie wiederverwendbar
"""
from typing import Dict, Any, List
from datetime import datetime
from app.models.mongodb_database import mongodb
from app.models.mongodb_models import MongoDBTool
from app.utils.performance_optimizer import QueryOptimizer
from app.utils.cache_manager import cached, invalidate_cache_pattern
import logging

logger = logging.getLogger(__name__)

class StatisticsService:
    """Zentraler Service für alle Statistiken"""
    
    @staticmethod
    @cached(ttl_seconds=60, key_prefix="dashboard_stats_")  # 1 Minute Cache
    def get_all_statistics() -> Dict[str, Any]:
        """
        Lädt alle Statistiken auf einmal.
        Wiederverwendbar für Dashboard, Admin-Dashboard und Startseite.
        OPTIMIERT: Verwendet QueryOptimizer für bessere Performance
        """
        try:
            # OPTIMIERT: Verwende optimierte Dashboard-Statistiken
            base_stats = QueryOptimizer.get_dashboard_statistics_optimized()
            
            # Ticket-Statistiken
            ticket_stats = StatisticsService._get_ticket_statistics()
            
            # Duplikat-Barcodes
            duplicate_barcodes = MongoDBTool.get_duplicate_barcodes()
            
            # Bestandsprognose
            consumables_forecast = MongoDBTool.get_consumables_forecast()
            
            # Überfällige Ausleihen
            overdue_loans = StatisticsService._get_overdue_loans()
            
            return {
                'tool_stats': base_stats['tool_stats'],
                'consumable_stats': base_stats['consumable_stats'],
                'worker_stats': base_stats['worker_stats'],
                'ticket_stats': ticket_stats,
                'duplicate_barcodes': duplicate_barcodes,
                'consumables_forecast': consumables_forecast,
                'overdue_loans': overdue_loans
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Statistiken: [Interner Fehler]")
            return StatisticsService._get_fallback_statistics()
    
    @staticmethod
    def _get_ticket_statistics() -> Dict[str, int]:
        """Berechnet Ticket-Statistiken"""
        try:
            ticket_pipeline = [
                {'$match': {'deleted': {'$ne': True}}},
                {
                    '$group': {
                        '_id': None,
                        'total': {'$sum': 1},
                        'open': {
                            '$sum': {
                                '$cond': [{'$eq': ['$status', 'offen']}, 1, 0]
                            }
                        },
                        'in_progress': {
                            '$sum': {
                                '$cond': [{'$eq': ['$status', 'in_bearbeitung']}, 1, 0]
                            }
                        },
                        'closed': {
                            '$sum': {
                                '$cond': [{'$eq': ['$status', 'geschlossen']}, 1, 0]
                            }
                        }
                    }
                }
            ]
            
            ticket_stats_result = list(mongodb.db.tickets.aggregate(ticket_pipeline))
            return ticket_stats_result[0] if ticket_stats_result else {
                'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0
            }
            
        except Exception as e:
            logger.error(f"Fehler bei Ticket-Statistiken: [Interner Fehler]")
            return {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
    
    @staticmethod
    def _get_overdue_loans() -> List[Dict[str, Any]]:
        """Findet alle überfälligen Ausleihen (Optimiert mit Aggregation zur Vermeidung von N+1 Problemen)"""
        try:
            today = datetime.now().date()
            today_dt = datetime.combine(today, datetime.min.time())
            
            # Aggregation-Pipeline zur Vermeidung von N+1 Problemen (Bolt ⚡)
            # OPTIMIERT: Filtert überfällige Ausleihen direkt in der DB (Bolt ⚡)
            pipeline = [
                {
                    '$match': {
                        'returned_at': None,
                        'expected_return_date': {'$exists': True, '$ne': None},
                        '$or': [
                            {'expected_return_date': {'$lt': today_dt}},
                            {'expected_return_date': {
                                '$lt': today.strftime('%Y-%m-%d')
                            }}
                        ]
                    }
                },
                {
                    '$lookup': {
                        'from': 'tools',
                        'localField': 'tool_barcode',
                        'foreignField': 'barcode',
                        'as': 'tool_info'
                    }
                },
                {'$unwind': {'path': '$tool_info', 'preserveNullAndEmptyArrays': True}},
                {
                    '$lookup': {
                        'from': 'workers',
                        'localField': 'worker_barcode',
                        'foreignField': 'barcode',
                        'as': 'worker_info'
                    }
                },
                {'$unwind': {'path': '$worker_info', 'preserveNullAndEmptyArrays': True}}
            ]

            active_loans = mongodb.aggregate('lendings', pipeline)
            
            overdue_loans = []
            
            for loan in active_loans:
                expected_date = loan.get('expected_return_date')
                
                # Konvertiere String zu datetime falls nötig
                if isinstance(expected_date, str):
                    try:
                        expected_date = datetime.strptime(
                            expected_date, '%Y-%m-%d'
                        )
                    except ValueError:
                        continue
                
                if expected_date:
                    # Nutze die bereits geladenen Informationen statt neuer Datenbankabfragen (N+1 Fix Bolt ⚡)
                    tool = loan.get('tool_info')
                    worker = loan.get('worker_info')
                    
                    # Filter für gelöschte Mitarbeiter (da mongomock kein complex lookup unterstützt)
                    if worker and worker.get('deleted') == True:
                        worker = None
                    
                    # Berechne Tage überfällig
                    days_overdue = (today - expected_date.date()).days
                    
                    overdue_loans.append({
                        'tool_name': tool.get('name') if tool else 'Unbekanntes Werkzeug',
                        'tool_barcode': loan.get('tool_barcode'),
                        'worker_name': f"{worker['firstname']} {worker['lastname']}" if (worker and worker.get('firstname') and worker.get('lastname')) else 'Unbekannt',
                        'worker_barcode': loan.get('worker_barcode'),
                        'expected_return_date': expected_date,
                        'days_overdue': days_overdue,
                        'lent_at': loan.get('lent_at')
                    })
            
            # Sortiere nach Anzahl der überfälligen Tage (absteigend)
            overdue_loans.sort(key=lambda x: x['days_overdue'], reverse=True)
            
            return overdue_loans
            
        except Exception as e:
            logger.error(f"Fehler beim Berechnen überfälliger Ausleihen: {e}")
            return []
    
    @staticmethod
    def _get_fallback_statistics() -> Dict[str, Any]:
        """Fallback-Statistiken bei Fehlern"""
        return {
            'tool_stats': {'total': 0, 'available': 0, 'lent': 0, 'defect': 0},
            'consumable_stats': {'total': 0, 'sufficient': 0, 'warning': 0, 'critical': 0},
            'worker_stats': {'total': 0, 'by_department': []},
            'ticket_stats': {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0},
            'duplicate_barcodes': [],
            'consumables_forecast': [],
            'overdue_loans': []
        }
    
    @staticmethod
    @cached(ttl_seconds=300, key_prefix="notices_")  # 5 Minuten Cache
    def get_notices() -> List[Dict[str, Any]]:
        """Lädt aktive Hinweise aus der Datenbank"""
        try:
            from flask import g
            current_dept = getattr(g, 'current_department', None)
            query = {'is_active': True}
            if current_dept:
                query['department'] = current_dept
            notices_list = list(mongodb.find('homepage_notices', query))
            # Sortiere nach Priorität und Erstellungsdatum
            notices_list.sort(key=lambda x: (x.get('priority', 0), x.get('created_at', datetime.min)), reverse=True)
            return notices_list
        except Exception as e:
            logger.error(f"Fehler beim Laden der Hinweise: [Interner Fehler]")
            return []
    
    @staticmethod
    def invalidate_dashboard_cache():
        """Invalidiert Dashboard-Cache bei Datenänderungen"""
        try:
            invalidated = invalidate_cache_pattern("dashboard_stats_")
            logger.info(f"Invalidated {invalidated} dashboard cache entries")
            return invalidated
        except Exception as e:
            logger.error(f"Error invalidating dashboard cache: [Interner Fehler]")
            return 0 