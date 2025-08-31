"""
Admin Trash Module - Papierkorb und Wiederherstellungsfunktionen

Dieses Modul enthält alle Funktionen für:
- Papierkorb-Verwaltung
- Wiederherstellung gelöschter Objekte
- Bereinigung alter Daten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from app.utils.decorators import admin_required, mitarbeiter_required
from app.models.mongodb_database import mongodb
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

bp = Blueprint('admin_trash', __name__, url_prefix='/admin')

@bp.route('/trash')
@admin_required
def trash():
    """Papierkorb-Übersicht"""
    try:
        # Gelöschte Objekte laden
        deleted_tools = list(mongodb.find('tools',
                                        {'deleted': True},
                                        sort=[('deleted_at', -1)]))
        deleted_consumables = list(mongodb.find('consumables',
                                              {'deleted': True},
                                              sort=[('deleted_at', -1)]))
        deleted_workers = list(mongodb.find('workers',
                                          {'deleted': True},
                                          sort=[('deleted_at', -1)]))

        return render_template('admin/trash.html',
                             deleted_tools=deleted_tools,
                             deleted_consumables=deleted_consumables,
                             deleted_workers=deleted_workers)

    except Exception as e:
        logger.error(f"Fehler beim Laden des Papierkorbs: {str(e)}")
        flash('Fehler beim Laden des Papierkorbs', 'error')
        return render_template('admin/trash.html',
                             deleted_tools=[],
                             deleted_consumables=[],
                             deleted_workers=[])

@bp.route('/trash/restore/<type>/<barcode>', methods=['POST'])
@admin_required
def restore_item(type, barcode):
    """Objekt aus dem Papierkorb wiederherstellen"""
    try:
        collection_map = {
            'tool': 'tools',
            'consumable': 'consumables',
            'worker': 'workers'
        }

        if type not in collection_map:
            return jsonify({'success': False, 'message': 'Ungültiger Objekttyp'}), 400

        collection = collection_map[type]

        # Objekt wiederherstellen
        result = mongodb.update_one(
            collection,
            {'barcode': barcode, 'deleted': True},
            {'$unset': {'deleted': 1, 'deleted_at': 1}}
        )

        if result.modified_count > 0:
            return jsonify({
                'success': True,
                'message': f'{type.capitalize()} erfolgreich wiederhergestellt'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'{type.capitalize()} nicht gefunden oder bereits wiederhergestellt'
            }), 404

    except Exception as e:
        logger.error(f"Fehler bei Wiederherstellung {type}/{barcode}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler bei Wiederherstellung: {str(e)}'
        }), 500

@bp.route('/cleanup_status')
@admin_required
def cleanup_status():
    """Status der Bereinigungsoperationen"""
    try:
        # Bereinigungsstatistiken sammeln
        total_deleted_tools = mongodb.count_documents('tools', {'deleted': True})
        total_deleted_consumables = mongodb.count_documents('consumables', {'deleted': True})
        total_deleted_workers = mongodb.count_documents('workers', {'deleted': True})

        # Älteste gelöschte Objekte finden
        oldest_tool = mongodb.find_one('tools',
                                     {'deleted': True},
                                     sort=[('deleted_at', 1)])
        oldest_consumable = mongodb.find_one('consumables',
                                           {'deleted': True},
                                           sort=[('deleted_at', 1)])
        oldest_worker = mongodb.find_one('workers',
                                        {'deleted': True},
                                        sort=[('deleted_at', 1)])

        stats = {
            'total_deleted_tools': total_deleted_tools,
            'total_deleted_consumables': total_deleted_consumables,
            'total_deleted_workers': total_deleted_workers,
            'oldest_tool': oldest_tool.get('deleted_at') if oldest_tool else None,
            'oldest_consumable': oldest_consumable.get('deleted_at') if oldest_consumable else None,
            'oldest_worker': oldest_worker.get('deleted_at') if oldest_worker else None
        }

        return render_template('admin/cleanup_status.html', stats=stats)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Bereinigungsstatistiken: {str(e)}")
        flash('Fehler beim Laden der Bereinigungsstatistiken', 'error')
        return render_template('admin/cleanup_status.html', stats={})

# Zusätzliche Hilfsfunktionen können hier hinzugefügt werden
