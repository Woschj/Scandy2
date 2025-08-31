"""
Admin Users Module - Nutzerverwaltung

Dieses Modul enthält alle Funktionen für:
- Nutzererstellung und -bearbeitung
- Rollen- und Berechtigungsverwaltung
- Nutzer-Migrationen
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user
from app.utils.decorators import admin_required
from app.services.admin_user_service import AdminUserService
from app.models.mongodb_database import mongodb
from app.utils.permissions import (
    get_role_permissions,
    set_role_permissions,
    DEFAULT_ROLE_PERMISSIONS,
    ALLOWED_ACTIONS,
    get_all_actions,
    normalize_permissions
)
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('admin_users', __name__, url_prefix='/admin')

@bp.route('/manage_users')
@admin_required
def manage_users():
    """Nutzerverwaltung-Übersicht"""
    try:
        users = AdminUserService.get_all_users()
        user_stats = AdminUserService.get_user_statistics()

        return render_template('admin/users.html',
                             users=users,
                             user_stats=user_stats)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Nutzer: {e}")
        flash('Fehler beim Laden der Nutzer', 'error')
        return render_template('admin/users.html', users=[], user_stats={})

@bp.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Neuen Nutzer hinzufügen"""
    try:
        if request.method == 'GET':
            roles = ['admin', 'mitarbeiter', 'anwender', 'teilnehmer']
            return render_template('admin/user_form.html', roles=roles, form_data=request.form)

        # POST verarbeiten
        user_data = {
            'username': request.form.get('username', '').strip(),
            'password': request.form.get('password', '').strip(),
            'email': request.form.get('email', '').strip(),
            'role': request.form.get('role', 'anwender'),
            'firstname': request.form.get('firstname', '').strip(),
            'lastname': request.form.get('lastname', '').strip(),
            'is_active': request.form.get('is_active') == 'on'
        }

        success, message, user_id = AdminUserService.create_user(user_data)

        if success:
            flash(message, 'success')
            return redirect(url_for('admin_users.manage_users'))
        else:
            flash(message, 'error')
            return render_template('admin/user_form.html',
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                                 form_data=request.form)

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Nutzers: {str(e)}")
        flash('Fehler beim Hinzufügen des Nutzers', 'error')
        return render_template('admin/user_form.html',
                             roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                             form_data=request.form)

@bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Nutzer bearbeiten"""
    try:
        if request.method == 'GET':
            user = AdminUserService.get_user_by_id(user_id)
            if not user:
                flash('Nutzer nicht gefunden', 'error')
                return redirect(url_for('admin_users.manage_users'))

            roles = ['admin', 'mitarbeiter', 'anwender', 'teilnehmer']
            return render_template('admin/user_form.html',
                                 user=user,
                                 roles=roles,
                                 edit_mode=True)

        # POST verarbeiten
        user_data = {
            'username': request.form.get('username', '').strip(),
            'email': request.form.get('email', '').strip(),
            'role': request.form.get('role', 'anwender'),
            'firstname': request.form.get('firstname', '').strip(),
            'lastname': request.form.get('lastname', '').strip(),
            'is_active': request.form.get('is_active') == 'on'
        }

        # Passwort nur aktualisieren wenn angegeben
        password = request.form.get('password', '').strip()
        if password:
            user_data['password'] = password

        success, message = AdminUserService.update_user(user_id, user_data)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin_users.manage_users'))

    except Exception as e:
        logger.error(f"Fehler beim Bearbeiten des Nutzers {user_id}: {str(e)}")
        flash('Fehler beim Bearbeiten des Nutzers', 'error')
        return redirect(url_for('admin_users.manage_users'))

@bp.route('/migrate_users_to_workers', methods=['POST'])
@admin_required
def migrate_users_to_workers():
    """Nutzer zu Mitarbeitenden migrieren"""
    try:
        # Diese Funktion ist veraltet
        flash('Diese Funktion wurde entfernt. Bitte verwalten Sie Mitarbeitende über die dedizierten Formulare.', 'info')
        return redirect(url_for('admin_users.manage_users'))

    except Exception as e:
        logger.error(f"Fehler bei Nutzer-Migration: {str(e)}")
        flash('Fehler bei Nutzer-Migration', 'error')
        return redirect(url_for('admin_users.manage_users'))

@bp.route('/role_permissions', methods=['GET', 'POST'])
@admin_required
def role_permissions():
    """Rollen und Berechtigungen verwalten"""
    try:
        if request.method == 'POST':
            # Berechtigungen aktualisieren
            role = request.form.get('role')
            action = request.form.get('action')
            allowed = request.form.get('allowed') == 'true'

            if role and action:
                permissions = get_role_permissions(role)
                if action not in permissions:
                    permissions[action] = {}
                permissions[action]['allowed'] = allowed
                set_role_permissions(role, permissions)

                flash(f'Berechtigung für {role} aktualisiert', 'success')

        # Aktuelle Berechtigungen laden
        roles = ['admin', 'mitarbeiter', 'anwender', 'teilnehmer']
        all_permissions = {}

        for role in roles:
            all_permissions[role] = get_role_permissions(role)

        actions = get_all_actions()

        return render_template('admin/role_permissions.html',
                             roles=roles,
                             permissions=all_permissions,
                             actions=actions)

    except Exception as e:
        logger.error(f"Fehler bei Rollen-Berechtigungen: {str(e)}")
        flash('Fehler bei Rollen-Berechtigungen', 'error')
        return redirect(url_for('admin_users.manage_users'))
