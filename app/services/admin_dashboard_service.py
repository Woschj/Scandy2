"""
Admin Dashboard Service

Dieser Service enthält alle Funktionen für das Admin-Dashboard,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class AdminDashboardService:
    """Service für Admin-Dashboard-Funktionen"""
    
    @staticmethod
    def _safe_datetime_conversion(date_value):
        """
        Konvertiert sicher String-Datumsfelder zu datetime Objekten
        Unterstützt verschiedene Datumsformate für alte Backups
        """
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, str):
            try:
                # Versuche verschiedene Datumsformate
                formats = [
                    '%Y-%m-%d %H:%M:%S.%f',  # 2025-06-27 14:13:12.387000
                    '%Y-%m-%d %H:%M:%S',     # 2025-06-27 14:13:12
                    '%Y-%m-%dT%H:%M:%S.%f',  # 2025-06-27T14:13:12.387000
                    '%Y-%m-%dT%H:%M:%S',     # 2025-06-27T14:13:12
                    '%Y-%m-%d',              # 2025-06-27
                    '%Y-%m-%dT%H:%M:%S.%fZ', # ISO mit Z
                    '%Y-%m-%dT%H:%M:%SZ'     # ISO mit Z
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except ValueError:
                        continue
                
                # Fallback: ISO-Format
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except Exception:
                logger.warning(f"Konnte Datum nicht konvertieren: {date_value}")
                return datetime.now()
        else:
            return datetime.now()
    
    @staticmethod
    def _safe_document_processing(doc, date_fields=None):
        """
        Verarbeitet ein Dokument sicher und konvertiert Datumsfelder
        """
        if not isinstance(doc, dict):
            return doc
            
        if date_fields is None:
            date_fields = ['created_at', 'updated_at', 'modified_at', 'deleted_at', 
                          'lent_at', 'returned_at', 'used_at', 'due_date', 'resolved_at']
        
        processed_doc = doc.copy()
        for field in date_fields:
            if field in processed_doc:
                processed_doc[field] = AdminDashboardService._safe_datetime_conversion(processed_doc[field])
        
        return processed_doc
    
    @staticmethod
    def get_recent_activity() -> List[Dict[str, Any]]:
        """Hole die letzten Aktivitäten"""
        try:
            activities = []
            
            # Hole die letzten 10 Ausleihen
            try:
                recent_lendings = list(mongodb.find('lendings', {}, sort=[('lent_at', -1)], limit=10))
                
                # Ausleihen verarbeiten
                for lending in recent_lendings:
                    try:
                        # Sichere Dokumentverarbeitung
                        lending = AdminDashboardService._safe_document_processing(lending, ['lent_at', 'returned_at'])
                        
                        tool = mongodb.find_one('tools', {'barcode': lending.get('tool_barcode', '')})
                        worker = mongodb.find_one('workers', {'barcode': lending.get('worker_barcode', '')})
                        
                        if tool and worker:
                            # Sichere Dokumentverarbeitung für Tool und Worker
                            tool = AdminDashboardService._safe_document_processing(tool)
                            worker = AdminDashboardService._safe_document_processing(worker)
                            
                            activities.append({
                                'type': 'lending',
                                'timestamp': lending.get('lent_at', datetime.now()),
                                'tool_name': tool.get('name', 'Unbekanntes Tool'),
                                'worker_name': worker.get('name', 'Unbekannter Worker'),
                                'status': lending.get('status', 'unbekannt'),
                                'id': str(lending.get('_id', ''))
                            })
                    except Exception as e:
                        logger.warning(f"Fehler bei Verarbeitung einer Ausleihe: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"Fehler beim Laden der Ausleihen: {str(e)}")
            
            # Hole die letzten 10 Verbrauchsmaterial-Ausgaben
            try:
                recent_usages = list(mongodb.find('consumable_usages', {}, sort=[('used_at', -1)], limit=10))
                
                # Verbrauchsmaterial-Ausgaben verarbeiten
                for usage in recent_usages:
                    try:
                        # Sichere Dokumentverarbeitung
                        usage = AdminDashboardService._safe_document_processing(usage, ['used_at'])
                        
                        consumable = mongodb.find_one('consumables', {'barcode': usage.get('consumable_barcode', '')})
                        worker = mongodb.find_one('workers', {'barcode': usage.get('worker_barcode', '')})
                        
                        if consumable and worker:
                            # Sichere Dokumentverarbeitung
                            consumable = AdminDashboardService._safe_document_processing(consumable)
                            worker = AdminDashboardService._safe_document_processing(worker)
                            
                            activities.append({
                                'type': 'consumable_usage',
                                'timestamp': usage.get('used_at', datetime.now()),
                                'consumable_name': consumable.get('name', 'Unbekanntes Verbrauchsmaterial'),
                                'worker_name': worker.get('name', 'Unbekannter Worker'),
                                'quantity': usage.get('quantity', 0),
                                'id': str(usage.get('_id', ''))
                            })
                    except Exception as e:
                        logger.warning(f"Fehler bei Verarbeitung einer Verbrauchsmaterial-Ausgabe: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Ausgaben: {str(e)}")
            
            # Sortiere nach Timestamp
            activities.sort(key=lambda x: x.get('timestamp', datetime.now()), reverse=True)
            
            return activities[:20]  # Maximal 20 Aktivitäten
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der letzten Aktivitäten: {str(e)}")
            return []

    @staticmethod
    def get_material_usage() -> Dict[str, Any]:
        """Hole die Materialnutzung"""
        try:
            # Hole Verbrauchsmaterial-Ausgaben der letzten 30 Tage
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Sichere Pipeline mit Datumsbehandlung
            pipeline = [
                {
                    '$addFields': {
                        'safe_used_at': {
                            '$cond': {
                                'if': {'$type': '$used_at'},
                                'then': '$used_at',
                                'else': datetime.now()
                            }
                        }
                    }
                },
                {
                    '$match': {
                        'safe_used_at': {'$gte': thirty_days_ago}
                    }
                },
                {
                    '$lookup': {
                        'from': 'consumables',
                        'localField': 'consumable_barcode',
                        'foreignField': 'barcode',
                        'as': 'consumable'
                    }
                },
                {
                    '$unwind': '$consumable'
                },
                {
                    '$group': {
                        '_id': '$consumable.name',
                        'total_quantity': {'$sum': '$quantity'},
                        'usage_count': {'$sum': 1}
                    }
                },
                {
                    '$sort': {'total_quantity': -1}
                },
                {
                    '$limit': 10
                }
            ]
            
            usage_data = list(mongodb.aggregate('consumable_usages', pipeline))
            
            return {
                'usage_data': usage_data,
                'period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Materialnutzung: {str(e)}")
            return {'usage_data': [], 'period_days': 30}

    @staticmethod  
    def get_overdue_loans() -> List[Dict[str, Any]]:
        """Findet alle überfälligen Ausleihen für das Admin-Dashboard"""
        try:
            from app.services.statistics_service import StatisticsService
            return StatisticsService._get_overdue_loans()
        except Exception as e:
            logger.error(f"Fehler beim Laden überfälliger Ausleihen: {str(e)}")
            return []

    @staticmethod
    def get_warnings() -> Dict[str, List[Dict[str, Any]]]:
        """Hole alle Warnungen für das Dashboard"""
        try:
            warnings = {
                'defect_tools': [],
                'overdue_lendings': [],
                'low_stock_consumables': []
            }
            
            # Defekte Werkzeuge
            try:
                defect_tools = list(mongodb.find('tools', {'status': 'defekt', 'deleted': {'$ne': True}}))
                for tool in defect_tools:
                    try:
                        # Sichere Dokumentverarbeitung
                        tool = AdminDashboardService._safe_document_processing(tool)
                        warnings['defect_tools'].append({
                            'name': tool.get('name', 'Unbekanntes Tool'),
                            'barcode': tool.get('barcode', ''),
                            'status': 'defekt',
                            'severity': 'error'
                        })
                    except Exception as e:
                        logger.warning(f"Fehler bei defektem Tool: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Fehler beim Laden defekter Tools: {str(e)}")
            
            # Überfällige Ausleihen - nutze die neue Logik basierend auf expected_return_date
            try:
                overdue_loans = AdminDashboardService.get_overdue_loans()
                
                for loan in overdue_loans:
                    try:
                        warnings['overdue_lendings'].append({
                            'tool_name': loan.get('tool_name', 'Unbekanntes Tool'),
                            'tool_barcode': loan.get('tool_barcode', ''),
                            'worker_name': loan.get('worker_name', 'Unbekannt'), 
                            'worker_barcode': loan.get('worker_barcode', ''),
                            'days_overdue': loan.get('days_overdue', 0),
                            'expected_return_date': loan.get('expected_return_date'),
                            'severity': 'error' if loan.get('days_overdue', 0) > 7 else 'warning'
                        })
                    except Exception as e:
                        logger.warning(f"Fehler bei überfälliger Ausleihe: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Fehler beim Laden überfälliger Ausleihen: {str(e)}")

            # Legacy-Fallback für alte Ausleihen ohne expected_return_date
            try:
                active_lendings = list(mongodb.find('lendings', {
                    'returned_at': {'$exists': False},
                    'expected_return_date': {'$exists': False}
                }))
                
                for lending in active_lendings:
                    try:
                        # Sichere Dokumentverarbeitung
                        lending = AdminDashboardService._safe_document_processing(lending, ['lent_at', 'due_date'])
                        
                        # Prüfe ob überfällig (mehr als 14 Tage ohne expected_return_date)
                        lent_at = lending.get('lent_at')
                        if lent_at and isinstance(lent_at, datetime):
                            days_overdue = (datetime.now() - lent_at).days
                            if days_overdue > 14:
                                tool = mongodb.find_one('tools', {'barcode': lending.get('tool_barcode', '')})
                                worker = mongodb.find_one('workers', {'barcode': lending.get('worker_barcode', '')})
                                
                                if tool and worker:
                                    tool = AdminDashboardService._safe_document_processing(tool)
                                    worker = AdminDashboardService._safe_document_processing(worker)
                                    
                                    warnings['overdue_lendings'].append({
                                        'tool_name': tool.get('name', 'Unbekanntes Tool'),
                                        'worker_name': worker.get('name', 'Unbekannter Worker'),
                                        'days_overdue': days_overdue,
                                        'lent_at': lent_at,
                                        'severity': 'warning'
                                    })
                    except Exception as e:
                        logger.warning(f"Fehler bei überfälliger Ausleihe: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Fehler beim Laden überfälliger Ausleihen: {str(e)}")
            
            # Verbrauchsmaterial mit niedrigem Bestand
            try:
                low_stock_consumables = list(mongodb.find('consumables', {'stock': {'$lt': 10}, 'deleted': {'$ne': True}}))
                for consumable in low_stock_consumables:
                    try:
                        # Sichere Dokumentverarbeitung
                        consumable = AdminDashboardService._safe_document_processing(consumable)
                        warnings['low_stock_consumables'].append({
                            'name': consumable.get('name', 'Unbekanntes Verbrauchsmaterial'),
                            'barcode': consumable.get('barcode', ''),
                            'stock': consumable.get('stock', 0),
                            'severity': 'warning'
                        })
                    except Exception as e:
                        logger.warning(f"Fehler bei Verbrauchsmaterial mit niedrigem Bestand: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Fehler beim Laden von Verbrauchsmaterial mit niedrigem Bestand: {str(e)}")
            
            return warnings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Warnungen: {str(e)}")
            return {'defect_tools': [], 'overdue_lendings': [], 'low_stock_consumables': []}

    @staticmethod
    def get_backup_info() -> Dict[str, Any]:
        """Hole Backup-Informationen"""
        try:
            from app.utils.backup_manager import backup_manager
            
            backup_dir = backup_manager.backup_dir
            backups = []
            
            if backup_dir.exists():
                for backup_file in backup_dir.glob('*.json'):
                    if backup_file.is_file():
                        stat = backup_file.stat()
                        backups.append({
                            'filename': backup_file.name,
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime),
                            'size_mb': round(stat.st_size / (1024 * 1024), 2)
                        })
            
            # Sortiere nach Änderungsdatum (neueste zuerst)
            backups.sort(key=lambda x: x['modified'], reverse=True)
            
            return {
                'backups': backups,
                'total_count': len(backups),
                'total_size_mb': sum(b['size_mb'] for b in backups)
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Informationen: {str(e)}")
            return {'backups': [], 'total_count': 0, 'total_size_mb': 0}

    @staticmethod
    def get_consumables_forecast() -> List[Dict[str, Any]]:
        """Hole Verbrauchsmaterial-Prognosen"""
        try:
            # Verwende den zentralen Statistics Service
            from app.services.statistics_service import StatisticsService
            stats = StatisticsService.get_all_statistics()
            return stats.get('consumables_forecast', [])
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Prognosen: {str(e)}")
            return []

    @staticmethod
    def get_consumable_trend() -> Dict[str, Any]:
        """Hole Verbrauchsmaterial-Trends für Charts"""
        try:
            # Berechne Trend der letzten 30 Tage
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Sichere Pipeline mit Datumsbehandlung
            pipeline = [
                {
                    '$addFields': {
                        'safe_used_at': {
                            '$cond': {
                                'if': {'$type': '$used_at'},
                                'then': '$used_at',
                                'else': datetime.now()
                            }
                        }
                    }
                },
                {
                    '$match': {
                        'safe_used_at': {'$gte': thirty_days_ago}
                    }
                },
                {
                    '$group': {
                        '_id': {
                            'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$safe_used_at'}},
                            'consumable': '$consumable_barcode'
                        },
                        'total_quantity': {'$sum': '$quantity'}
                    }
                },
                {
                    '$group': {
                        '_id': '$_id.date',
                        'total_usage': {'$sum': '$total_quantity'}
                    }
                },
                {
                    '$sort': {'_id': 1}
                }
            ]
            
            trend_data = list(mongodb.aggregate('consumable_usages', pipeline))
            
            # Formatiere Daten für Chart.js
            labels = [item['_id'] for item in trend_data]
            data = [abs(item['total_usage']) for item in trend_data]  # Absolutwert da quantity negativ ist
            
            return {
                'labels': labels,
                'datasets': [{
                    'label': 'Täglicher Verbrauch',
                    'data': data,
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'tension': 0.1
                }]
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Trends: {str(e)}")
            return {'labels': [], 'datasets': []} 