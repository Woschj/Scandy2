from .mongodb_models import BaseModel
from datetime import datetime
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class Tool(BaseModel):
    collection_name = 'tools'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs.get('name', '')
        self.barcode = kwargs.get('barcode', '')
        self.category = kwargs.get('category', '')
        self.location = kwargs.get('location', '')
        self.description = kwargs.get('description', '')
        self.image_path = kwargs.get('image_path', '')
        self.deleted = kwargs.get('deleted', False)
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        
        # Neue optionale Felder
        self.serial_number = kwargs.get('serial_number', '')
        self.invoice_number = kwargs.get('invoice_number', '')
        self.mac_address = kwargs.get('mac_address', '')
        self.mac_address_wlan = kwargs.get('mac_address_wlan', '')
        self.user_groups = kwargs.get('user_groups', [])
        self.additional_software = kwargs.get('additional_software', [])

    @staticmethod
    def get_all_with_status():
        """Holt alle Werkzeuge mit aktuellem Ausleihstatus"""
        from .mongodb_database import get_database
        
        db = get_database()
        tools_collection = db['tools']
        lendings_collection = db['lendings']
        workers_collection = db['workers']
        
        # Alle nicht gelöschten Werkzeuge holen
        tools = list(tools_collection.find({'deleted': False}))
        
        for tool in tools:
            # Aktuelle Ausleihe finden (ohne Rückgabedatum)
            current_lending = lendings_collection.find_one({
                'tool_barcode': tool['barcode'],
                'returned_at': None
            })
            
            if current_lending:
                # Worker-Informationen holen
                worker = workers_collection.find_one({'barcode': current_lending['worker_barcode']})
                if worker:
                    tool['current_borrower'] = f"{worker.get('firstname', '')} {worker.get('lastname', '')}"
                    tool['worker_barcode'] = current_lending['worker_barcode']
                    tool['formatted_lent_at'] = current_lending['lent_at'].strftime('%d.%m.%Y %H:%M') if current_lending.get('lent_at') else ''
                else:
                    tool['current_borrower'] = 'Unbekannt'
                    tool['worker_barcode'] = current_lending['worker_barcode']
                    tool['formatted_lent_at'] = current_lending['lent_at'].strftime('%d.%m.%Y %H:%M') if current_lending.get('lent_at') else ''
            else:
                tool['current_borrower'] = None
                tool['worker_barcode'] = None
                tool['formatted_lent_at'] = None
                tool['formatted_returned_at'] = None
        
        # Nach Namen sortieren
        tools.sort(key=lambda x: x.get('name', ''))
        return tools

    @staticmethod
    def get_lending_history(barcode):
        """Holt die Ausleihhistorie für ein Werkzeug"""
        from .mongodb_database import get_database
        
        db = get_database()
        lendings_collection = db['lendings']
        workers_collection = db['workers']
        
        # Alle Ausleihungen für das Werkzeug holen
        lendings = list(lendings_collection.find({'tool_barcode': barcode}).sort([('lent_at', -1)]))
        
        history = []
        for lending in lendings:
            # Worker-Informationen holen
            worker = workers_collection.find_one({'barcode': lending['worker_barcode']})
            worker_name = f"{worker.get('firstname', '')} {worker.get('lastname', '')}" if worker else 'Unbekannt'
            
            # Ausleihe-Eintrag
            history.append({
                'action_type': 'Ausleihe/Rückgabe',
                'action_date': lending['lent_at'].strftime('%d.%m.%Y %H:%M') if lending.get('lent_at') else '',
                'worker': worker_name,
                'action': 'Ausgeliehen',
                'reason': None,
                'raw_date': lending.get('lent_at'),
                'lent_at': lending['lent_at'].strftime('%d.%m.%Y %H:%M') if lending.get('lent_at') else '',
                'returned_at': None
            })
            
            # Rückgabe-Eintrag (falls vorhanden)
            if lending.get('returned_at'):
                history.append({
                    'action_type': 'Ausleihe/Rückgabe',
                    'action_date': lending['returned_at'].strftime('%d.%m.%Y %H:%M'),
                    'worker': worker_name,
                    'action': 'Zurückgegeben',
                    'reason': None,
                    'raw_date': lending.get('returned_at'),
                    'lent_at': lending['lent_at'].strftime('%d.%m.%Y %H:%M') if lending.get('lent_at') else '',
                    'returned_at': lending['returned_at'].strftime('%d.%m.%Y %H:%M')
                })
        
        # Nach Datum sortieren (neueste zuerst)
        history.sort(key=lambda x: x['raw_date'] if x['raw_date'] else datetime.min, reverse=True)
        return history

    @staticmethod
    def get_by_barcode(barcode):
        """Holt ein Werkzeug anhand des Barcodes"""
        from .mongodb_database import get_database
        
        db = get_database()
        tools_collection = db['tools']
        
        tool_data = tools_collection.find_one({'barcode': barcode, 'deleted': False})
        if tool_data:
            return Tool(**tool_data)
        return None

    @staticmethod
    def get_by_id(tool_id):
        """Holt ein Werkzeug anhand der ID"""
        from .mongodb_database import get_database
        
        db = get_database()
        tools_collection = db['tools']
        
        # Robuste ID-Behandlung für verschiedene ID-Typen
        try:
            # Versuche zuerst mit String-ID
            tool_data = tools_collection.find_one({'_id': tool_id, 'deleted': False})
            if tool_data:
                return Tool(**tool_data)
            
            # Falls nicht gefunden, versuche mit ObjectId
            try:
                obj_id = ObjectId(tool_id)
                tool_data = tools_collection.find_one({'_id': obj_id, 'deleted': False})
                if tool_data:
                    return Tool(**tool_data)
            except Exception as e:
                logger.warning(f"Fehler bei ObjectId-Konvertierung für Tool {tool_id}: [Interner Fehler]")
                pass
            
            return None
        except Exception as e:
            logger.error(f"Fehler beim Suchen von Tool {tool_id}: [Interner Fehler]")
            return None

    def save(self):
        """Speichert das Werkzeug in der Datenbank"""
        from .mongodb_database import get_database
        
        db = get_database()
        tools_collection = db['tools']
        
        if not hasattr(self, '_id') or not self._id:
            # Neues Werkzeug
            self.created_at = datetime.now()
            self.updated_at = datetime.now()
            result = tools_collection.insert_one(self.to_dict())
            self._id = result.inserted_id
        else:
            # Bestehendes Werkzeug aktualisieren
            self.updated_at = datetime.now()
            tools_collection.update_one(
                {'_id': self._id},
                {'$set': self.to_dict()}
            )
        
        return self

    def delete(self):
        """Markiert das Werkzeug als gelöscht (Soft Delete)"""
        from .mongodb_database import get_database
        
        db = get_database()
        tools_collection = db['tools']
        
        self.deleted = True
        self.updated_at = datetime.now()
        tools_collection.update_one(
            {'_id': self._id},
            {'$set': {'deleted': True, 'updated_at': self.updated_at}}
        )

    def to_dict(self):
        """Konvertiert das Werkzeug in ein Dictionary"""
        data = {
            'name': self.name,
            'barcode': self.barcode,
            'category': self.category,
            'location': self.location,
            'description': self.description,
            'image_path': self.image_path,
            'deleted': self.deleted,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'serial_number': self.serial_number,
            'invoice_number': self.invoice_number,
            'mac_address': self.mac_address,
            'mac_address_wlan': self.mac_address_wlan,
            'user_groups': self.user_groups,
            'additional_software': self.additional_software
        }
        
        if hasattr(self, '_id') and self._id:
            data['_id'] = self._id
            
        return data