#!/usr/bin/env python3
"""
Vereinfachte Backup-Routen für Scandy
"""

import os
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.utils.simple_backup import simple_backup
from app.utils.decorators import admin_required

bp = Blueprint('backup', __name__)

@bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Erstellt ein neues Backup"""
    try:
        payload = request.get_json(silent=True) or {}
        include_media = payload.get('include_media', True)
        
        filename = simple_backup.create_backup(include_media=include_media)
        
        if filename:
            return jsonify({
                'success': True,
                'message': 'Backup erfolgreich erstellt',
                'filename': filename
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Backup fehlgeschlagen'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Erstellen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/list', methods=['GET'])
@login_required
@admin_required
def list_backups():
    """Listet alle verfügbaren Backups auf"""
    try:
        backups = simple_backup.list_backups()
        return jsonify({
            'success': True,
            'backups': backups
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Auflisten der Backups: [Interner Fehler]'
        }), 500

@bp.route('/restore', methods=['POST'])
@login_required
@admin_required
def restore_backup():
    """Stellt ein Backup wieder her"""
    try:
        payload = request.get_json(silent=True) or {}
        filename = payload.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'message': 'Backup-Dateiname erforderlich'
            }), 400
        
        success, message = simple_backup.restore_backup(filename)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Wiederherstellen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/download/<filename>', methods=['GET'])
@login_required
@admin_required
def download_backup(filename):
    """Lädt ein Backup herunter"""
    try:
        filename = secure_filename(filename)
        backup_path = simple_backup.backup_dir / filename
        
        if not backup_path.exists():
            return jsonify({
                'success': False,
                'message': 'Backup nicht gefunden'
            }), 404
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Herunterladen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/delete/<filename>', methods=['DELETE'])
@login_required
@admin_required
def delete_backup(filename):
    """Löscht ein Backup"""
    try:
        filename = secure_filename(filename)
        if simple_backup.delete_backup(filename):
            return jsonify({
                'success': True,
                'message': 'Backup erfolgreich gelöscht'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Backup nicht gefunden'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/upload', methods=['POST'])
@login_required
@admin_required
def upload_backup():
    """Lädt ein Backup hoch"""
    try:
        if 'backup_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Keine Datei hochgeladen'
            }), 400
        
        file = request.files['backup_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'Keine Datei ausgewählt'
            }), 400
        
        filename = secure_filename(file.filename)
        backup_path = simple_backup.backup_dir / filename
        file.save(backup_path)

        return jsonify({
            'success': True,
            'message': 'Backup erfolgreich hochgeladen',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Hochladen des Backups: [Interner Fehler]'
        }), 500
