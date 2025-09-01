#!/usr/bin/env python3
"""
Backup-Routen für das vereinheitlichte Backup-System
"""

import os
import json
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest

from app.utils.unified_backup_manager import unified_backup_manager
from app.utils.decorators import admin_required

bp = Blueprint('backup', __name__, url_prefix='/backup')

@bp.route('/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """
    🚀 Erstellt ein neues optimiertes Backup mit Fortschritts-Tracking
    """
    try:
        # Parameter aus Request
        include_media = request.json.get('include_media', True)
        compress = request.json.get('compress', True)

        # Fortschritts-Callback für WebSocket oder Response
        progress_updates = []

        def progress_callback(message: str, percentage: int):
            """Sammelt Fortschritts-Updates"""
            progress_updates.append({
                'message': message,
                'percentage': percentage,
                'timestamp': datetime.now().isoformat()
            })
            # Hier könnte man WebSocket-Updates senden
            print(f"📊 Backup-Fortschritt: {percentage}% - {message}")

        # 🚀 Optimiertes Backup erstellen
        backup_filename = unified_backup_manager.create_backup(
            include_media=include_media,
            compress=compress,
            progress_callback=progress_callback
        )

        if backup_filename:
            return jsonify({
                'success': True,
                'message': '🚀 Optimiertes Backup erfolgreich erstellt',
                'filename': backup_filename,
                'progress': progress_updates,
                'optimized': True,
                'parallel_processing': True
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Backup fehlgeschlagen',
                'progress': progress_updates
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Erstellen des optimierten Backups: {str(e)}'
        }), 500

@bp.route('/list', methods=['GET'])
@login_required
@admin_required
def list_backups():
    """Listet alle verfügbaren Backups auf"""
    try:
        backups = unified_backup_manager.list_backups()
        
        return jsonify({
            'success': True,
            'backups': backups
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Auflisten der Backups: {str(e)}'
        }), 500

@bp.route('/restore', methods=['POST'])
@login_required
@admin_required
def restore_backup():
    """Stellt ein Backup wieder her"""
    try:
        backup_filename = request.json.get('filename')
        include_media = request.json.get('include_media', True)
        
        if not backup_filename:
            return jsonify({
                'success': False,
                'message': 'Backup-Dateiname erforderlich'
            }), 400
        
        # Backup wiederherstellen
        success = unified_backup_manager.restore_backup(
            backup_filename,
            include_media=include_media
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Backup erfolgreich wiederhergestellt'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Backup-Wiederherstellung fehlgeschlagen'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Wiederherstellen des Backups: {str(e)}'
        }), 500

@bp.route('/download/<filename>', methods=['GET'])
@login_required
@admin_required
def download_backup(filename):
    """Lädt ein Backup herunter"""
    try:
        backup_path = Path('backups') / secure_filename(filename)
        
        if not backup_path.exists():
            return jsonify({
                'success': False,
                'message': 'Backup nicht gefunden'
            }), 404
        
        # Bestimme MIME-Type basierend auf Dateiendung
        if filename.endswith('.zip'):
            mimetype = 'application/zip'
        elif filename.endswith('.json'):
            mimetype = 'application/json'
        else:
            mimetype = 'application/octet-stream'
        
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Herunterladen des Backups: {str(e)}'
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
        
        # Datei speichern
        filename = secure_filename(file.filename)
        backup_path = Path('backups') / filename
        
        file.save(backup_path)
        
        return jsonify({
            'success': True,
            'message': 'Backup erfolgreich hochgeladen',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Hochladen des Backups: {str(e)}'
        }), 500

@bp.route('/import-json', methods=['POST'])
@login_required
@admin_required
def import_json_backup():
    """Importiert ein JSON-Backup"""
    try:
        if 'json_file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'Keine JSON-Datei hochgeladen'
            }), 400
        
        file = request.files['json_file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'Keine Datei ausgewählt'
            }), 400
        
        # Temporäre Datei speichern
        temp_dir = Path('temp')
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / secure_filename(file.filename)
        
        file.save(temp_path)
        
        try:
            # JSON-Backup importieren
            success = unified_backup_manager.import_json_backup(str(temp_path))
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'JSON-Backup erfolgreich importiert'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'JSON-Backup-Import fehlgeschlagen'
                }), 500
                
        finally:
            # Temporäre Datei löschen
            if temp_path.exists():
                temp_path.unlink()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Importieren des JSON-Backups: {str(e)}'
        }), 500

@bp.route('/delete/<filename>', methods=['DELETE'])
@login_required
@admin_required
def delete_backup(filename):
    """Löscht ein Backup"""
    try:
        backup_path = Path('backups') / secure_filename(filename)
        
        if not backup_path.exists():
            return jsonify({
                'success': False,
                'message': 'Backup nicht gefunden'
            }), 404
        
        backup_path.unlink()
        
        return jsonify({
            'success': True,
            'message': 'Backup erfolgreich gelöscht'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen des Backups: {str(e)}'
        }), 500

@bp.route('/test/<filename>', methods=['GET'])
@login_required
@admin_required
def test_backup(filename):
    """Testet ein Backup"""
    try:
        backup_path = Path('backups') / secure_filename(filename)
        
        if not backup_path.exists():
            return jsonify({
                'success': False,
                'message': 'Backup nicht gefunden'
            }), 404
        
        # Backup testen
        import zipfile
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            # Metadaten prüfen
            metadata = None
            if 'backup_metadata.json' in zipf.namelist():
                metadata_content = zipf.read('backup_metadata.json')
                metadata = json.loads(metadata_content.decode('utf-8'))
            
            # Struktur prüfen
            files = zipf.namelist()
            structure = {
                'has_mongodb': any(f.startswith('mongodb/') for f in files),
                'has_media': any(f.startswith('media/') for f in files),
                'has_config': any(f.startswith('config/') for f in files),
                'has_metadata': metadata is not None
            }
            
            return jsonify({
                'success': True,
                'valid': True,
                'metadata': metadata,
                'structure': structure,
                'size': backup_path.stat().st_size
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'valid': False,
            'message': f'Backup ist beschädigt: {str(e)}'
        }), 500

@bp.route('/info', methods=['GET'])
@login_required
@admin_required
def backup_info():
    """Gibt Informationen über das Backup-System zurück"""
    try:
        backup_dir = Path('backups')
        total_size = sum(f.stat().st_size for f in backup_dir.glob('*.zip'))
        
        # Medien-Verzeichnisse prüfen
        media_dirs = [
            Path("app/static/uploads"),
            Path("app/uploads"),
            Path("uploads")
        ]
        
        media_size = 0
        media_files = 0
        for media_dir in media_dirs:
            if media_dir.exists():
                for root, dirs, files in os.walk(media_dir):
                    for file in files:
                        file_path = Path(root) / file
                        media_size += file_path.stat().st_size
                        media_files += 1
                break
        
        return jsonify({
            'success': True,
            'info': {
                'backup_count': len(list(backup_dir.glob('*.zip'))),
                'total_backup_size': unified_backup_manager._format_size(total_size),
                'media_files': media_files,
                'media_size': unified_backup_manager._format_size(media_size),
                'max_backup_size_gb': unified_backup_manager.max_backup_size_gb,
                'include_media': unified_backup_manager.include_media,
                'compress_backups': unified_backup_manager.compress_backups
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Fehler beim Abrufen der Backup-Informationen: {str(e)}'
        }), 500 