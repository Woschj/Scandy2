from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from app.models.mongodb_models import MongoDBLending
import logging

bp = Blueprint('lending', __name__)
logger = logging.getLogger(__name__)

# Test-Route ohne Login-Erfordernis
@bp.route('/api/lending/test', methods=['GET'])
def test_lending():
    return jsonify({
        'status': 'ok',
        'message': 'Lending API is working'
    })

@bp.route('/api/lending/process', methods=['POST'])
@login_required
def process_lending():
    logger.info("=== Starting process_lending ===")
    logger.info(f"Request Method: {request.method}")
    logger.info(f"Request Path: {request.path}")
    logger.info(f"Request Headers: {dict(request.headers)}")
    
    try:
        data = request.get_json()
        logger.info(f"Received data: {data}")
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'Keine Daten empfangen'
            }), 400

        # Validierung der Eingabedaten
        required_fields = ['item_type', 'item_barcode', 'worker_barcode']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Fehlende Pflichtfelder: {", ".join(missing_fields)}'
            }), 400

        # Test-Antwort für Debug
        return jsonify({
            'success': True,
            'message': 'Test-Antwort',
            'received_data': data
        })

    except Exception as e:
        logger.error(f"Error in process_lending: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Ausleihe: {str(e)}'
        }), 500