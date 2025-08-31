"""
Admin Media Module - Medienverwaltung

Dieses Modul enthält alle Funktionen für:
- Logo-Upload und -Verwaltung
- Medien-Uploads
- Datei-Management
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import current_user
from app.utils.decorators import admin_required
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

bp = Blueprint('admin_media', __name__, url_prefix='/admin')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

def allowed_file(filename):
    """Prüfen ob Dateiendung erlaubt ist"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/upload_logo', methods=['POST'])
@admin_required
def upload_logo():
    """Logo hochladen"""
    try:
        if 'logo' not in request.files:
            flash('Keine Datei ausgewählt', 'error')
            return redirect(request.referrer or url_for('admin_core.dashboard'))

        file = request.files['logo']

        if file.filename == '':
            flash('Keine Datei ausgewählt', 'error')
            return redirect(request.referrer or url_for('admin_core.dashboard'))

        if not allowed_file(file.filename):
            flash('Dateityp nicht erlaubt. Nur PNG, JPG, JPEG, GIF, SVG sind erlaubt.', 'error')
            return redirect(request.referrer or url_for('admin_core.dashboard'))

        # Dateiname sichern
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"

        # Upload-Verzeichnis erstellen falls nicht vorhanden
        upload_dir = Path(current_app.root_path) / 'static' / 'uploads' / 'logos'
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Datei speichern
        file_path = upload_dir / filename
        file.save(file_path)

        # Logo-Pfad in Datenbank speichern
        from app.models.mongodb_database import mongodb
        mongodb.update_one(
            'settings',
            {'key': 'logo_path'},
            {'$set': {'value': f'/static/uploads/logos/{filename}', 'updated_at': datetime.now()}},
            upsert=True
        )

        flash('Logo erfolgreich hochgeladen', 'success')
        return redirect(request.referrer or url_for('admin_core.dashboard'))

    except Exception as e:
        logger.error(f"Fehler beim Logo-Upload: {str(e)}")
        flash('Fehler beim Logo-Upload', 'error')
        return redirect(request.referrer or url_for('admin_core.dashboard'))

@bp.route('/delete-logo/<filename>', methods=['POST'])
@admin_required
def delete_logo(filename):
    """Logo löschen"""
    try:
        # Datei sichern für Löschung
        secure_name = secure_filename(filename)

        # Pfad zur Datei
        file_path = Path(current_app.root_path) / 'static' / 'uploads' / 'logos' / secure_name

        # Datei löschen falls sie existiert
        if file_path.exists():
            file_path.unlink()

            # Logo-Einstellung aus Datenbank entfernen
            from app.models.mongodb_database import mongodb
            mongodb.update_one(
                'settings',
                {'key': 'logo_path'},
                {'$unset': {'value': 1}, '$set': {'updated_at': datetime.now()}}
            )

            flash('Logo erfolgreich gelöscht', 'success')
        else:
            flash('Logo-Datei nicht gefunden', 'warning')

        return redirect(request.referrer or url_for('admin_core.dashboard'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Logos {filename}: {str(e)}")
        flash('Fehler beim Löschen des Logos', 'error')
        return redirect(request.referrer or url_for('admin_core.dashboard'))

# Zusätzliche Medien-Management-Funktionen können hier hinzugefügt werden
