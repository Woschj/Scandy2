"""
Admin Core Module - Dashboard und Kernfunktionen

Dieses Modul enthält die Kern-Admin-Funktionalitäten:
- Dashboard
- Hauptnavigation
- Grundlegende Admin-Funktionen
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, current_app
from flask_login import current_user
from app.utils.decorators import admin_required
from app.models.mongodb_database import mongodb
from app.services.admin_dashboard_service import AdminDashboardService
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('admin_core', __name__, url_prefix='/admin')

@bp.route('/')
@bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin-Dashboard mit Übersichten und Statistiken"""
    try:
        # Dashboard-Daten laden
        dashboard_data = AdminDashboardService.get_dashboard_data()

        return render_template('admin/dashboard.html',
                             **dashboard_data)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Admin-Dashboards: {str(e)}")
        flash('Fehler beim Laden des Dashboards', 'error')
        return render_template('admin/dashboard.html',
                             tools_count=0,
                             consumables_count=0,
                             workers_count=0,
                             tickets_count=0,
                             recent_activities=[])

@bp.route('/change_department', methods=['POST'])
@admin_required
def change_department():
    """Abteilung wechseln"""
    try:
        department = request.form.get('department')
        if department:
            session = request.session
            session['department'] = department
            flash(f'Abteilung gewechselt zu: {department}', 'success')
        else:
            flash('Keine Abteilung ausgewählt', 'error')
    except Exception as e:
        logger.error(f"Fehler beim Abteilungswechsel: {str(e)}")
        flash('Fehler beim Abteilungswechsel', 'error')

    return redirect(request.referrer or url_for('admin_core.dashboard'))

# Weitere Kernfunktionen können hier hinzugefügt werden
