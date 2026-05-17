"""
Zentraler Tool Service für Scandy
Alle Werkzeug-Funktionalitäten an einem Ort
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from flask import current_app, g
from app.models.mongodb_database import mongodb
from app.services.lending_service import LendingService
from app.services.utility_service import UtilityService
from app.utils.database_helpers import get_locations_from_settings
import logging

logger = logging.getLogger(__name__)

class ToolService:
    """Zentraler Service für alle Werkzeug-Operationen"""
    
    def __init__(self):
        self.lending_service = None
        self.utility_service = None
    
    def _get_lending_service(self):
        """Lazy initialization des LendingService"""
        if self.lending_service is None:
            self.lending_service = LendingService()
        return self.lending_service
    
    def _get_utility_service(self):
        """Lazy initialization des UtilityService"""
        if self.utility_service is None:
            self.utility_service = UtilityService()
        return self.utility_service
    
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Holt alle aktiven Werkzeuge mit aktuellem Ausleihstatus (optimiert via Aggregation)
        
        Returns:
            List: Liste aller Werkzeuge
        """
        try:
            # Basis-Filter für Werkzeuge
            match_query = {'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                match_query['department'] = g.current_department

            # Aggregation-Pipeline zur Vermeidung von N+1 Lookups
            pipeline = [
                {'$match': match_query},
                {
                    '$lookup': {
                        'from': 'lendings',
                        'localField': 'barcode',
                        'foreignField': 'tool_barcode',
                        'as': 'active_lendings'
                    }
                },
                {
                    '$addFields': {
                        'current_lending': {
                            '$arrayElemAt': [
                                {'$filter': {
                                    'input': '$active_lendings',
                                    'as': 'l',
                                    'cond': {'$eq': ['$$l.returned_at', None]}
                                }},
                                0
                            ]
                        }
                    }
                },
                {
                    '$lookup': {
                        'from': 'workers',
                        'localField': 'current_lending.worker_barcode',
                        'foreignField': 'barcode',
                        'as': 'worker_info'
                    }
                },
                {
                    '$addFields': {
                        'worker': {'$arrayElemAt': ['$worker_info', 0]}
                    }
                }
            ]

            tools = mongodb.aggregate('tools', pipeline)
            
            # Post-Processing in Python (für Datumskonvertierung und Status-Logik)
            processed_tools = []
            now_date = datetime.now().date()

            for tool in tools:
                try:
                    tool = self._convert_datetime_fields(tool)
                    tool['id'] = str(tool['_id'])
                    
                    current_lending = tool.get('current_lending')
                    if current_lending:
                        worker = tool.get('worker', {})
                        worker_name = f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip() or 'Unbekannt'

                        tool['is_borrowed'] = True
                        tool['current_borrower'] = worker_name
                        tool['lent_to_worker_barcode'] = current_lending.get('worker_barcode')
                        tool['lent_to_worker_name'] = worker_name
                        tool['lent_at'] = current_lending.get('lent_at')
                        tool['expected_return_date'] = current_lending.get('expected_return_date')
                        
                        # Prüfe ob das Werkzeug überfällig ist
                        expected_date = tool['expected_return_date']
                        if expected_date:
                            # Konvertiere String zu datetime falls nötig
                            if isinstance(expected_date, str):
                                try:
                                    expected_date = datetime.strptime(expected_date, '%Y-%m-%d')
                                except ValueError:
                                    expected_date = None
                            
                            # Prüfe ob überfällig
                            if expected_date and (isinstance(expected_date, datetime) and expected_date.date() < now_date):
                                tool['status'] = 'überfällig'
                            else:
                                tool['status'] = 'ausgeliehen'
                        else:
                            tool['status'] = 'ausgeliehen'
                    else:
                        tool['is_borrowed'] = False
                        tool['lent_to_worker_barcode'] = None
                        tool['lent_to_worker_name'] = None
                        tool['lent_at'] = None
                        tool['expected_return_date'] = None
                        if not tool.get('status'):
                            tool['status'] = 'verfügbar'
                    
                    # Aufräumen der temporären Aggregations-Felder
                    tool.pop('active_lendings', None)
                    tool.pop('current_lending', None)
                    tool.pop('worker_info', None)
                    tool.pop('worker', None)

                    processed_tools.append(tool)
                except Exception as tool_error:
                    logger.error(f"Fehler beim Verarbeiten von Werkzeug {tool.get('barcode', 'unbekannt')}: {str(tool_error)}")
                    continue
            
            return processed_tools
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Werkzeuge: [Interner Fehler]")
            return []
    
    def get_tool_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Holt ein Werkzeug anhand des Barcodes
        
        Args:
            barcode: Barcode des Werkzeugs
            
        Returns:
            Optional[Dict]: Werkzeug-Daten oder None
        """
        try:
            query = {'barcode': barcode, 'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                query['department'] = g.current_department
            tool = mongodb.find_one('tools', query)
            if tool:
                tool = self._convert_datetime_fields(tool)
                tool['id'] = str(tool['_id'])
            return tool
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Werkzeugs {barcode}: [Interner Fehler]")
            return None
    
    def create_tool(self, tool_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt ein neues Werkzeug
        
        Args:
            tool_data: Werkzeug-Daten
            
        Returns:
            Tuple: (success, message, barcode)
        """
        try:
            # Validierung
            dept = getattr(g, 'current_department', None)
            if not dept:
                return False, 'Bitte Abteilung wählen, bevor Sie ein Werkzeug anlegen', None
            if not tool_data.get('name'):
                return False, 'Name ist erforderlich', None
            
            if not tool_data.get('barcode'):
                return False, 'Barcode ist erforderlich', None
            
            barcode = tool_data['barcode']
            
            # Prüfe ob der Barcode bereits existiert (nur innerhalb der aktuellen Abteilung)
            uniqueness_query = {'barcode': barcode, 'deleted': {'$ne': True}}
            if dept:
                uniqueness_query['department'] = dept
            existing_tool = mongodb.find_one('tools', uniqueness_query)
            if existing_tool:
                return False, 'Dieser Barcode existiert bereits', None
            
            # Werkzeug-Daten vorbereiten
            tool = {
                'name': tool_data['name'],
                'barcode': barcode,
                'description': tool_data.get('description', ''),
                'category': tool_data.get('category'),
                'location': tool_data.get('location'),
                'status': tool_data.get('status', 'verfügbar'),
                'serial_number': tool_data.get('serial_number', ''),
                'invoice_number': tool_data.get('invoice_number', ''),
                'mac_address': tool_data.get('mac_address', ''),
                'mac_address_wlan': tool_data.get('mac_address_wlan', ''),
                'user_groups': tool_data.get('user_groups', []),
                'additional_software': tool_data.get('additional_software', []),
                'department': dept,
                'created_at': datetime.now(),
                'modified_at': datetime.now(),
                'deleted': False
            }
            
            # Benutzerdefinierte Felder hinzufügen, falls vorhanden
            if 'custom_fields' in tool_data:
                tool['custom_fields'] = tool_data['custom_fields']
            
            # Werkzeug in Datenbank speichern
            result = mongodb.insert_one('tools', tool)
            
            logger.info(f"Werkzeug erstellt: {barcode}")
            return True, 'Werkzeug wurde erfolgreich erstellt', barcode
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Werkzeugs: [Interner Fehler]")
            return False, f'Fehler beim Erstellen des Werkzeugs: [Interner Fehler]', None
    
    def update_tool(self, barcode: str, tool_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Aktualisiert ein Werkzeug
        
        Args:
            barcode: Aktueller Barcode
            tool_data: Neue Werkzeug-Daten
            
        Returns:
            Tuple: (success, message, new_barcode)
        """
        try:
            tool = self.get_tool_by_barcode(barcode)
            if not tool:
                return False, 'Werkzeug nicht gefunden', barcode
            
            # Nur dann Barcode ändern, wenn er explizit angegeben wurde und sich unterscheidet
            new_barcode = tool_data.get('barcode')
            if new_barcode and new_barcode != barcode:
                # Prüfe ob der neue Barcode bereits existiert
                existing_query = {'barcode': new_barcode, 'deleted': {'$ne': True}}
                if getattr(g, 'current_department', None):
                    existing_query['department'] = g.current_department
                existing_tool = mongodb.find_one('tools', existing_query)
                if existing_tool:
                    return False, f'Der Barcode "{new_barcode}" existiert bereits', barcode
            else:
                # Barcode bleibt unverändert
                new_barcode = barcode
            
            # Prüfe ob das Werkzeug ausgeliehen ist
            current_lending = self._get_lending_service().get_current_lending(barcode)
            new_status = tool_data.get('status')
            
            # Status nur ändern, wenn er explizit angegeben wurde
            if new_status:
                if current_lending and new_status == 'defekt':
                    return False, 'Ein ausgeliehenes Werkzeug kann nicht als defekt markiert werden', barcode
            else:
                # Status bleibt unverändert
                new_status = tool.get('status', 'verfügbar')
            
            # Update-Daten vorbereiten
            update_data = {
                'name': tool_data.get('name', tool['name']),
                'description': tool_data.get('description', tool.get('description', '')),
                'category': tool_data.get('category', tool.get('category')),
                'location': tool_data.get('location', tool.get('location')),
                'status': new_status,
                'serial_number': tool_data.get('serial_number', tool.get('serial_number', '')),
                'invoice_number': tool_data.get('invoice_number', tool.get('invoice_number', '')),
                'mac_address': tool_data.get('mac_address', tool.get('mac_address', '')),
                'mac_address_wlan': tool_data.get('mac_address_wlan', tool.get('mac_address_wlan', '')),
                'user_groups': tool_data.get('user_groups', tool.get('user_groups', [])),
                'additional_software': tool_data.get('additional_software', tool.get('additional_software', [])),
                'modified_at': datetime.now()
            }
            
            # Benutzerdefinierte Felder hinzufügen, falls vorhanden
            if 'custom_fields' in tool_data:
                update_data['custom_fields'] = tool_data['custom_fields']
            
            if new_barcode != barcode:
                update_data['barcode'] = new_barcode
            
            # Update durchführen
            filter_query = {'barcode': barcode}
            if getattr(g, 'current_department', None):
                filter_query['department'] = g.current_department
            mongodb.update_one('tools', filter_query, {'$set': update_data})
            
            logger.info(f"Werkzeug aktualisiert: {barcode} -> {new_barcode}")
            return True, 'Werkzeug erfolgreich aktualisiert', new_barcode
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Werkzeugs: [Interner Fehler]")
            return False, f'Fehler beim Aktualisieren: [Interner Fehler]', barcode
    
    def delete_tool(self, barcode: str, permanent: bool = False) -> Tuple[bool, str]:
        """
        Löscht ein Werkzeug (soft oder permanent)
        
        Args:
            barcode: Barcode des Werkzeugs
            permanent: True für permanente Löschung
            
        Returns:
            Tuple: (success, message)
        """
        try:
            tool = self.get_tool_by_barcode(barcode)
            if not tool:
                return False, 'Werkzeug nicht gefunden'
            
            # Prüfe ob das Werkzeug ausgeliehen ist
            current_lending = self._get_lending_service().get_current_lending(barcode)
            if current_lending:
                return False, 'Ein ausgeliehenes Werkzeug kann nicht gelöscht werden'
            
            if permanent:
                # Permanente Löschung
                delete_query = {'barcode': barcode}
                if getattr(g, 'current_department', None):
                    delete_query['department'] = g.current_department
                mongodb.delete_one('tools', delete_query)
                # Auch alle zugehörigen Ausleihen löschen
                mongodb.delete_many('lendings', {'tool_barcode': barcode})
                
                logger.info(f"Werkzeug permanent gelöscht: {barcode}")
                return True, 'Werkzeug permanent gelöscht'
            else:
                # Soft-Delete
                soft_filter = {'barcode': barcode}
                if getattr(g, 'current_department', None):
                    soft_filter['department'] = g.current_department
                mongodb.update_one('tools', 
                                 soft_filter, 
                                 {'$set': {
                                     'deleted': True,
                                     'deleted_at': datetime.now()
                                 }})
                
                logger.info(f"Werkzeug soft-gelöscht: {barcode}")
                return True, 'Werkzeug gelöscht'
                
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Werkzeugs: [Interner Fehler]")
            return False, f'Fehler beim Löschen: [Interner Fehler]'
    
    def change_tool_status(self, barcode: str, new_status: str) -> Tuple[bool, str]:
        """
        Ändert den Status eines Werkzeugs
        
        Args:
            barcode: Barcode des Werkzeugs
            new_status: Neuer Status
            
        Returns:
            Tuple: (success, message)
        """
        try:
            if new_status not in ['verfügbar', 'defekt']:
                return False, 'Ungültiger Status'
            
            tool = self.get_tool_by_barcode(barcode)
            if not tool:
                return False, 'Werkzeug nicht gefunden'
            
            # Prüfe ob das Werkzeug ausgeliehen ist
            current_lending = self._get_lending_service().get_current_lending(barcode)
            if current_lending and new_status == 'defekt':
                return False, 'Ein ausgeliehenes Werkzeug kann nicht als defekt markiert werden'
            
            # Status aktualisieren
            filter_query = {'barcode': barcode}
            if getattr(g, 'current_department', None):
                filter_query['department'] = g.current_department
            mongodb.update_one('tools', 
                             filter_query, 
                             {'$set': {'status': new_status, 'modified_at': datetime.now()}})
            
            logger.info(f"Werkzeug-Status geändert: {barcode} -> {new_status}")
            return True, f'Status erfolgreich auf "{new_status}" geändert'
            
        except Exception as e:
            logger.error(f"Fehler beim Ändern des Werkzeug-Status: [Interner Fehler]")
            return False, f'Fehler beim Ändern: [Interner Fehler]'
    
    def get_tool_details(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Holt detaillierte Informationen zu einem Werkzeug
        
        Args:
            barcode: Barcode des Werkzeugs
            
        Returns:
            Optional[Dict]: Detaillierte Werkzeug-Informationen
        """
        try:
            tool = self.get_tool_by_barcode(barcode)
            if not tool:
                return None
            
            # Aktuelle Ausleihe hinzufügen
            current_lending = self._get_lending_service().get_current_lending(barcode)
            if current_lending:
                tool['current_borrower'] = current_lending.get('worker_name', 'Unbekannt')
                tool['lending_date'] = current_lending.get('lent_at')
                tool['is_available'] = False
                tool['lent_to_worker_barcode'] = current_lending.get('worker_barcode')
                tool['lent_to_worker_name'] = current_lending.get('worker_name', 'Unbekannt')
                tool['lent_at'] = current_lending.get('lent_at')
                tool['expected_return_date'] = current_lending.get('expected_return_date')
                
                # Prüfe ob das Werkzeug überfällig ist
                if current_lending.get('expected_return_date'):
                    expected_date = current_lending['expected_return_date']
                    # Konvertiere String zu datetime falls nötig
                    if isinstance(expected_date, str):
                        try:
                            expected_date = datetime.strptime(expected_date, '%Y-%m-%d')
                        except ValueError:
                            expected_date = None
                    
                    # Prüfe ob überfällig
                    if expected_date and expected_date.date() < datetime.now().date():
                        tool['status'] = 'überfällig'
                    else:
                        tool['status'] = 'ausgeliehen'
                else:
                    tool['status'] = 'ausgeliehen'
            else:
                tool['is_available'] = True
                tool['lent_to_worker_barcode'] = None
                tool['lent_to_worker_name'] = None
                tool['lent_at'] = None
                tool['expected_return_date'] = None
                if not tool.get('status'):
                    tool['status'] = 'verfügbar'
            
            # Ausleihhistorie hinzufügen
            lending_history = self._get_lending_service().get_tool_lending_history(barcode)
            tool['lending_history'] = lending_history
            
            # Software aus Nutzergruppen automatisch hinzufügen
            tool = self._merge_software_from_user_groups(tool)
            
            return tool
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Werkzeug-Details: [Interner Fehler]")
            return None
    
    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """
        Sucht nach Werkzeugen
        
        Args:
            query: Suchbegriff
            
        Returns:
            List: Liste der gefundenen Werkzeuge
        """
        try:
            # Suche in Name, Beschreibung und Barcode
            search_query = {
                'deleted': {'$ne': True},
                '$or': [
                    {'name': {'$regex': query, '$options': 'i'}},
                    {'description': {'$regex': query, '$options': 'i'}},
                    {'barcode': {'$regex': query, '$options': 'i'}}
                ]
            }
            
            if getattr(g, 'current_department', None):
                search_query['department'] = g.current_department
            tools = list(mongodb.find('tools', search_query))
            
            # Datetime-Felder konvertieren
            for tool in tools:
                tool = self._convert_datetime_fields(tool)
                tool['id'] = str(tool['_id'])
            
            return tools
            
        except Exception as e:
            logger.error(f"Fehler bei der Werkzeug-Suche: [Interner Fehler]")
            return []
    
    def get_tools_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Holt Werkzeuge nach Kategorie
        
        Args:
            category: Kategorie
            
        Returns:
            List: Liste der Werkzeuge in der Kategorie
        """
        try:
            query = {'category': category, 'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                query['department'] = g.current_department
            tools = list(mongodb.find('tools', query))
            
            # Datetime-Felder konvertieren
            for tool in tools:
                tool = self._convert_datetime_fields(tool)
                tool['id'] = str(tool['_id'])
            
            return tools
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Werkzeuge nach Kategorie: [Interner Fehler]")
            return []
    
    def get_tools_by_location(self, location: str) -> List[Dict[str, Any]]:
        """
        Holt Werkzeuge nach Standort
        
        Args:
            location: Standort
            
        Returns:
            List: Liste der Werkzeuge am Standort
        """
        try:
            query = {'location': location, 'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                query['department'] = g.current_department
            tools = list(mongodb.find('tools', query))
            
            # Datetime-Felder konvertieren
            for tool in tools:
                tool = self._convert_datetime_fields(tool)
                tool['id'] = str(tool['_id'])
            
            return tools
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Werkzeuge nach Standort: [Interner Fehler]")
            return []
    
    def get_tools_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Holt Werkzeuge nach Status
        
        Args:
            status: Status (verfügbar, defekt, ausgeliehen)
            
        Returns:
            List: Liste der Werkzeuge mit dem Status
        """
        try:
            if status == 'ausgeliehen':
                # Für ausgeliehene Werkzeuge müssen wir die Ausleihen prüfen
                borrowed_tools = []
                all_tools = self.get_all_tools()
                for tool in all_tools:
                    if tool.get('is_borrowed', False):
                        borrowed_tools.append(tool)
                return borrowed_tools
            else:
                # Für andere Status direkt in der tools Collection suchen
                query = {'status': status, 'deleted': {'$ne': True}}
                if getattr(g, 'current_department', None):
                    query['department'] = g.current_department
                tools = list(mongodb.find('tools', query))
                
                # Datetime-Felder konvertieren
                for tool in tools:
                    tool = self._convert_datetime_fields(tool)
                    tool['id'] = str(tool['_id'])
                
                return tools
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Werkzeuge nach Status: [Interner Fehler]")
            return []
    
    def get_tool_statistics(self) -> Dict[str, Any]:
        """
        Holt Statistiken für Werkzeuge (optimiert via Aggregation) (Bolt ⚡)
        Reduziert Datenbank-Abfragen und verlagert Berechnungen in die Datenbank.
        
        Returns:
            Dict: Verschiedene Statistiken
        """
        try:
            # Basis-Filter für Werkzeuge
            match_query = {'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                match_query['department'] = g.current_department

            # Aggregation-Pipeline zur effizienten Berechnung aller Statistiken in einem Durchgang
            pipeline = [
                {'$match': match_query},
                {
                    '$lookup': {
                        'from': 'lendings',
                        'localField': 'barcode',
                        'foreignField': 'tool_barcode',
                        'as': 'all_lendings'
                    }
                },
                {
                    '$addFields': {
                        'is_borrowed': {
                            '$gt': [
                                {'$size': {
                                    '$filter': {
                                        'input': '$all_lendings',
                                        'as': 'l',
                                        'cond': {'$eq': ['$$l.returned_at', None]}
                                    }
                                }},
                                0
                            ]
                        }
                    }
                },
                {
                    '$facet': {
                        'main_stats': [
                            {
                                '$group': {
                                    '_id': None,
                                    'total_tools': {'$sum': 1},
                                    'available_tools': {
                                        '$sum': {
                                            '$cond': [
                                                {'$and': [
                                                    {'$eq': ['$status', 'verfügbar']},
                                                    {'$eq': ['$is_borrowed', False]}
                                                ]},
                                                1, 0
                                            ]
                                        }
                                    },
                                    'borrowed_tools': {
                                        '$sum': {'$cond': ['$is_borrowed', 1, 0]}
                                    },
                                    'defect_tools': {
                                        '$sum': {
                                            '$cond': [{'$eq': ['$status', 'defekt']}, 1, 0]
                                        }
                                    }
                                }
                            }
                        ],
                        'categories': [
                            {'$group': {
                                '_id': {'$ifNull': ['$category', 'Keine Kategorie']},
                                'count': {'$sum': 1}
                            }}
                        ],
                        'locations': [
                            {'$group': {
                                '_id': {'$ifNull': ['$location', 'Kein Standort']},
                                'count': {'$sum': 1}
                            }}
                        ]
                    }
                }
            ]

            results = mongodb.aggregate('tools', pipeline)

            if not results:
                return {
                    'total_tools': 0, 'available_tools': 0, 'borrowed_tools': 0,
                    'defect_tools': 0, 'categories': {}, 'locations': {}
                }

            result = results[0]
            main = result.get('main_stats', [{}])[0] if result.get('main_stats') else {}
            
            stats = {
                'total_tools': main.get('total_tools', 0),
                'available_tools': main.get('available_tools', 0),
                'borrowed_tools': main.get('borrowed_tools', 0),
                'defect_tools': main.get('defect_tools', 0),
                'categories': {item['_id']: item['count'] for item in result.get('categories', []) if item['_id'] is not None},
                'locations': {item['_id']: item['count'] for item in result.get('locations', []) if item['_id'] is not None}
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Werkzeug-Statistiken: [Interner Fehler]")
            return {
                'total_tools': 0,
                'available_tools': 0,
                'borrowed_tools': 0,
                'defect_tools': 0,
                'categories': {},
                'locations': {}
            }
    
    def export_tools(self) -> str:
        """
        Exportiert alle Werkzeuge als CSV
        
        Returns:
            str: CSV-Daten
        """
        try:
            import csv
            from io import StringIO
            
            tools = self.get_all_tools()
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'Barcode', 'Name', 'Beschreibung', 'Kategorie', 'Standort', 
                'Status', 'Ausgeliehen', 'Erstellt am', 'Geändert am'
            ])
            
            # Daten
            for tool in tools:
                writer.writerow([
                    tool.get('barcode', ''),
                    tool.get('name', ''),
                    tool.get('description', ''),
                    tool.get('category', ''),
                    tool.get('location', ''),
                    tool.get('status', ''),
                    'Ja' if tool.get('is_borrowed', False) else 'Nein',
                    tool.get('created_at', ''),
                    tool.get('modified_at', '')
                ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Fehler beim Export der Werkzeuge: [Interner Fehler]")
            return ""
    
    def _convert_datetime_fields(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Konvertiert datetime-Strings zu datetime-Objekten
        
        Args:
            tool: Werkzeug-Daten
            
        Returns:
            Dict: Werkzeug mit konvertierten Datetime-Feldern
        """
        date_fields = ['created_at', 'modified_at', 'deleted_at']
        for field in date_fields:
            if tool.get(field):
                if isinstance(tool[field], str):
                    try:
                        # Versuche verschiedene Datumsformate zu parsen
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                            try:
                                tool[field] = datetime.strptime(tool[field], fmt)
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Fehler bei Datumskonvertierung für Feld {field}: [Interner Fehler]")
                        # Wenn alle Formate fehlschlagen, setze auf None
                        tool[field] = None
                elif isinstance(tool[field], datetime):
                    # Bereits ein datetime-Objekt, nichts zu tun
                    pass
                else:
                    # Versuche es als datetime zu konvertieren
                    try:
                        tool[field] = datetime.fromisoformat(str(tool[field]))
                    except Exception as e:
                        logger.warning(f"Fehler bei ISO-Datumskonvertierung für Feld {field}: [Interner Fehler]")
                        # Wenn Konvertierung fehlschlägt, setze auf None
                        tool[field] = None
            else:
                # Feld ist None oder nicht vorhanden, setze auf None
                tool[field] = None
        return tool
    
    def _merge_software_from_user_groups(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Führt Software aus Nutzergruppen mit der bereits vorhandenen Software zusammen
        
        Args:
            tool: Tool-Dictionary
            
        Returns:
            Dict: Tool mit zusammengeführter Software
        """
        try:
            # Bestehende additional_software holen
            current_software = set(tool.get('additional_software', []))
            
            # User Groups des Tools holen
            user_groups = tool.get('user_groups', [])
            if not user_groups:
                return tool
            
            # Software aus jeder Nutzergruppe sammeln
            for group_id in user_groups:
                try:
                    # Nutzergruppe aus Datenbank laden - ObjectId konvertieren falls nötig
                    from bson import ObjectId
                    query_id = group_id
                    if isinstance(group_id, str):
                        try:
                            query_id = ObjectId(group_id)
                        except Exception:
                            # Falls String keine gültige ObjectId ist, als String verwenden
                            query_id = group_id
                    
                    group = mongodb.find_one('user_groups', {'_id': query_id})
                    if group and group.get('software'):
                        # Software der Gruppe hinzufügen
                        for software_id in group['software']:
                            current_software.add(software_id)
                except Exception as e:
                    logger.warning(f"Fehler beim Laden der Nutzergruppe {group_id}: [Interner Fehler]")
            
            # Zurück zur Liste konvertieren und Tool aktualisieren
            tool['additional_software'] = list(current_software)
            
            return tool
            
        except Exception as e:
            logger.error(f"Fehler beim Zusammenführen der Software aus Nutzergruppen: [Interner Fehler]")
            return tool
