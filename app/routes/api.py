from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from app.utils.decorators import admin_required, login_required, mitarbeiter_required
from app.models.mongodb_database import mongodb
import logging
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from datetime import datetime, timedelta

bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)

@bp.before_request
def log_request_info():
    """Loggt alle API-Requests"""
    logger.info(f"Request: {request.method} {request.url} - IP: {request.remote_addr}")

@bp.route('/workers', methods=['GET'])
@mitarbeiter_required
def get_workers():
    """Gibt alle aktiven Mitarbeiter zurück"""
    try:
        workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}, sort=[('lastname', 1), ('firstname', 1)]))
        return jsonify({
            'success': True,
            'workers': workers
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Laden der Mitarbeiter: [Interner Fehler]'
        }), 500

@bp.route('/inventory/tools/<barcode>', methods=['GET'])
@login_required
def get_tool(barcode):
    """Gibt Details zu einem Werkzeug zurück"""
    try:
        tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
        
        # Hole Ausleihhistorie
        lendings = mongodb.find('lendings', {'tool_barcode': barcode}, sort=[('lent_at', -1)])
        
        tool['lending_history'] = lendings
        tool['type'] = 'tool'  # Typ hinzufügen für Quickscan
        
        return jsonify({
            'success': True,
            'tool': tool
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Laden des Werkzeugs: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden des Werkzeugs'
        }), 500

@bp.route('/inventory/workers/<barcode>', methods=['GET'])
@login_required
def get_worker(barcode):
    """Gibt Details zu einem Mitarbeiter zurück"""
    try:
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404
        
        # Hole aktive Ausleihen
        active_lendings = mongodb.find('lendings', {
            'worker_barcode': barcode,
            'returned_at': None
        }, sort=[('lent_at', -1)])
        
        # Hole Ausleihhistorie
        all_lendings = mongodb.find('lendings', {'worker_barcode': barcode}, sort=[('lent_at', -1)])
        
        worker['active_lendings'] = active_lendings
        worker['lending_history'] = all_lendings
        
        return jsonify({
            'success': True,
            'worker': worker
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Laden des Mitarbeiters: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden des Mitarbeiters'
        }), 500

@bp.route('/settings/colors', methods=['POST'])
@admin_required
def update_colors():
    """Aktualisiert die Farbeinstellungen"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Keine Daten empfangen'}), 400
        
        # Speichere die Farben in MongoDB
        for color_key, color_value in data.items():
            mongodb.update_one('settings', 
                             {'key': color_key}, 
                             {'$set': {'value': color_value}}, 
                             upsert=True)
        
        return jsonify({
            'success': True,
            'message': 'Farben erfolgreich aktualisiert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Farben: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Aktualisieren der Farben'
        }), 500

@bp.after_request
def after_request(response):
    """Loggt alle API-Responses"""
    logger.info(f"Response: {response.status_code} {response.status} {response.status_code} - Size: {len(response.get_data())} bytes")
    return response

@bp.route('/lending/process', methods=['POST'])
@login_required
def process_lending_via_api():
    """Alias-Endpoint für Ausleihe/Rückgabe/Verbrauch über das zentrale LendingService.
    Erwartet JSON mit item_barcode, worker_barcode, action (lend|return|consume), item_type (tool|consumable), quantity.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Keine Daten empfangen'}), 400

        from app.services.lending_service import LendingService
        success, message, result_data = LendingService.process_lending_request(data)

        if success:
            return jsonify({'success': True, 'message': message, 'data': result_data})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        logger.error(f"Fehler bei /api/lending/process: [Interner Fehler]", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler bei der Verarbeitung'}), 500

@bp.route('/lending/return', methods=['POST'])
@login_required
def return_tool():
    """Gibt ein Werkzeug zurück"""
    try:
        data = request.get_json()
        tool_barcode = data.get('tool_barcode')
        worker_barcode = data.get('worker_barcode')
        
        logger.info(f"Return request: tool_barcode={tool_barcode}, worker_barcode={worker_barcode}")
        
        if not tool_barcode:
            logger.warning("Missing tool_barcode in return request")
            return jsonify({
                'success': False,
                'message': 'Fehlender tool_barcode Parameter'
            }), 400
        
        # Validiere Werkzeug
        tool = mongodb.find_one('tools', {'barcode': tool_barcode, 'deleted': {'$ne': True}})
        if not tool:
            logger.warning(f"Werkzeug {tool_barcode} nicht gefunden")
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
        
        # Prüfe aktive Ausleihe
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': tool_barcode,
            'returned_at': None
        })
        
        if not active_lending:
            logger.warning(f"Keine aktive Ausleihe für Werkzeug {tool_barcode}")
            return jsonify({
                'success': False,
                'message': 'Dieses Werkzeug ist nicht ausgeliehen'
            }), 400
        
        # Verwende den zentralen LendingService für konsistente Rückgabe
        from app.services.lending_service import LendingService
        
        success, message = LendingService.return_tool_centralized(tool_barcode, worker_barcode)
        
        if success:
            logger.info(f"Rückgabe erfolgreich: {message}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Rückgabe fehlgeschlagen: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
    except Exception as e:
        logger.error(f"Error in return_tool: [Interner Fehler]", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Rückgabe: [Interner Fehler]'
        }), 500

