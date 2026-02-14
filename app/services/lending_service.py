"""
Zentraler Lending Service für Scandy
Alle Ausleihe/Rückgabe-Logik an einem Ort
"""
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from app.models.mongodb_database import mongodb
import logging

logger = logging.getLogger(__name__)

class LendingService:
    """Zentraler Service für alle Ausleihe/Rückgabe-Operationen"""
    
    @staticmethod
    def process_lending_request(data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Verarbeitet eine Ausleihe/Rückgabe-Anfrage
        
        Args:
            data: Request-Daten mit item_barcode, worker_barcode, action, item_type, quantity
            
        Returns:
            (success, message, result_data)
        """
        try:
            item_barcode = data.get('item_barcode', '').strip()
            worker_barcode = data.get('worker_barcode', '').strip()
            action = data.get('action', '').strip()
            item_type = data.get('item_type', '').strip()
            quantity = data.get('quantity', 1)
            
            # Erweiterte Validierung
            if not item_barcode:
                return False, 'Item-Barcode ist erforderlich', {}
            if not worker_barcode:
                return False, 'Worker-Barcode ist erforderlich', {}
            if not action:
                return False, 'Aktion ist erforderlich', {}
            if not item_type:
                return False, 'Item-Typ ist erforderlich', {}
            
            # Validiere Aktionen
            valid_actions = ['lend', 'return', 'consume']
            if action not in valid_actions:
                return False, f'Ungültige Aktion. Erlaubt: {", ".join(valid_actions)}', {}
            
            # Validiere Item-Typen
            valid_types = ['tool', 'consumable']
            if item_type not in valid_types:
                return False, f'Ungültiger Item-Typ. Erlaubt: {", ".join(valid_types)}', {}
            
            # Prüfe ob Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': worker_barcode, 'deleted': {'$ne': True}})
            if not worker:
                return False, 'Mitarbeiter nicht gefunden', {}
            
            # Verarbeite basierend auf Item-Typ
            if item_type == 'tool':
                return LendingService._process_tool_lending(item_barcode, worker_barcode, action, worker)
            elif item_type == 'consumable':
                return LendingService._process_consumable_lending(item_barcode, worker_barcode, action, quantity, worker)
            else:
                return False, 'Ungültiger Item-Typ', {}
                
        except Exception as e:
            logger.error(f"Fehler bei der Ausleihe-Verarbeitung: [Interner Fehler]")
            return False, f'Fehler bei der Verarbeitung: [Interner Fehler]', {}
    
    @staticmethod
    def _process_tool_lending(item_barcode: str, worker_barcode: str, action: str, worker: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Verarbeitet Werkzeug-Ausleihe/Rückgabe mit verbesserter Konsistenz"""
        try:
            # Prüfe ob Werkzeug existiert
            tool = mongodb.find_one('tools', {'barcode': item_barcode, 'deleted': {'$ne': True}})
            if not tool:
                return False, 'Werkzeug nicht gefunden', {}
            
            if action == 'lend':
                return LendingService._lend_tool(item_barcode, worker_barcode, tool, worker)
            elif action == 'return':
                return LendingService._return_tool(item_barcode, worker_barcode, tool, worker)
            else:
                return False, 'Ungültige Aktion für Werkzeug', {}
                
        except Exception as e:
            logger.error(f"Fehler bei Werkzeug-Ausleihe: [Interner Fehler]")
            return False, f'Fehler bei der Werkzeug-Verarbeitung: [Interner Fehler]', {}
    
    @staticmethod
    def _lend_tool(item_barcode: str, worker_barcode: str, tool: Dict[str, Any], worker: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Verarbeitet Werkzeug-Ausleihe mit Konsistenzprüfung"""
        try:
            # Prüfe ob bereits ausgeliehen
            active_lending = mongodb.find_one('lendings', {
                'tool_barcode': item_barcode,
                'returned_at': None
            })
            
            if active_lending:
                current_worker = mongodb.find_one('workers', {'barcode': active_lending['worker_barcode']})
                worker_name = f"{current_worker['firstname']} {current_worker['lastname']}" if current_worker else "Unbekannt"
                return False, f'Dieses Werkzeug ist bereits an {worker_name} ausgeliehen', {}
            
            # Prüfe Werkzeug-Status
            if tool.get('status') == 'defekt':
                return False, 'Dieses Werkzeug ist als defekt markiert', {}
            
            # Erstelle neue Ausleihe
            lending_data = {
                'tool_barcode': item_barcode,
                'worker_barcode': worker_barcode,
                'lent_at': datetime.now(),
                'created_at': datetime.now(),
                'sync_status': 'pending'
            }
            
            lending_result = mongodb.insert_one('lendings', lending_data)
            if not lending_result:
                return False, 'Fehler beim Erstellen der Ausleihe', {}
            
            # Aktualisiere Werkzeug-Status
            tool_update_result = mongodb.update_one('tools', 
                                                 {'barcode': item_barcode}, 
                                                 {
                                                     '$set': {
                                                         'status': 'ausgeliehen', 
                                                         'modified_at': datetime.now(),
                                                         'sync_status': 'pending'
                                                     }
                                                 })
            
            if not tool_update_result:
                # Rollback: Lösche die Ausleihe wenn Werkzeug-Update fehlschlägt
                mongodb.delete_one('lendings', {'_id': lending_result})
                return False, 'Fehler beim Aktualisieren des Werkzeug-Status', {}
            
            logger.info(f"Werkzeug {tool['name']} erfolgreich an {worker['firstname']} {worker['lastname']} ausgeliehen")
            
            return True, f'Werkzeug {tool["name"]} wurde an {worker["firstname"]} {worker["lastname"]} ausgeliehen', {
                'tool_name': tool['name'],
                'worker_name': f"{worker['firstname']} {worker['lastname']}",
                'lending_id': str(lending_result)
            }
            
        except Exception as e:
            logger.error(f"Fehler bei Werkzeug-Ausleihe: [Interner Fehler]")
            return False, f'Fehler bei der Ausleihe: [Interner Fehler]', {}
    
    @staticmethod
    def _return_tool(item_barcode: str, worker_barcode: str, tool: Dict[str, Any], worker: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Verarbeitet Werkzeug-Rückgabe mit Konsistenzprüfung"""
        try:
            logger.info(f"_return_tool aufgerufen: item_barcode={item_barcode}, worker_barcode={worker_barcode}")
            
            # Finde aktive Ausleihe
            active_lending = mongodb.find_one('lendings', {
                'tool_barcode': item_barcode,
                'returned_at': None
            })
            
            logger.info(f"Aktive Ausleihe gefunden: {active_lending}")
            
            if not active_lending:
                logger.warning(f"Keine aktive Ausleihe für Werkzeug {item_barcode}")
                return False, 'Dieses Werkzeug ist nicht ausgeliehen', {}
            
            # Prüfe Berechtigung (optional)
            if worker_barcode and active_lending['worker_barcode'] != worker_barcode:
                current_worker = mongodb.find_one('workers', {'barcode': active_lending['worker_barcode']})
                worker_name = f"{current_worker['firstname']} {current_worker['lastname']}" if current_worker else "Unbekannt"
                logger.warning(f"Berechtigungsfehler: Werkzeug wurde von {worker_name} ausgeliehen")
                return False, f'Dieses Werkzeug wurde von {worker_name} ausgeliehen', {}
            
            # Markiere Ausleihe als zurückgegeben
            try:
                logger.info(f"Versuche Ausleihe zu markieren: {active_lending['_id']}")
                
                # Konvertiere String-ID zu ObjectId falls nötig
                from bson import ObjectId
                lending_id = active_lending['_id']
                if isinstance(lending_id, str):
                    try:
                        lending_id = ObjectId(lending_id)
                        logger.info(f"String-ID zu ObjectId konvertiert: {lending_id}")
                    except Exception as e:
                        logger.error(f"Fehler beim Konvertieren der ID: [Interner Fehler]")
                        return False, f'Fehler beim Konvertieren der ID: [Interner Fehler]', {}
                
                lending_update_result = mongodb.update_one('lendings', 
                                                        {'_id': lending_id}, 
                                                        {
                                                            '$set': {
                                                                'returned_at': datetime.now(),
                                                                'updated_at': datetime.now(),
                                                                'sync_status': 'pending'
                                                            }
                                                        })
                
                logger.info(f"Lending Update Result: {lending_update_result}")
                
                if not lending_update_result:
                    logger.error(f"Fehler beim Markieren der Rückgabe für Ausleihe {active_lending['_id']}")
                    return False, 'Fehler beim Markieren der Rückgabe', {}
                else:
                    logger.info(f"Ausleihe erfolgreich markiert als zurückgegeben")
            except Exception as e:
                logger.error(f"Exception beim Markieren der Rückgabe: [Interner Fehler]")
                return False, f'Fehler beim Markieren der Rückgabe: [Interner Fehler]', {}
            
            # Aktualisiere Werkzeug-Status
            try:
                logger.info(f"Versuche Werkzeug-Status zu aktualisieren: {item_barcode}")
                tool_update_result = mongodb.update_one('tools', 
                                                     {'barcode': item_barcode}, 
                                                     {
                                                         '$set': {
                                                             'status': 'verfügbar', 
                                                             'modified_at': datetime.now(),
                                                             'sync_status': 'pending'
                                                         }
                                                     })
                
                logger.info(f"Tool Update Result: {tool_update_result}")
                
                if not tool_update_result:
                    # Rollback: Setze Ausleihe zurück wenn Werkzeug-Update fehlschlägt
                    logger.warning(f"Tool Update fehlgeschlagen, führe Rollback durch")
                    try:
                        mongodb.update_one('lendings', 
                                         {'_id': active_lending['_id']}, 
                                         {
                                             '$unset': {
                                                 'returned_at': '',
                                                 'updated_at': '',
                                                 'sync_status': ''
                                             }
                                         })
                    except Exception as rollback_error:
                        logger.error(f"Rollback fehlgeschlagen: {str(rollback_error)}")
                    
                    return False, 'Fehler beim Aktualisieren des Werkzeug-Status', {}
                else:
                    logger.info(f"Werkzeug-Status erfolgreich aktualisiert")
            except Exception as e:
                logger.error(f"Exception beim Aktualisieren des Werkzeug-Status: [Interner Fehler]")
                # Rollback versuchen
                try:
                    mongodb.update_one('lendings', 
                                     {'_id': active_lending['_id']}, 
                                     {
                                         '$unset': {
                                             'returned_at': '',
                                             'updated_at': '',
                                             'sync_status': ''
                                         }
                                     })
                except Exception as rollback_error:
                    logger.error(f"Rollback fehlgeschlagen: {str(rollback_error)}")
                
                return False, f'Fehler beim Aktualisieren des Werkzeug-Status: [Interner Fehler]', {}
            
            logger.info(f"Werkzeug {tool['name']} erfolgreich zurückgegeben")
            
            return True, f'Werkzeug {tool["name"]} wurde erfolgreich zurückgegeben', {
                'tool_name': tool['name'],
                'returned_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Fehler bei Werkzeug-Rückgabe: [Interner Fehler]", exc_info=True)
            return False, f'Fehler bei der Rückgabe: [Interner Fehler]', {}
    
    @staticmethod
    def _process_consumable_lending(item_barcode: str, worker_barcode: str, action: str, quantity: int, worker: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Verarbeitet Verbrauchsmaterial-Entnahme mit verbesserter Konsistenz"""
        try:
            if action != 'consume':
                return False, 'Ungültige Aktion für Verbrauchsmaterial', {}
            
            # Validiere Menge
            if not isinstance(quantity, (int, float)) or quantity <= 0:
                return False, 'Ungültige Menge', {}
            
            # Prüfe ob Verbrauchsmaterial existiert
            consumable = mongodb.find_one('consumables', {'barcode': item_barcode, 'deleted': {'$ne': True}})
            if not consumable:
                return False, 'Verbrauchsmaterial nicht gefunden', {}
            
            # Prüfe verfügbare Menge
            current_quantity = consumable.get('quantity', 0)
            if current_quantity < quantity:
                return False, f'Nicht genügend {consumable.get("name", "")} verfügbar (verfügbar: {current_quantity}, benötigt: {quantity})', {}
            
            # Erstelle Verbrauchseintrag mit negativer Menge für Ausgaben
            usage_data = {
                'consumable_barcode': item_barcode,
                'worker_barcode': worker_barcode,
                'quantity': -quantity,  # Negative Menge für Ausgaben
                'used_at': datetime.now(),
                'created_at': datetime.now(),
                'consumable_name': consumable.get('name', ''),
                'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip(),
                'direction': 'out',
                'sync_status': 'pending'
            }
            
            usage_result = mongodb.insert_one('consumable_usages', usage_data)
            if not usage_result:
                return False, 'Fehler beim Erstellen des Verbrauchseintrags', {}
            
            # Reduziere verfügbare Menge
            new_quantity = current_quantity - quantity
            consumable_update_result = mongodb.update_one('consumables', 
                                                        {'barcode': item_barcode}, 
                                                        {
                                                            '$set': {
                                                                'quantity': new_quantity,
                                                                'updated_at': datetime.now(),
                                                                'sync_status': 'pending'
                                                            }
                                                        })
            
            if not consumable_update_result:
                # Rollback: Lösche Verbrauchseintrag wenn Update fehlschlägt
                mongodb.delete_one('consumable_usages', {'_id': usage_result})
                return False, 'Fehler beim Aktualisieren des Bestands', {}
            
            logger.info(f"{quantity}x {consumable.get('name', '')} erfolgreich an {worker.get('firstname', '')} {worker.get('lastname', '')} ausgegeben")
            
            return True, f'{quantity}x {consumable.get("name", "")} erfolgreich an {worker.get("firstname", "")} {worker.get("lastname", "")} ausgegeben', {
                'consumable_name': consumable.get('name', ''),
                'quantity': quantity,
                'worker_name': f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip(),
                'usage_id': str(usage_result)
            }
            
        except Exception as e:
            logger.error(f"Fehler bei Verbrauchsmaterial-Entnahme: [Interner Fehler]")
            return False, f'Fehler bei der Verbrauchsmaterial-Verarbeitung: [Interner Fehler]', {}
    
    @staticmethod
    def get_active_lendings() -> list:
        """Holt alle aktiven Ausleihen"""
        try:
            active_lendings = mongodb.find('lendings', {'returned_at': None})
            
            # Erweitere mit Tool- und Worker-Informationen
            enriched_lendings = []
            for lending in active_lendings:
                tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
                worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
                
                if tool and worker:
                    enriched_lendings.append({
                        **lending,
                        'tool_name': tool['name'],
                        'worker_name': f"{worker['firstname']} {worker['lastname']}",
                        'lent_at': lending['lent_at']
                    })
            
            # Sortiere nach Datum (neueste zuerst)
            enriched_lendings.sort(key=lambda x: x.get('lent_at', datetime.min), reverse=True)
            return enriched_lendings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aktiver Ausleihen: [Interner Fehler]")
            return []
    
    @staticmethod
    def get_recent_consumable_usage(limit: int = 10) -> list:
        """Holt die letzten Verbrauchsmaterial-Entnahmen"""
        try:
            recent_usages = mongodb.find('consumable_usages')
            # Sortiere und limitiere
            recent_usages.sort(key=lambda x: x.get('used_at', datetime.min), reverse=True)
            recent_usages = recent_usages[:limit]
            
            # Erweitere mit Consumable- und Worker-Informationen
            enriched_usages = []
            for usage in recent_usages:
                consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
                worker = mongodb.find_one('workers', {'barcode': usage['worker_barcode']})
                
                if consumable and worker:
                    enriched_usages.append({
                        'consumable_name': consumable['name'],
                        'quantity': usage['quantity'],
                        'worker_name': f"{worker['firstname']} {worker['lastname']}",
                        'used_at': usage['used_at']
                    })
            
            return enriched_usages
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Entnahmen: [Interner Fehler]")
            return []
    
    @staticmethod
    def get_worker_consumable_history(worker_barcode: str) -> List[Dict[str, Any]]:
        """
        Holt die Verbrauchsmaterial-Historie für einen Mitarbeiter
        
        Args:
            worker_barcode: Barcode des Mitarbeiters
            
        Returns:
            List[Dict]: Liste der Verbrauchsmaterial-Ausgaben
        """
        try:
            # Hole alle Verbrauchsmaterial-Ausgaben des Mitarbeiters
            usages = mongodb.find('consumable_usages', {'worker_barcode': worker_barcode})
            
            # Erweitere mit Consumable-Informationen
            enriched_usages = []
            for usage in usages:
                consumable = mongodb.find_one('consumables', {'barcode': usage['consumable_barcode']})
                if consumable:
                    usage['consumable_name'] = consumable.get('name', '')
                    usage['consumable_barcode'] = usage['consumable_barcode']
                    enriched_usages.append(usage)
            
            # Sortiere nach Datum (neueste zuerst)
            def safe_date_key(usage):
                used_at = usage.get('used_at')
                if isinstance(used_at, str):
                    try:
                        return datetime.strptime(used_at, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        return datetime.min
                elif isinstance(used_at, datetime):
                    return used_at
                else:
                    return datetime.min
            
            enriched_usages.sort(key=safe_date_key, reverse=True)
            return enriched_usages
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Historie: [Interner Fehler]")
            return []
    
    @staticmethod
    def get_current_lending(tool_barcode: str) -> Optional[Dict[str, Any]]:
        """
        Holt die aktuelle Ausleihe für ein Werkzeug
        
        Args:
            tool_barcode: Barcode des Werkzeugs
            
        Returns:
            Optional[Dict]: Aktuelle Ausleihe oder None
        """
        try:
            current_lending = mongodb.find_one('lendings', {
                'tool_barcode': tool_barcode,
                'returned_at': None
            })
            
            if current_lending:
                # Worker-Informationen hinzufügen
                worker = mongodb.find_one('workers', {'barcode': current_lending['worker_barcode']})
                if worker:
                    current_lending['worker_name'] = f"{worker['firstname']} {worker['lastname']}"
                
                # Tool-Informationen hinzufügen
                tool = mongodb.find_one('tools', {'barcode': tool_barcode})
                if tool:
                    current_lending['tool_name'] = tool['name']
            
            return current_lending
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der aktuellen Ausleihe: [Interner Fehler]")
            return None
    
    @staticmethod
    def get_tool_lending_history(tool_barcode: str) -> List[Dict[str, Any]]:
        """
        Holt die Ausleihhistorie für ein Werkzeug
        
        Args:
            tool_barcode: Barcode des Werkzeugs
            
        Returns:
            List[Dict]: Liste der Ausleihen
        """
        try:
            lendings = mongodb.find('lendings', {'tool_barcode': tool_barcode})
            
            # Erweitere mit Worker-Informationen
            enriched_lendings = []
            for lending in lendings:
                worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode']})
                if worker:
                    lending['worker_name'] = f"{worker['firstname']} {worker['lastname']}"
                
                enriched_lendings.append(lending)
            
            # Sortiere nach Datum (neueste zuerst)
            def safe_date_key(lending):
                lent_at = lending.get('lent_at')
                if isinstance(lent_at, str):
                    try:
                        return datetime.strptime(lent_at, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        return datetime.min
                elif isinstance(lent_at, datetime):
                    return lent_at
                else:
                    return datetime.min
            
            enriched_lendings.sort(key=safe_date_key, reverse=True)
            return enriched_lendings
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ausleihhistorie: [Interner Fehler]")
            return []
    
    @staticmethod
    def validate_lending_consistency() -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validiert die Konsistenz der Ausleihdaten
        
        Returns:
            (is_consistent, message, issues)
        """
        try:
            issues = []
            
            # 1. Prüfe Werkzeuge mit falschem Status
            tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
            for tool in tools:
                barcode = tool.get('barcode')
                status = tool.get('status')
                
                # Prüfe aktive Ausleihe
                active_lending = mongodb.find_one('lendings', {
                    'tool_barcode': barcode,
                    'returned_at': None
                })
                
                if active_lending and status != 'ausgeliehen':
                    issues.append({
                        'type': 'tool_status_mismatch',
                        'tool_barcode': barcode,
                        'tool_name': tool.get('name', ''),
                        'current_status': status,
                        'expected_status': 'ausgeliehen',
                        'message': f'Werkzeug {tool.get("name", "")} ist ausgeliehen aber Status ist "{status}"'
                    })
                elif not active_lending and status == 'ausgeliehen':
                    issues.append({
                        'type': 'tool_status_mismatch',
                        'tool_barcode': barcode,
                        'tool_name': tool.get('name', ''),
                        'current_status': status,
                        'expected_status': 'verfügbar',
                        'message': f'Werkzeug {tool.get("name", "")} ist nicht ausgeliehen aber Status ist "ausgeliehen"'
                    })
            
            # 2. Prüfe verwaiste Ausleihen
            orphaned_lendings = list(mongodb.find('lendings', {
                'returned_at': None,
                'tool_barcode': {'$exists': True}
            }))
            
            for lending in orphaned_lendings:
                tool_barcode = lending.get('tool_barcode')
                tool = mongodb.find_one('tools', {'barcode': tool_barcode, 'deleted': {'$ne': True}})
                
                if not tool:
                    issues.append({
                        'type': 'orphaned_lending',
                        'lending_id': str(lending.get('_id')),
                        'tool_barcode': tool_barcode,
                        'message': f'Verwaiste Ausleihe für nicht existierendes Werkzeug {tool_barcode}'
                    })
            
            # 3. Prüfe doppelte aktive Ausleihen
            tool_barcodes = [lending['tool_barcode'] for lending in orphaned_lendings]
            for barcode in set(tool_barcodes):
                count = tool_barcodes.count(barcode)
                if count > 1:
                    issues.append({
                        'type': 'duplicate_active_lending',
                        'tool_barcode': barcode,
                        'count': count,
                        'message': f'Mehrere aktive Ausleihen für Werkzeug {barcode} gefunden'
                    })
            
            is_consistent = len(issues) == 0
            message = f'Konsistenzprüfung abgeschlossen: {len(issues)} Probleme gefunden' if issues else 'Alle Daten sind konsistent'
            
            return is_consistent, message, {
                'total_issues': len(issues),
                'issues': issues
            }
            
        except Exception as e:
            logger.error(f"Fehler bei der Konsistenzprüfung: [Interner Fehler]")
            return False, f'Fehler bei der Konsistenzprüfung: [Interner Fehler]', {}
    
    @staticmethod
    def fix_lending_inconsistencies() -> Tuple[bool, str, Dict[str, Any]]:
        """
        Behebt Inkonsistenzen in den Ausleihdaten
        
        Returns:
            (success, message, statistics)
        """
        try:
            fixed_count = 0
            cleaned_count = 0
            
            # 1. Werkzeuge mit falschem Status korrigieren
            tools = list(mongodb.find('tools', {'deleted': {'$ne': True}}))
            
            for tool in tools:
                barcode = tool.get('barcode')
                status = tool.get('status')
                
                # Prüfe aktive Ausleihe
                active_lending = mongodb.find_one('lendings', {
                    'tool_barcode': barcode,
                    'returned_at': None
                })
                
                if active_lending and status != 'ausgeliehen':
                    # Werkzeug ist ausgeliehen aber Status ist falsch
                    mongodb.update_one('tools', 
                                     {'barcode': barcode}, 
                                     {'$set': {'status': 'ausgeliehen'}})
                    fixed_count += 1
                elif not active_lending and status == 'ausgeliehen':
                    # Werkzeug ist nicht ausgeliehen aber Status ist falsch
                    mongodb.update_one('tools', 
                                     {'barcode': barcode}, 
                                     {'$set': {'status': 'verfügbar'}})
                    fixed_count += 1
            
            # 2. Verwaiste Ausleihen bereinigen
            orphaned_lendings = list(mongodb.find('lendings', {
                'returned_at': None,
                'tool_barcode': {'$exists': True}
            }))
            
            for lending in orphaned_lendings:
                tool_barcode = lending.get('tool_barcode')
                tool = mongodb.find_one('tools', {'barcode': tool_barcode, 'deleted': {'$ne': True}})
                
                if not tool:
                    # Werkzeug existiert nicht mehr, Ausleihe löschen
                    mongodb.delete_one('lendings', {'_id': lending['_id']})
                    cleaned_count += 1
            
            # 3. Doppelte aktive Ausleihen bereinigen (behalte die neueste)
            tool_barcodes = [lending['tool_barcode'] for lending in orphaned_lendings]
            for barcode in set(tool_barcodes):
                count = tool_barcodes.count(barcode)
                if count > 1:
                    # Finde alle aktiven Ausleihen für dieses Werkzeug
                    duplicate_lendings = list(mongodb.find('lendings', {
                        'tool_barcode': barcode,
                        'returned_at': None
                    }))
                    
                    # Sortiere nach Datum (neueste zuerst)
                    duplicate_lendings.sort(key=lambda x: x.get('lent_at', datetime.min), reverse=True)
                    
                    # Behalte nur die neueste, markiere die anderen als zurückgegeben
                    for lending in duplicate_lendings[1:]:
                        mongodb.update_one('lendings', 
                                         {'_id': lending['_id']}, 
                                         {'$set': {'returned_at': datetime.now()}})
                        cleaned_count += 1
            
            return True, f'Inkonsistenzen behoben: {fixed_count} Werkzeug-Status korrigiert, {cleaned_count} Ausleihen bereinigt', {
                'fixed_status_count': fixed_count,
                'cleaned_lendings_count': cleaned_count
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Beheben der Inkonsistenzen: [Interner Fehler]")
            return False, f'Fehler beim Beheben der Inkonsistenzen: [Interner Fehler]', {}
    
    @staticmethod
    def return_tool_centralized(tool_barcode: str, worker_barcode: str = None) -> Tuple[bool, str]:
        """
        Zentrale Rückgabe-Funktion für Werkzeuge
        
        Args:
            tool_barcode: Barcode des Werkzeugs
            worker_barcode: Optional - Barcode des Mitarbeiters
            
        Returns:
            (success, message)
        """
        try:
            logger.info(f"return_tool_centralized aufgerufen: tool_barcode={tool_barcode}, worker_barcode={worker_barcode}")
            
            # Finde aktive Ausleihe
            if worker_barcode:
                # Spezifischer Mitarbeiter
                lending = mongodb.find_one('lendings', {
                    'tool_barcode': tool_barcode,
                    'worker_barcode': worker_barcode,
                    'returned_at': None
                })
                logger.info(f"Suche nach spezifischer Ausleihe: {lending}")
            else:
                # Beliebiger Mitarbeiter
                lending = mongodb.find_one('lendings', {
                    'tool_barcode': tool_barcode,
                    'returned_at': None
                })
                logger.info(f"Suche nach beliebiger Ausleihe: {lending}")
            
            if not lending:
                logger.warning(f"Keine aktive Ausleihe für Werkzeug {tool_barcode} gefunden")
                return False, 'Keine aktive Ausleihe für dieses Werkzeug gefunden'
            
            # Werkzeug-Informationen holen
            tool = mongodb.find_one('tools', {'barcode': tool_barcode, 'deleted': {'$ne': True}})
            if not tool:
                logger.warning(f"Werkzeug {tool_barcode} nicht gefunden")
                return False, 'Werkzeug nicht gefunden'
            
            # Worker-Informationen holen
            worker = mongodb.find_one('workers', {'barcode': lending['worker_barcode'], 'deleted': {'$ne': True}})
            worker_name = f"{worker['firstname']} {worker['lastname']}" if worker else "Unbekannt"
            logger.info(f"Worker gefunden: {worker_name}")
            
            # Verwende die zentrale Rückgabe-Funktion
            success, message, _ = LendingService._return_tool(tool_barcode, lending['worker_barcode'], tool, worker or {})
            
            if success:
                logger.info(f"Rückgabe erfolgreich: {message}")
                return True, f'Werkzeug {tool["name"]} wurde von {worker_name} erfolgreich zurückgegeben'
            else:
                logger.warning(f"Rückgabe fehlgeschlagen: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"Fehler bei der zentralen Rückgabe: [Interner Fehler]", exc_info=True)
            return False, f'Fehler bei der Rückgabe: [Interner Fehler]'