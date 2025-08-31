"""
Zentraler Statistics Service für Scandy
Berechnet alle Statistiken an einem Ort und macht sie wiederverwendbar
"""
from typing import Dict, Any, List
from datetime import datetime
from app.models.mongodb_database import mongodb
from app.models.mongodb_models import MongoDBTool
import logging

logger = logging.getLogger(__name__)

class StatisticsService:
    """Zentraler Service für alle Statistiken"""
    
    @staticmethod
    def get_all_statistics() -> Dict[str, Any]:
        """
        Lädt alle Statistiken auf einmal.
        Wiederverwendbar für Dashboard, Admin-Dashboard und Startseite.
        """
        try:
            # Basis-Statistiken von MongoDBTool
            base_stats = MongoDBTool.get_statistics()
            
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
            logger.error(f"Fehler beim Laden der Statistiken: {str(e)}")
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
            logger.error(f"Fehler bei Ticket-Statistiken: {str(e)}")
            return {'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0}
    
    @staticmethod
    def _get_overdue_loans() -> List[Dict[str, Any]]:
        """Findet alle überfälligen Ausleihen"""
        try:
            today = datetime.now().date()
            
            # Finde alle aktiven Ausleihen mit Rückgabedatum
            active_loans = list(mongodb.find('lendings', {
                'returned_at': None,
                'expected_return_date': {'$exists': True, '$ne': None}
            }))
            
            overdue_loans = []
            
            for loan in active_loans:
                expected_date = loan.get('expected_return_date')
                if not expected_date:
                    continue
                
                # Konvertiere String zu datetime falls nötig
                if isinstance(expected_date, str):
                    try:
                        expected_date = datetime.strptime(expected_date, '%Y-%m-%d')
                    except ValueError:
                        continue
                
                # Prüfe ob überfällig
                if expected_date.date() < today:
                    # Hole Tool-Informationen
                    tool = mongodb.find_one('tools', {'barcode': loan.get('tool_barcode')})
                    
                    # Hole Mitarbeitende-Informationen
                    worker = mongodb.find_one('workers', {
                        'barcode': loan.get('worker_barcode'),
                        'deleted': {'$ne': True}
                    })
                    
                    # Berechne Tage überfällig
                    days_overdue = (today - expected_date.date()).days
                    
                    overdue_loans.append({
                        'tool_name': tool.get('name') if tool else 'Unbekanntes Werkzeug',
                        'tool_barcode': loan.get('tool_barcode'),
                        'worker_name': f"{worker['firstname']} {worker['lastname']}" if worker else 'Unbekannt',
                        'worker_barcode': loan.get('worker_barcode'),
                        'expected_return_date': expected_date,
                        'days_overdue': days_overdue,
                        'lent_at': loan.get('lent_at')
                    })
            
            # Sortiere nach Anzahl der überfälligen Tage (absteigend)
            overdue_loans.sort(key=lambda x: x['days_overdue'], reverse=True)
            
            return overdue_loans
            
        except Exception as e:
            logger.error(f"Fehler beim Berechnen überfälliger Ausleihen: {str(e)}")
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
            logger.error(f"Fehler beim Laden der Hinweise: {str(e)}")
            return [] 