@bp.route('/inventory/consumables/<barcode>', methods=['GET'])
@login_required
def get_consumable(barcode):
    """Gibt Details zu einem Verbrauchsmaterial zurück"""
    try:
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not consumable:
            return jsonify({
                'success': False,
                'message': 'Verbrauchsmaterial nicht gefunden'
            }), 404
        
        # Hole Verbrauchshistorie
        usages = mongodb.find('consumable_usages', {'consumable_barcode': barcode}, sort=[('used_at', -1)])
        
        consumable['usage_history'] = usages
        consumable['type'] = 'consumable'  # Typ hinzufügen für Quickscan
        
        return jsonify({
            'success': True,
            'consumable': consumable
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Laden des Verbrauchsmaterials: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden des Verbrauchsmaterials'
        }), 500

@bp.route('/update_barcode', methods=['POST'])
@mitarbeiter_required
def update_barcode():
    """Aktualisiert einen Barcode"""
    try:
        data = request.get_json()
        old_barcode = data.get('old_barcode')
        new_barcode = data.get('new_barcode')
        item_type = data.get('type')
        
        if not all([old_barcode, new_barcode, item_type]):
            return jsonify({'success': False, 'message': 'Fehlende Parameter'})
        
        if item_type not in ['tool', 'consumable', 'worker']:
            return jsonify({'success': False, 'message': 'Ungültiger Typ'})
        
        # Prüfe ob neuer Barcode bereits existiert
        existing = mongodb.find_one(item_type + 's', {'barcode': new_barcode, 'deleted': {'$ne': True}})
        if existing:
            return jsonify({
                'success': False,
                'message': f'Barcode {new_barcode} existiert bereits'
            }), 400
        
        # Aktualisiere Barcode
        mongodb.update_one(item_type + 's', 
                          {'barcode': old_barcode}, 
                          {'$set': {'barcode': new_barcode}})
        
        # Aktualisiere auch in Ausleihen falls es ein Werkzeug ist
        if item_type == 'tool':
            mongodb.update_many('lendings', 
                              {'tool_barcode': old_barcode}, 
                              {'$set': {'tool_barcode': new_barcode}})
        
        # Aktualisiere auch in Verbrauchsmaterial-Entnahmen falls es ein Verbrauchsmaterial ist
        if item_type == 'consumable':
            mongodb.update_many('consumable_usages', 
                              {'consumable_barcode': old_barcode}, 
                              {'$set': {'consumable_barcode': new_barcode}})
        
        return jsonify({
            'success': True,
            'message': 'Barcode erfolgreich aktualisiert'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Barcodes: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Aktualisieren des Barcodes'
        }), 500

