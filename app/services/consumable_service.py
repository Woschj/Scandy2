"""
Zentraler Consumable Service für Scandy
Alle Verbrauchsmaterial-Funktionen an einem Ort
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from app.models.mongodb_database import mongodb
from flask import g
import logging

logger = logging.getLogger(__name__)

class ConsumableService:
    """Zentraler Service für alle Verbrauchsmaterial-Operationen"""
    
    @staticmethod
    def get_all_consumables() -> List[Dict[str, Any]]:
        try:
            query = {'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                query['department'] = g.current_department
            return list(mongodb.find('consumables', query))
        except Exception:
            logger.error("Fehler beim Laden der Verbrauchsmaterialien: [Interner Fehler]")
            return []
    
    @staticmethod
    def add_consumable(data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            barcode = data.get('barcode')
            dept = getattr(g, 'current_department', None)
            if not dept:
                return False, 'Bitte Abteilung wählen, bevor Sie ein Verbrauchsmaterial anlegen'
            # Prüfe auf Barcode-Duplikate innerhalb der aktuellen Abteilung
            for collection in ['tools', 'consumables', 'workers']:
                uniq_query = {'barcode': barcode, 'deleted': {'$ne': True}}
                if dept:
                    uniq_query['department'] = dept
                if mongodb.find_one(collection, uniq_query):
                    return False, 'Barcode bereits vergeben'
            
            consumable_data = {
                'name': data.get('name'),
                'barcode': barcode,
                'category': data.get('category'),
                'location': data.get('location'),
                'quantity': int(data.get('quantity', 0)),
                'min_quantity': int(data.get('min_quantity', 0)),
                'description': data.get('description', ''),
                'department': dept,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'deleted': False
            }
            
            # Benutzerdefinierte Felder hinzufügen, falls vorhanden
            if 'custom_fields' in data:
                consumable_data['custom_fields'] = data['custom_fields']
            mongodb.insert_one('consumables', consumable_data)
            return True, 'Verbrauchsmaterial wurde erfolgreich hinzugefügt'
        except Exception:
            logger.error("Fehler beim Hinzufügen des Verbrauchsmaterials: [Interner Fehler]")
            return False, 'Fehler beim Hinzufügen des Verbrauchsmaterials'
    
    @staticmethod
    def update_consumable(barcode: str, data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        try:
            new_barcode = data.get('barcode')
            filter_query = {'barcode': barcode, 'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                filter_query['department'] = g.current_department
            current = mongodb.find_one('consumables', filter_query)
            if not current:
                return False, 'Verbrauchsmaterial nicht gefunden', None
            if new_barcode != barcode:
                for collection in ['tools', 'consumables', 'workers']:
                    uniq_query = {'barcode': new_barcode, 'deleted': {'$ne': True}}
                    if getattr(g, 'current_department', None):
                        uniq_query['department'] = g.current_department
                    if mongodb.find_one(collection, uniq_query):
                        return False, f'Der Barcode "{new_barcode}" existiert bereits', None
            update_data = {
                'name': data.get('name'),
                'description': data.get('description'),
                'category': data.get('category'),
                'location': data.get('location'),
                'quantity': int(data.get('quantity', current['quantity'])),
                'min_quantity': int(data.get('min_quantity', current['min_quantity'])),
                'barcode': new_barcode,
                'updated_at': datetime.now()
            }
            
            # Benutzerdefinierte Felder hinzufügen, falls vorhanden
            if 'custom_fields' in data:
                update_data['custom_fields'] = data['custom_fields']
            update_filter = {'barcode': barcode}
            if getattr(g, 'current_department', None):
                update_filter['department'] = g.current_department
            mongodb.update_one('consumables', update_filter, {'$set': update_data})
            # Bestandsänderung protokollieren
            if int(data.get('quantity', current['quantity'])) != current['quantity']:
                usage_data = {
                    'consumable_barcode': new_barcode,
                    'worker_barcode': 'admin',
                    'quantity': int(data.get('quantity', current['quantity'])) - current['quantity'],
                    'used_at': datetime.now()
                }
                mongodb.insert_one('consumable_usages', usage_data)
            return True, 'Verbrauchsmaterial erfolgreich aktualisiert', new_barcode
        except Exception:
            logger.error("Fehler beim Aktualisieren des Verbrauchsmaterials: [Interner Fehler]")
            return False, 'Ein interner Fehler ist aufgetreten.', None
    
    @staticmethod
    def get_consumable_detail(barcode: str) -> Optional[Dict[str, Any]]:
        try:
            filter_query = {'barcode': barcode, 'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                filter_query['department'] = g.current_department
            return mongodb.find_one('consumables', filter_query)
        except Exception:
            logger.error("Fehler beim Laden des Verbrauchsmaterials: [Interner Fehler]")
            return None
    
    @staticmethod
    def get_consumable_usages(barcode: str) -> List[Dict[str, Any]]:
        """Holt die rohen Verbrauchsdaten für ein Verbrauchsmaterial"""
        try:
            return list(mongodb.find('consumable_usages', {'consumable_barcode': barcode}, sort=[('used_at', -1)]))
        except Exception:
            logger.error("Fehler beim Laden der Verbrauchsdaten: [Interner Fehler]")
            return []

    @staticmethod
    def get_usage_history(barcode: str) -> List[Dict[str, Any]]:
        """
        Holt die angereicherte Nutzungshistorie für ein Verbrauchsmaterial (optimiert via Aggregation) (Bolt ⚡)
        Reduziert Datenbank-Abfragen von O(N) auf O(1).
        """
        try:
            pipeline = [
                {'$match': {'consumable_barcode': barcode}},
                {'$sort': {'used_at': -1}},
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

            usages = mongodb.aggregate('consumable_usages', pipeline)

            # Enriched Result-Set erstellen
            history = []
            for usage in usages:
                worker = usage.get('worker_info', {})
                worker_name = f"{worker.get('firstname', '')} {worker.get('lastname', '')}".strip() or "Admin"

                # Datums-Konvertierung zur Sicherheit (für Kompatibilität mit dem Template)
                action_date = usage.get('used_at')
                if isinstance(action_date, str):
                    try:
                        action_date = datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        action_date = datetime.now()
                elif not isinstance(action_date, datetime):
                    action_date = datetime.now()

                history.append({
                    'action': "Entnommen" if usage.get('quantity', 0) < 0 else "Hinzugefügt",
                    'quantity': abs(usage.get('quantity', 0)),
                    'worker_name': worker_name,
                    'worker_barcode': usage.get('worker_barcode'),
                    'date': action_date
                })

            return history

        except Exception as e:
            logger.error(f"Fehler beim Laden der Nutzungshistorie: {e}")
            return []
    
    @staticmethod
    def delete_consumable(barcode: str) -> Tuple[bool, str]:
        try:
            result = mongodb.update_one('consumables', {'barcode': barcode}, {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
            if result:
                return True, 'Verbrauchsmaterial erfolgreich gelöscht'
            else:
                return False, 'Fehler beim Löschen'
        except Exception:
            logger.error("Fehler beim Löschen des Verbrauchsmaterials: [Interner Fehler]")
            return False, 'Fehler beim Löschen'
    
    @staticmethod
    def adjust_stock(barcode: str, quantity_change: int, reason: str) -> Tuple[bool, str]:
        """Passt den Bestand eines Verbrauchsmaterials an"""
        try:
            # Verbrauchsmaterial finden
            filter_query = {'barcode': barcode, 'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                filter_query['department'] = g.current_department
            consumable = mongodb.find_one('consumables', filter_query)
            if not consumable:
                return False, 'Verbrauchsmaterial nicht gefunden'
            
            # Neuen Bestand berechnen
            current_quantity = consumable.get('quantity', 0)
            new_quantity = current_quantity + quantity_change
            
            # Negativen Bestand verhindern
            if new_quantity < 0:
                return False, f'Bestand kann nicht unter 0 fallen. Aktueller Bestand: {current_quantity}'
            
            # Bestand aktualisieren
            update_filter = {'barcode': barcode}
            if getattr(g, 'current_department', None):
                update_filter['department'] = g.current_department
            mongodb.update_one('consumables', 
                             update_filter, 
                             {'$set': {'quantity': new_quantity, 'updated_at': datetime.now()}})
            
            # Verwendung protokollieren
            usage_data = {
                'consumable_barcode': barcode,
                'worker_barcode': getattr(g, 'current_user', {}).get('username', 'admin'),  # Aktuellen Benutzer verwenden
                'quantity': quantity_change,  # Positiv für Hinzufügung, negativ für Entnahme
                'reason': reason,
                'used_at': datetime.now()
            }
            mongodb.insert_one('consumable_usages', usage_data)
            
            action = "hinzugefügt" if quantity_change > 0 else "entnommen"
            return True, f'{abs(quantity_change)} Stück {action}. Neuer Bestand: {new_quantity}'
            
        except Exception:
            logger.error("Fehler beim Anpassen des Bestands: [Interner Fehler]")
            return False, 'Fehler beim Anpassen des Bestands: [Interner Fehler]'
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """
        Holt Statistiken für Verbrauchsmaterialien (optimiert via Aggregation Bolt ⚡)
        Reduziert Datenbank-Abfragen von O(N) auf O(1) und eliminiert Python-Loops.
        """
        try:
            # Basis-Filter für Verbrauchsmaterialien (Bolt ⚡)
            match_query = {'deleted': {'$ne': True}}
            if getattr(g, 'current_department', None):
                match_query['department'] = g.current_department

            # Aggregation-Pipeline zur Performance-Optimierung
            pipeline = [
                {'$match': match_query},
                {
                    '$facet': {
                        'base_counts': [
                            {
                                '$group': {
                                    '_id': None,
                                    'total': {'$sum': 1},
                                    'sufficient': {
                                        '$sum': {'$cond': [{'$gte': ['$quantity', '$min_quantity']}, 1, 0]}
                                    },
                                    'warning': {
                                        '$sum': {
                                            '$cond': [
                                                {'$and': [
                                                    {'$lt': ['$quantity', '$min_quantity']},
                                                    {'$gt': ['$quantity', 0]}
                                                ]},
                                                1, 0
                                            ]
                                        }
                                    },
                                    'critical': {
                                        '$sum': {'$cond': [{'$lte': ['$quantity', 0]}, 1, 0]}
                                    }
                                }
                            }
                        ],
                        'categories': [
                            {'$group': {'_id': {'$ifNull': ['$category', 'Keine Kategorie']}, 'count': {'$sum': 1}}}
                        ],
                        'locations': [
                            {'$group': {'_id': {'$ifNull': ['$location', 'Kein Standort']}, 'count': {'$sum': 1}}}
                        ]
                    }
                }
            ]
            
            result = mongodb.aggregate('consumables', pipeline)

            if not result or not result[0]['base_counts']:
                return {
                    'total_consumables': 0,
                    'categories': {},
                    'locations': {},
                    'stock_levels': {'sufficient': 0, 'warning': 0, 'critical': 0}
                }
            
            data = result[0]
            base = data['base_counts'][0]
            
            return {
                'total_consumables': base.get('total', 0),
                'categories': {c['_id']: c['count'] for c in data['categories'] if c['_id']},
                'locations': {loc['_id']: loc['count'] for loc in data['locations'] if loc['_id']},
                'stock_levels': {
                    'sufficient': base.get('sufficient', 0),
                    'warning': base.get('warning', 0),
                    'critical': base.get('critical', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Verbrauchsmaterial-Statistiken: {e}")
            return {
                'total_consumables': 0,
                'categories': {},
                'locations': {},
                'stock_levels': {'sufficient': 0, 'warning': 0, 'critical': 0}
            } 