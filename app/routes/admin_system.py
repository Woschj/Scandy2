"""
Admin System Module - Systemverwaltung und Konfiguration

Dieses Modul enthält alle System-bezogenen Funktionen:
- Systemeinstellungen
- Feature-Flags
- Software-Management
- Nutzergruppen
- Abteilungsverwaltung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from app.utils.decorators import admin_required
from app.models.mongodb_database import mongodb
from app.models.feature_system import (
    feature_system,
    get_feature_settings,
    set_feature_setting,
    is_feature_enabled
)
from app.services.admin_system_settings_service import AdminSystemSettingsService
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('admin_system', __name__, url_prefix='/admin')

@bp.route('/system', methods=['GET', 'POST'])
@admin_required
def system_settings():
    """Systemeinstellungen verwalten"""
    try:
        if request.method == 'POST':
            # Einstellungen aktualisieren
            settings_data = {
                'system_name': request.form.get('system_name', 'Scandy'),
                'ticket_system_name': request.form.get('ticket_system_name', 'Tickets'),
                'tool_system_name': request.form.get('tool_system_name', 'Werkzeuge'),
                'consumable_system_name': request.form.get('consumable_system_name', 'Verbrauchsmaterial'),
                'enable_weekly_reports': request.form.get('enable_weekly_reports') == 'on',
                'enable_job_board': request.form.get('enable_job_board') == 'on',
                'enable_ticket_system': request.form.get('enable_ticket_system') == 'on'
            }

            for key, value in settings_data.items():
                mongodb.update_one('settings',
                                 {'key': key},
                                 {'$set': {'value': value, 'updated_at': datetime.now()}},
                                 upsert=True)

            flash('Systemeinstellungen gespeichert', 'success')
            return redirect(url_for('admin_system.system_settings'))

        # Aktuelle Einstellungen laden
        settings = {}
        setting_keys = [
            'system_name', 'ticket_system_name', 'tool_system_name', 'consumable_system_name',
            'enable_weekly_reports', 'enable_job_board', 'enable_ticket_system'
        ]

        for key in setting_keys:
            setting = mongodb.find_one('settings', {'key': key})
            settings[key] = setting.get('value', '') if setting else ''

        return render_template('admin/server-settings.html', settings=settings)

    except Exception as e:
        logger.error(f"Fehler bei Systemeinstellungen: {str(e)}")
        flash('Fehler bei Systemeinstellungen', 'error')
        return render_template('admin/server-settings.html', settings={})

@bp.route('/feature_settings', methods=['GET', 'POST'])
@admin_required
def feature_settings():
    """Feature-Einstellungen verwalten"""
    try:
        if request.method == 'POST':
            # Feature-Einstellungen aktualisieren
            feature_data = {
                'weekly_reports': request.form.get('weekly_reports') == 'on',
                'job_board': request.form.get('job_board') == 'on',
                'ticket_system': request.form.get('ticket_system') == 'on',
                'canteen_integration': request.form.get('canteen_integration') == 'on',
                'barcode_scanning': request.form.get('barcode_scanning') == 'on',
                'notifications': request.form.get('notifications') == 'on'
            }

            for feature, enabled in feature_data.items():
                set_feature_setting(feature, enabled)

            flash('Feature-Einstellungen gespeichert', 'success')
            return redirect(url_for('admin_system.feature_settings'))

        # Aktuelle Feature-Einstellungen laden
        current_features = get_feature_settings()

        return render_template('admin/feature_settings.html',
                             features=current_features)

    except Exception as e:
        logger.error(f"Fehler bei Feature-Einstellungen: {str(e)}")
        flash('Fehler bei Feature-Einstellungen', 'error')
        return render_template('admin/feature_settings.html', features={})

@bp.route('/software')
@admin_required
def software_management():
    """Software-Management Übersicht"""
    try:
        # Software-Daten laden (vereinfacht)
        software_list = list(mongodb.find('software', {}, sort=[('name', 1)]))

        return render_template('admin/software_management.html',
                             software_list=software_list)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Software: {str(e)}")
        flash('Fehler beim Laden der Software', 'error')
        return render_template('admin/software_management.html', software_list=[])

@bp.route('/software/add', methods=['POST'])
@admin_required
def add_software():
    """Software hinzufügen"""
    try:
        software_data = {
            'name': request.form.get('name', '').strip(),
            'version': request.form.get('version', '').strip(),
            'description': request.form.get('description', '').strip(),
            'category': request.form.get('category', 'allgemein'),
            'created_at': datetime.now(),
            'is_active': True
        }

        if not software_data['name']:
            flash('Software-Name ist erforderlich', 'error')
            return redirect(url_for('admin_system.software_management'))

        software_id = mongodb.insert_one('software', software_data)

        flash('Software erfolgreich hinzugefügt', 'success')
        return redirect(url_for('admin_system.software_management'))

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Software: {str(e)}")
        flash('Fehler beim Hinzufügen der Software', 'error')
        return redirect(url_for('admin_system.software_management'))

@bp.route('/software/delete/<software_id>', methods=['POST'])
@admin_required
def delete_software(software_id):
    """Software löschen"""
    try:
        result = mongodb.delete_one('software', {'_id': software_id})

        if result.deleted_count > 0:
            flash('Software erfolgreich gelöscht', 'success')
        else:
            flash('Software nicht gefunden', 'error')

        return redirect(url_for('admin_system.software_management'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Software {software_id}: {str(e)}")
        flash('Fehler beim Löschen der Software', 'error')
        return redirect(url_for('admin_system.software_management'))

@bp.route('/user_groups')
@admin_required
def user_groups():
    """Nutzgruppen verwalten"""
    try:
        # Gruppen laden
        groups = list(mongodb.find('user_groups', {}, sort=[('name', 1)]))

        return render_template('admin/user_groups.html', groups=groups)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Nutzergruppen: {str(e)}")
        flash('Fehler beim Laden der Nutzergruppen', 'error')
        return render_template('admin/user_groups.html', groups=[])

@bp.route('/user_groups/add', methods=['POST'])
@admin_required
def add_user_group():
    """Nutzergruppe hinzufügen"""
    try:
        group_data = {
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'permissions': request.form.getlist('permissions'),
            'created_at': datetime.now(),
            'is_active': True
        }

        if not group_data['name']:
            flash('Gruppenname ist erforderlich', 'error')
            return redirect(url_for('admin_system.user_groups'))

        group_id = mongodb.insert_one('user_groups', group_data)

        flash('Nutzergruppe erfolgreich erstellt', 'success')
        return redirect(url_for('admin_system.user_groups'))

    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Nutzergruppe: {str(e)}")
        flash('Fehler beim Erstellen der Nutzergruppe', 'error')
        return redirect(url_for('admin_system.user_groups'))

@bp.route('/user_groups/delete/<group_id>', methods=['POST'])
@admin_required
def delete_user_group(group_id):
    """Nutzergruppe löschen"""
    try:
        result = mongodb.delete_one('user_groups', {'_id': group_id})

        if result.deleted_count > 0:
            flash('Nutzergruppe erfolgreich gelöscht', 'success')
        else:
            flash('Nutzergruppe nicht gefunden', 'error')

        return redirect(url_for('admin_system.user_groups'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Nutzergruppe {group_id}: {str(e)}")
        flash('Fehler beim Löschen der Nutzergruppe', 'error')
        return redirect(url_for('admin_system.user_groups'))

@bp.route('/user_groups/<group_id>/edit', methods=['POST'])
@admin_required
def edit_user_group(group_id):
    """Nutzergruppe bearbeiten"""
    try:
        update_data = {
            'name': request.form.get('name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'permissions': request.form.getlist('permissions'),
            'updated_at': datetime.now()
        }

        result = mongodb.update_one('user_groups',
                                  {'_id': group_id},
                                  {'$set': update_data})

        if result.modified_count > 0:
            flash('Nutzergruppe erfolgreich aktualisiert', 'success')
        else:
            flash('Nutzergruppe nicht gefunden oder keine Änderungen', 'warning')

        return redirect(url_for('admin_system.user_groups'))

    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten der Nutzergruppe {group_id}: {str(e)}")
        flash('Fehler beim Bearbeiten der Nutzergruppe', 'error')
        return redirect(url_for('admin_system.user_groups'))

@bp.route('/departments')
@admin_required
def departments():
    """Abteilungen verwalten"""
    try:
        # Abteilungen laden
        departments_data = mongodb.find_one('settings', {'key': 'departments'})
        departments_list = departments_data.get('value', []) if departments_data else []

        return render_template('admin/departments.html',
                             departments=departments_list)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Abteilungen: {str(e)}")
        flash('Fehler beim Laden der Abteilungen', 'error')
        return render_template('admin/departments.html', departments=[])

@bp.route('/departments/manage')
@admin_required
def departments_manage():
    """Abteilungen detailliert verwalten"""
    try:
        # Abteilungen laden
        departments_data = mongodb.find_one('settings', {'key': 'departments'})
        departments_list = departments_data.get('value', []) if departments_data else []

        return render_template('admin/departments.html',
                             departments=departments_list,
                             manage_mode=True)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Abteilungen: {str(e)}")
        flash('Fehler beim Laden der Abteilungen', 'error')
        return render_template('admin/departments.html',
                             departments=[],
                             manage_mode=True)