@bp.route('/consumables/<barcode>/forecast', methods=['GET'])
@login_required
def get_consumable_forecast(barcode):
    """Berechnet eine Bestandsprognose für ein Verbrauchsmaterial"""
    try:
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not consumable:
            return jsonify({
                'success': False,
                'message': 'Verbrauchsmaterial nicht gefunden'
            }), 404
        
        # Hole Verbrauch der letzten 30 Tage
        thirty_days_ago = datetime.now() - timedelta(days=30)
        usages = list(mongodb.find('consumable_usages', {
            'consumable_barcode': barcode,
            'used_at': {'$gte': thirty_days_ago},
            'quantity': {'$lt': 0}  # Nur Entnahmen
        }))
        
        # Berechne durchschnittlichen täglichen Verbrauch
        total_usage = abs(sum(usage['quantity'] for usage in usages))
        avg_daily_usage = total_usage / 30 if usages else 0
        
        # Berechne Tage bis zur Neubestellung
        current_quantity = consumable.get('quantity', 0)
        days_until_reorder = int(current_quantity / avg_daily_usage) if avg_daily_usage > 0 else 999
        
        return jsonify({
            'success': True,
            'data': {
                'current_quantity': current_quantity,
                'avg_daily_usage': round(avg_daily_usage, 2),
                'days_until_reorder': days_until_reorder,
                'min_quantity': consumable.get('min_quantity', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Fehler bei der Bestandsprognose: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler bei der Berechnung'
        }), 500

@bp.route('/notices', methods=['GET'])
def get_notices():
    """Gibt alle aktiven Hinweise zurück"""
    try:
        notices = list(mongodb.find('homepage_notices', {'is_active': True}, sort=[('priority', -1), ('created_at', -1)]))
        return jsonify({'success': True, 'notices': notices})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/notices/<id>', methods=['GET'])
@admin_required
def get_notice(id):
    """Gibt einen spezifischen Hinweis zurück"""
    try:
        notice = mongodb.find_one('homepage_notices', {'_id': id})
        if not notice:
            return jsonify({'error': 'Hinweis nicht gefunden'}), 404
        return jsonify({'success': True, 'notice': notice})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/notices', methods=['POST'])
@admin_required
def create_notice():
    """Erstellt einen neuen Hinweis"""
    try:
        data = request.get_json()
        notice_data = {
            'title': data.get('title'),
            'content': data.get('content'),
            'is_active': data.get('is_active', True),
            'priority': data.get('priority', 1),
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        result = mongodb.insert_one('homepage_notices', notice_data)
        return jsonify({'success': True, 'id': str(result)})
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/notices/<id>', methods=['PUT'])
@admin_required
def update_notice(id):
    """Aktualisiert einen Hinweis"""
    try:
        data = request.get_json()
        update_data = {
            'title': data.get('title'),
            'content': data.get('content'),
            'is_active': data.get('is_active', True),
            'priority': data.get('priority', 1),
            'updated_at': datetime.now()
        }
        mongodb.update_one('homepage_notices', {'_id': id}, {'$set': update_data})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/notices/<id>', methods=['DELETE'])
@admin_required
def delete_notice(id):
    """Löscht einen Hinweis"""
    try:
        mongodb.delete_one('homepage_notices', {'_id': id})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/quickscan/process_lending', methods=['POST'])
@login_required
def process_lending():
    """Verarbeitet Ausleihe/Rückgabe über Quickscan"""
    try:
        import logging
        logger = logging.getLogger("quickscan")
        data = request.get_json()
        logger.info(f"QuickScan-Request: {data}")
        
        # Verwende den zentralen Lending Service
        from app.services.lending_service import LendingService
        success, message, result_data = LendingService.process_lending_request(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'data': result_data
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
    except Exception as e:
        import traceback
        logger.error(f"Fehler bei der Quickscan-Verarbeitung: [Interner Fehler]\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': 'Fehler bei der Verarbeitung'
        }), 500

@bp.route('/debug/test-return/<tool_barcode>', methods=['POST'])
@login_required
def test_return_tool(tool_barcode):
    """Test-Route für Rückgabe-Problem"""
    try:
        logger.info(f"Test return für Werkzeug: {tool_barcode}")
        
        # Validiere Werkzeug
        tool = mongodb.find_one('tools', {'barcode': tool_barcode, 'deleted': {'$ne': True}})
        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404
        
        # Prüfe aktive Ausleihe
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': tool_barcode,
            'returned_at': None
        })
        
        if not active_lending:
            return jsonify({
                'success': False,
                'message': 'Dieses Werkzeug ist nicht ausgeliehen'
            }), 400
        
        # Verwende den zentralen LendingService
        from app.services.lending_service import LendingService
        
        success, message = LendingService.return_tool_centralized(tool_barcode, None)
        
        return jsonify({
            'success': success,
            'message': message,
            'tool': {
                'name': tool.get('name'),
                'status': tool.get('status'),
                'barcode': tool.get('barcode')
            },
            'lending': {
                'id': str(active_lending.get('_id')),
                'worker_barcode': active_lending.get('worker_barcode'),
                'lent_at': str(active_lending.get('lent_at'))
            }
        })
        
    except Exception as e:
        logger.error(f"Fehler in test_return_tool: [Interner Fehler]", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler: [Interner Fehler]'
        }), 500

@bp.route('/debug/test-mongodb-update/<tool_barcode>', methods=['POST'])
@login_required
def test_mongodb_update(tool_barcode):
    """Test-Route für MongoDB-Update-Problem"""
    try:
        logger.info(f"Test MongoDB Update für Werkzeug: {tool_barcode}")
        
        # Finde aktive Ausleihe
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': tool_barcode,
            'returned_at': None
        })
        
        if not active_lending:
            return jsonify({
                'success': False,
                'message': 'Keine aktive Ausleihe gefunden'
            }), 400
        
        logger.info(f"Aktive Ausleihe gefunden: {active_lending}")
        
        # Teste direktes MongoDB-Update
        from datetime import datetime
        
        # Test 1: Einfaches Update
        logger.info("Test 1: Einfaches Update")
        result1 = mongodb.update_one('lendings', 
                                   {'_id': active_lending['_id']}, 
                                   {'$set': {'test_field': 'test_value'}})
        logger.info(f"Test 1 Ergebnis: {result1}")
        
        # Test 2: Update mit returned_at
        logger.info("Test 2: Update mit returned_at")
        result2 = mongodb.update_one('lendings', 
                                   {'_id': active_lending['_id']}, 
                                   {'$set': {'returned_at': datetime.now()}})
        logger.info(f"Test 2 Ergebnis: {result2}")
        
        # Test 3: Update mit $unset
        logger.info("Test 3: Update mit $unset")
        result3 = mongodb.update_one('lendings', 
                                   {'_id': active_lending['_id']}, 
                                   {'$unset': {'test_field': ''}})
        logger.info(f"Test 3 Ergebnis: {result3}")
        
        return jsonify({
            'success': True,
            'message': 'MongoDB Update Tests abgeschlossen',
            'results': {
                'test1': result1,
                'test2': result2,
                'test3': result3
            },
            'lending_id': str(active_lending['_id'])
        })
        
    except Exception as e:
        logger.error(f"Fehler in test_mongodb_update: [Interner Fehler]", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler: [Interner Fehler]'
        }), 500