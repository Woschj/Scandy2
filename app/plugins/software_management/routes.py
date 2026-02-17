from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import logging
from app.models.mongodb_database import mongodb, is_feature_enabled
from app.utils.decorators import mitarbeiter_required
from bson import ObjectId
from datetime import datetime

bp = Blueprint('software_management', __name__)
logger = logging.getLogger(__name__)

@bp.route('/software')
@mitarbeiter_required
def get_software():
    """Gibt alle Software-Pakete zurück"""
    try:
        software_list = mongodb.find('software', {}, sort=[('name', 1)])
        return jsonify({
            'success': True,
            'software': list(software_list)
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Software: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Software'
        })

@bp.route('/software/add', methods=['POST'])
@mitarbeiter_required
def add_software():
    """Fügt ein neues Software-Paket hinzu"""
    try:
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Prüfe ob Software bereits existiert
        existing = mongodb.find_one('software', {'name': name})
        if existing:
            return jsonify({
                'success': False,
                'message': 'Diese Software existiert bereits.'
            })

        software_data = {
            'name': name,
            'category': category,
            'description': description,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        mongodb.insert_one('software', software_data)

        return jsonify({
            'success': True,
            'message': f'Software "{name}" erfolgreich hinzugefügt'
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Software: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/software/delete/<software_id>', methods=['POST'])
@mitarbeiter_required
def delete_software(software_id):
    """Löscht ein Software-Paket"""
    try:
        # Prüfe ob Software in Nutzergruppen verwendet wird
        groups_using_software = mongodb.find('user_groups', {'software': {'$in': [software_id]}})
        if list(groups_using_software):
            return jsonify({
                'success': False,
                'message': 'Diese Software wird noch in Nutzergruppen verwendet und kann nicht gelöscht werden.'
            })

        result = mongodb.delete_one('software', {'_id': ObjectId(software_id)})

        if result.deleted_count > 0:
            return jsonify({
                'success': True,
                'message': 'Software erfolgreich gelöscht'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Software nicht gefunden'
            })

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Software: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/user_groups')
@mitarbeiter_required
def get_user_groups_admin():
    """Gibt alle Nutzergruppen zurück"""
    try:
        groups = mongodb.find('user_groups', {}, sort=[('name', 1)])
        return jsonify({
            'success': True,
            'groups': list(groups)
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Nutzergruppen: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Nutzergruppen'
        })

@bp.route('/user_groups/add', methods=['POST'])
@mitarbeiter_required
def add_user_group():
    """Fügt eine neue Nutzergruppe hinzu"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        software_ids = request.form.getlist('software')

        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Prüfe ob Gruppe bereits existiert
        existing = mongodb.find_one('user_groups', {'name': name})
        if existing:
            return jsonify({
                'success': False,
                'message': 'Diese Nutzergruppe existiert bereits.'
            })

        group_data = {
            'name': name,
            'description': description,
            'software': software_ids,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        mongodb.insert_one('user_groups', group_data)

        return jsonify({
            'success': True,
            'message': f'Nutzergruppe "{name}" erfolgreich hinzugefügt'
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Nutzergruppe: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/user_groups/delete/<group_id>', methods=['POST'])
@mitarbeiter_required
def delete_user_group(group_id):
    """Löscht eine Nutzergruppe"""
    try:
        # Prüfe ob Gruppe in Werkzeugen verwendet wird
        tools_using_group = mongodb.find('tools', {'user_groups': {'$in': [group_id]}})
        if list(tools_using_group):
            return jsonify({
                'success': False,
                'message': 'Diese Nutzergruppe wird noch in Werkzeugen verwendet und kann nicht gelöscht werden.'
            })

        result = mongodb.delete_one('user_groups', {'_id': ObjectId(group_id)})

        if result.deleted_count > 0:
            return jsonify({
                'success': True,
                'message': 'Nutzergruppe erfolgreich gelöscht'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nutzergruppe nicht gefunden'
            })

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Nutzergruppe: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/user_groups/<group_id>/edit', methods=['POST'])
@mitarbeiter_required
def edit_user_group(group_id):
    """Bearbeitet eine Nutzergruppe"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        software_ids = request.form.getlist('software')

        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Prüfe ob Name bereits existiert (außer bei der aktuellen Gruppe)
        existing = mongodb.find_one('user_groups', {'name': name, '_id': {'$ne': ObjectId(group_id)}})
        if existing:
            return jsonify({
                'success': False,
                'message': 'Diese Nutzergruppe existiert bereits.'
            })

        update_data = {
            'name': name,
            'description': description,
            'software': software_ids,
            'updated_at': datetime.now()
        }

        success = mongodb.update_one('user_groups', {'_id': ObjectId(group_id)}, {'$set': update_data})

        if success:
            return jsonify({
                'success': True,
                'message': f'Nutzergruppe "{name}" erfolgreich aktualisiert'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nutzergruppe nicht gefunden oder keine Änderungen'
            })

    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten der Nutzergruppe: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/software_management')
@mitarbeiter_required
def software_management():
    """Software- und Nutzergruppen-Verwaltung"""
    try:
        # Prüfe ob Software-Management aktiviert ist
        if not is_feature_enabled('software_management'):
            flash('Software-Management ist deaktiviert', 'error')
            return redirect(url_for('admin.dashboard'))

        # Hole alle Software-Pakete
        software_list = list(mongodb.find('software', {}, sort=[('name', 1)]))

        # Hole alle Nutzergruppen
        groups_list = list(mongodb.find('user_groups', {}, sort=[('name', 1)]))

        return render_template('software_management/software_management.html',
                             software_list=software_list,
                             groups_list=groups_list)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Software-Verwaltung: [Interner Fehler]")
        flash('Fehler beim Laden der Software-Verwaltung', 'error')
        return redirect(url_for('admin.dashboard'))
