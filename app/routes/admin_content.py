"""
Admin Content Module - Verwaltung von Tools, Consumables und Workers

Dieses Modul enthält alle CRUD-Operationen für:
- Tools (Werkzeuge)
- Consumables (Verbrauchsmaterial)
- Workers (Mitarbeitende)
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from app.utils.decorators import admin_required, mitarbeiter_required
from app.utils.permissions import permission_required
from app.models.mongodb_models import MongoDBTool, MongoDBWorker, MongoDBConsumable
from app.models.mongodb_database import mongodb
from app.services.excel_export_service import ExcelExportService
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

bp = Blueprint('admin_content', __name__, url_prefix='/admin')

# ===== TOOLS MANAGEMENT =====

@bp.route('/tools/delete', methods=['DELETE'])
@mitarbeiter_required
@permission_required('tools', 'delete')
def delete_tools():
    """Mehrere Tools löschen (Soft Delete)"""
    try:
        data = request.get_json()
        tool_barcodes = data.get('tool_barcodes', [])

        if not tool_barcodes:
            return jsonify({'success': False, 'message': 'Keine Tools ausgewählt'}), 400

        deleted_count = 0
        for barcode in tool_barcodes:
            tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
            if tool:
                mongodb.update_one('tools',
                                 {'barcode': barcode},
                                 {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
                deleted_count += 1

        return jsonify({
            'success': True,
            'message': f'{deleted_count} Werkzeuge erfolgreich gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Tools: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen der Tools'}), 500

@bp.route('/tools/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
@permission_required('tools', 'delete')
def delete_tool_by_barcode(barcode):
    """Einzelnes Tool löschen (Soft Delete)"""
    try:
        tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not tool:
            return jsonify({'success': False, 'message': 'Werkzeug nicht gefunden'}), 404

        mongodb.update_one('tools',
                         {'barcode': barcode},
                         {'$set': {'deleted': True, 'deleted_at': datetime.now()}})

        return jsonify({'success': True, 'message': 'Werkzeug erfolgreich gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs {barcode}: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen des Werkzeugs'}), 500

@bp.route('/tools/<barcode>/delete-permanent', methods=['DELETE'])
@admin_required
def delete_tool_permanent(barcode):
    """Tool permanent löschen"""
    try:
        tool = mongodb.find_one('tools', {'barcode': barcode})
        if not tool:
            return jsonify({'success': False, 'message': 'Werkzeug nicht gefunden'}), 404

        mongodb.delete_one('tools', {'barcode': barcode})

        # Auch zugehörige Ausleihen löschen
        mongodb.delete_many('lendings', {'tool_barcode': barcode})

        return jsonify({'success': True, 'message': 'Werkzeug dauerhaft gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Werkzeugs {barcode}: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim permanenten Löschen'}), 500

# ===== CONSUMABLES MANAGEMENT =====

@bp.route('/consumables/delete', methods=['DELETE'])
@mitarbeiter_required
@permission_required('consumables', 'delete')
def delete_consumables():
    """Mehrere Verbrauchsmaterialien löschen (Soft Delete)"""
    try:
        data = request.get_json()
        consumable_barcodes = data.get('consumable_barcodes', [])

        if not consumable_barcodes:
            return jsonify({'success': False, 'message': 'Keine Verbrauchsmaterialien ausgewählt'}), 400

        deleted_count = 0
        for barcode in consumable_barcodes:
            consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
            if consumable:
                mongodb.update_one('consumables',
                                 {'barcode': barcode},
                                 {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
                deleted_count += 1

        return jsonify({
            'success': True,
            'message': f'{deleted_count} Verbrauchsmaterialien erfolgreich gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Verbrauchsmaterialien: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen der Verbrauchsmaterialien'}), 500

@bp.route('/consumables/<barcode>/delete-permanent', methods=['DELETE'])
@admin_required
def delete_consumable_permanent(barcode):
    """Verbrauchsmaterial permanent löschen"""
    try:
        consumable = mongodb.find_one('consumables', {'barcode': barcode})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404

        mongodb.delete_one('consumables', {'barcode': barcode})

        return jsonify({'success': True, 'message': 'Verbrauchsmaterial dauerhaft gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Verbrauchsmaterials {barcode}: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim permanenten Löschen'}), 500

# ===== WORKERS MANAGEMENT =====

@bp.route('/workers/delete', methods=['DELETE'])
@mitarbeiter_required
@permission_required('workers', 'delete')
def delete_workers():
    """Mehrere Mitarbeitende löschen (Soft Delete)"""
    try:
        data = request.get_json()
        worker_barcodes = data.get('worker_barcodes', [])

        if not worker_barcodes:
            return jsonify({'success': False, 'message': 'Keine Mitarbeitenden ausgewählt'}), 400

        deleted_count = 0
        errors = []

        for barcode in worker_barcodes:
            worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
            if worker:
                # Prüfen ob Mitarbeitende noch Werkzeuge ausgeliehen hat
                lending = mongodb.find_one('lendings', {'worker_barcode': barcode, 'returned_at': None})
                if lending:
                    errors.append(f"Mitarbeitende {barcode} hat noch Werkzeuge ausgeliehen")
                    continue

                mongodb.update_one('workers',
                                 {'barcode': barcode},
                                 {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
                deleted_count += 1

        message = f'{deleted_count} Mitarbeitende erfolgreich gelöscht'
        if errors:
            message += f'. Fehler: {", ".join(errors)}'

        return jsonify({
            'success': True,
            'message': message
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Mitarbeitenden: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen der Mitarbeitenden'}), 500

@bp.route('/workers/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
@permission_required('workers', 'delete')
def delete_worker_by_barcode(barcode):
    """Einzelne Mitarbeitende löschen (Soft Delete)"""
    try:
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeitende nicht gefunden'}), 404

        # Prüfen ob Mitarbeitende noch Werkzeuge ausgeliehen hat
        lending = mongodb.find_one('lendings', {'worker_barcode': barcode, 'returned_at': None})
        if lending:
            return jsonify({
                'success': False,
                'message': 'Mitarbeitende muss zuerst alle Werkzeuge zurückgeben'
            }), 400

        mongodb.update_one('workers',
                         {'barcode': barcode},
                         {'$set': {'deleted': True, 'deleted_at': datetime.now()}})

        return jsonify({'success': True, 'message': 'Mitarbeitende erfolgreich gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Mitarbeitenden {barcode}: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen der Mitarbeitenden'}), 500

@bp.route('/workers/<barcode>/delete-permanent', methods=['DELETE'])
@admin_required
def delete_worker_permanent(barcode):
    """Mitarbeitende permanent löschen"""
    try:
        worker = mongodb.find_one('workers', {'barcode': barcode})
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeitende nicht gefunden'}), 404

        # Prüfen ob Mitarbeitende noch Werkzeuge ausgeliehen hat
        lending = mongodb.find_one('lendings', {'worker_barcode': barcode, 'returned_at': None})
        if lending:
            return jsonify({
                'success': False,
                'message': 'Mitarbeitende muss zuerst alle Werkzeuge zurückgeben'
            }), 400

        mongodb.delete_one('workers', {'barcode': barcode})

        return jsonify({'success': True, 'message': 'Mitarbeitende dauerhaft gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen der Mitarbeitenden {barcode}: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim permanenten Löschen'}), 500

# ===== MANUAL LENDING =====

@bp.route('/manual-lending', methods=['GET', 'POST'])
@admin_required
def manual_lending():
    """Manuelle Ausleihe von Werkzeugen"""
    try:
        if request.method == 'GET':
            # Daten für die Auswahl laden
            tools = list(mongodb.find('tools',
                                    {'deleted': {'$ne': True}},
                                    sort=[('name', 1)]))
            workers = list(mongodb.find('workers',
                                      {'deleted': {'$ne': True}},
                                      sort=[('lastname', 1), ('firstname', 1)]))
            consumables = list(mongodb.find('consumables',
                                          {'deleted': {'$ne': True}},
                                          sort=[('name', 1)]))

            # Aktive Ausleihen laden
            current_lendings = list(mongodb.find('lendings',
                                               {'returned_at': None},
                                               sort=[('lent_at', -1)]))

            return render_template('admin/manual_lending.html',
                                 tools=tools,
                                 workers=workers,
                                 consumables=consumables,
                                 current_lendings=current_lendings)

        # POST-Request verarbeiten
        # Hier würde die Logik für manuelle Ausleihe stehen
        flash('Manuelle Ausleihe-Funktion noch nicht implementiert', 'info')
        return redirect(url_for('admin_content.manual_lending'))

    except Exception as e:
        logger.error(f"Fehler bei manueller Ausleihe: {str(e)}")
        flash('Fehler bei manueller Ausleihe', 'error')
        return redirect(url_for('admin_content.manual_lending'))
