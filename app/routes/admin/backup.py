from .blueprint import bp
from .shared import *
@bp.route('/backup/list')
@mitarbeiter_required
def backup_list():
    """Gibt eine Liste der verfügbaren Backups zurück (alle Formate)"""
    try:
        from app.utils.unified_backup_manager import unified_backup_manager
        from app.services.admin_backup_service import AdminBackupService

        # Hole neue ZIP-Backups
        zip_backups = unified_backup_manager.list_backups()

        # Hole alte JSON-Backups
        json_backups = AdminBackupService.get_backup_list()

        # Hole native Backups
        native_backups = AdminBackupService.get_native_backup_list()

        # Konvertiere ZIP-Backups in das erwartete Format
        converted_zip_backups = []
        for backup in zip_backups:
            try:
                # Parse created_at String zu Timestamp
                from datetime import datetime
                created_at = backup.get('created_at', '')
                if created_at and created_at != 'Unbekannt':
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_timestamp = dt.timestamp()
                else:
                    created_timestamp = 0

                # Hole tatsächliche Dateigröße
                backup_path = backup_manager.backup_dir / backup['filename']
                file_size = backup_path.stat().st_size if backup_path.exists() else 0

                converted_zip_backups.append({
                    'name': backup['filename'],
                    'size': file_size,  # Numerische Größe in Bytes
                    'created': created_timestamp,
                    'type': 'zip',
                    'includes_media': backup.get('includes_media', False),
                    'version': backup.get('version', '2.0')
                })
            except Exception as e:
                logger.error(f"Fehler beim Konvertieren von ZIP-Backup {backup}: {e}")
                continue

        # Kombiniere alle Backups
        all_backups = converted_zip_backups + json_backups + native_backups

        # Sortiere nach Erstellungsdatum (neueste zuerst)
        all_backups.sort(key=lambda x: x.get('created', 0), reverse=True)

        return jsonify({
            'status': 'success',
            'backups': all_backups,
            'zip_count': len(converted_zip_backups),
            'json_count': len(json_backups),
            'native_count': len(native_backups),
            'total_count': len(all_backups)
        })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Backups: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Laden der Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Erstellt ein neues Backup der aktuellen Datenbank"""
    try:
        success, message, backup_filename = AdminBackupService.create_backup()

        if success:
            # E-Mail-Versand (optional)
            email_recipient = request.form.get('email_recipient', '').strip()
            if email_recipient and backup_filename:
                try:
                    from app.utils.email_utils import send_backup_mail
                    from app.utils.backup_manager import backup_manager
                    backup_path = backup_manager.get_backup_path(backup_filename)
                    send_backup_mail(email_recipient, str(backup_path))
                    return jsonify({
                        'status': 'success',
                        'message': f'{message} und an {email_recipient} gesendet',
                        'filename': backup_filename
                    })
                except Exception as e:
                    logger.error(f"Fehler beim E-Mail-Versand: {str(e)}")
                    return jsonify({
                        'status': 'success',
                        'message': f'{message}, aber E-Mail-Versand fehlgeschlagen',
                        'filename': backup_filename
                    })
            else:
                return jsonify({
                    'status': 'success',
                    'message': message,
                    'filename': backup_filename
                })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 500

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Erstellen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/upload', methods=['POST'])
@admin_required
def upload_backup():
    """Lädt ein Backup hoch und stellt es wieder her"""
    try:
        if 'backup_file' not in request.files:
            logger.warning("Backup-Upload: Keine Datei in request.files gefunden")
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400

        file = request.files['backup_file']
        if file.filename == '':
            logger.warning("Backup-Upload: Leerer Dateiname")
            return jsonify({
                'status': 'error',
                'message': 'Keine Datei ausgewählt'
            }), 400

        # Prüfe Dateityp - unterstütze ZIP und JSON Backups
        file_extension = Path(file.filename).suffix.lower()

        if file_extension not in ['.zip', '.json']:
            logger.warning(f"Backup-Upload: Ungültiger Dateityp: {file.filename}")
            return jsonify({
                'status': 'error',
                'message': 'Nur ZIP- und JSON-Backups sind erlaubt'
            }), 400

        # Prüfe Dateigröße
        file.seek(0, 2)  # Gehe zum Ende der Datei
        file_size = file.tell()
        file.seek(0)  # Zurück zum Anfang

        logger.info(f"Backup-Upload: Datei {file.filename}, Größe: {file_size} bytes")

        if file_size == 0:
            logger.warning("Backup-Upload: Datei ist leer")
            return jsonify({
                'status': 'error',
                'message': 'Die hochgeladene Datei ist leer. Bitte wählen Sie eine gültige Backup-Datei aus.'
            }), 400

        # Direkt ins Backup-Verzeichnis speichern
        backup_filename = secure_filename(file.filename)
        backup_path = Path('backups') / backup_filename

        # Backup-Verzeichnis erstellen falls nicht vorhanden
        backup_path.parent.mkdir(exist_ok=True)

        # Datei direkt ins Backup-Verzeichnis speichern
        file.save(backup_path)

        try:
            if file_extension == '.zip':
                # ZIP-Backup über vereinheitlichtes System
                from app.utils.unified_backup_manager import unified_backup_manager
                success = unified_backup_manager.restore_backup(backup_filename)

                if success:
                    logger.info("Backup-Upload: ZIP-Backup erfolgreich wiederhergestellt")
                    return jsonify({
                        'status': 'success',
                        'message': f'ZIP-Backup erfolgreich hochgeladen und wiederhergestellt: {file.filename}'
                    })
                else:
                    logger.error("Backup-Upload: Fehler beim Wiederherstellen des ZIP-Backups")
                    return jsonify({
                        'status': 'error',
                        'message': f'Fehler beim Wiederherstellen des ZIP-Backups: {file.filename}'
                    }), 500
            elif file_extension == '.json':
                # JSON-Backup über BackupService
                from app.services.backup_service import BackupService
                backup_service = BackupService()
                success, message = backup_service._restore_from_json(str(backup_path))

                if success:
                    logger.info("Backup-Upload: JSON-Backup erfolgreich wiederhergestellt")
                    return jsonify({
                        'status': 'success',
                        'message': f'JSON-Backup erfolgreich hochgeladen und wiederhergestellt: {file.filename}'
                    })
                else:
                    logger.error("Backup-Upload: Fehler beim Wiederherstellen des JSON-Backups")
                    return jsonify({
                        'status': 'error',
                        'message': f'Fehler beim Wiederherstellen des JSON-Backups: {message}'
                    }), 500

        except Exception as e:
            # Bei Fehler das fehlerhafte Backup löschen
            if backup_path.exists():
                backup_path.unlink()
            raise e

    except Exception as e:
        logger.error(f"Fehler beim Hochladen des Backups: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Hochladen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/restore/<filename>', methods=['POST'])
@admin_required
def restore_backup(filename):
    """Stellt ein Backup wieder her (automatische Erkennung JSON/Native)"""
    try:
        from app.services.admin_backup_service import AdminBackupService
        from app.utils.backup_manager import backup_manager

        # Prüfe Backup-Typ
        backup_path = backup_manager.backup_dir / filename
        is_native = backup_path.is_dir() and filename.startswith('scandy_native_backup_')
        is_zip = backup_path.is_file() and filename.endswith('.zip')

        if is_zip:
            # Verwende vereinheitlichtes ZIP-Restore
            from app.utils.unified_backup_manager import unified_backup_manager
            success = unified_backup_manager.restore_backup(filename)
            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'ZIP-Backup erfolgreich wiederhergestellt: {filename}',
                    'backup_type': 'zip'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Fehler beim Wiederherstellen des ZIP-Backups: {filename}',
                    'backup_type': 'zip'
                }), 500
        elif is_native:
            # Verwende native Restore
            success, message = AdminBackupService.restore_native_backup(filename)
            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Native Backup wiederhergestellt: {message}',
                    'backup_type': 'native'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Fehler beim Wiederherstellen des nativen Backups: {message}',
                    'backup_type': 'native'
                }), 500
        else:
            # Verwende JSON Restore
            success, message, validation_info = AdminBackupService.restore_backup(filename)
            if success:
                return jsonify({
                    'status': 'success',
                    'message': message,
                    'validation_info': validation_info,
                    'backup_type': 'json'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'message': message,
                    'backup_type': 'json'
                }), 500

    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Wiederherstellen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/download/<filename>')
@admin_required
def download_backup(filename):
    """Lädt ein Backup herunter (JSON oder Native als ZIP)"""
    try:
        from pathlib import Path
        from app.utils.backup_manager import backup_manager
        import zipfile
        import tempfile
        import os

        backup_path = backup_manager.backup_dir / filename

        if not backup_path.exists():
            return jsonify({
                'status': 'error',
                'message': 'Backup nicht gefunden'
            }), 404

        # Prüfe Backup-Typ
        is_native = backup_path.is_dir() and filename.startswith('scandy_native_backup_')
        is_zip = backup_path.is_file() and filename.endswith('.zip')

        if is_zip:
            # ZIP Backup - direkt senden
            return send_file(
                backup_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/zip'
            )
        elif is_native:
            # Native Backup (Verzeichnis) - erstelle ZIP
            try:
                # Erstelle temporäres ZIP
                temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
                temp_zip.close()

                with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Füge alle Dateien im Backup-Verzeichnis zum ZIP hinzu
                    for root, dirs, files in os.walk(backup_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, backup_path)
                            zipf.write(file_path, arcname)

                # Sende ZIP-Datei
                return send_file(
                    temp_zip.name,
                    as_attachment=True,
                    download_name=f"{filename}.zip",
                    mimetype='application/zip'
                )

            except Exception as e:
                # Lösche temporäre Datei bei Fehler
                if os.path.exists(temp_zip.name):
                    os.unlink(temp_zip.name)
                raise e

        else:
            # JSON Backup (Datei) - direkt senden
            return send_file(
                backup_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/json'
            )

    except Exception as e:
        logger.error(f"Fehler beim Herunterladen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Herunterladen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/test/<filename>')
@admin_required
def test_backup(filename):
    """Testet ein Backup ohne es wiederherzustellen"""
    try:
        success, result = AdminBackupService.test_backup(filename)

        if success:
            return jsonify({
                'status': 'success',
                'message': 'Backup-Test erfolgreich',
                'data': result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': result
            }), 400

    except Exception as e:
        logger.error(f"Fehler beim Testen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Testen des Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/create-json', methods=['POST'])
@admin_required
def create_json_backup():
    """Erstellt ein JSON-Backup (für Kompatibilität)"""
    try:
        from app.services.admin_backup_service import AdminBackupService

        success, message, backup_filename = AdminBackupService.create_json_backup()

        if success:
            return jsonify({
                'status': 'success',
                'message': f'JSON-Backup erfolgreich erstellt: {backup_filename}',
                'filename': backup_filename
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Fehler beim Erstellen des JSON-Backups: {message}'
            }), 500

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des JSON-Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Erstellen des JSON-Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/create-native', methods=['POST'])
@admin_required
def create_native_backup():
    """Erstellt ein natives MongoDB-Backup mit mongodump"""
    try:
        from app.services.admin_backup_service import AdminBackupService

        success, message, backup_filename = AdminBackupService.create_native_backup()

        if success:
            return jsonify({
                'status': 'success',
                'message': f'Native Backup erfolgreich erstellt: {backup_filename}',
                'filename': backup_filename
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Fehler beim Erstellen des nativen Backups: {message}'
            }), 500

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des nativen Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Erstellen des nativen Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/restore-native/<backup_name>', methods=['POST'])
@admin_required
def restore_native_backup(backup_name):
    """Stellt ein natives MongoDB-Backup mit mongorestore wieder her"""
    try:
        from app.services.admin_backup_service import AdminBackupService

        success, message = AdminBackupService.restore_native_backup(backup_name)

        if success:
            return jsonify({
                'status': 'success',
                'message': f'Native Backup erfolgreich wiederhergestellt: {backup_name}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Fehler beim Wiederherstellen des nativen Backups: {message}'
            }), 500

    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen des nativen Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Wiederherstellen des nativen Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/create-hybrid', methods=['POST'])
@admin_required
def create_hybrid_backup():
    """Erstellt ein hybrides Backup (Native + JSON)"""
    try:
        from app.services.admin_backup_service import AdminBackupService

        success, message, result = AdminBackupService.create_hybrid_backup()

        if success:
            return jsonify({
                'status': 'success',
                'message': f'Hybrides Backup erfolgreich erstellt: {message}',
                'result': result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Fehler beim Erstellen des hybriden Backups: {message}'
            }), 500

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des hybriden Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Erstellen des hybriden Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/convert-old/<filename>', methods=['POST'])
@admin_required
def convert_old_backup(filename):
    """Konvertiert ein altes Backup in das neue Format"""
    try:
        from app.utils.backup_manager import backup_manager
        converted_filename = backup_manager.convert_old_backup(filename)

        if converted_filename:
            return jsonify({
                'status': 'success',
                'message': f'Backup erfolgreich konvertiert: {converted_filename}',
                'converted_filename': converted_filename
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Fehler beim Konvertieren des Backups'
            }), 500

    except Exception as e:
        logger.error(f"Fehler beim Konvertieren des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Konvertieren des Backups: [Interner Fehler]'
        }), 500

@bp.route('/backup/convert-all-old', methods=['POST'])
@admin_required
def convert_all_old_backups():
    """Konvertiert alle alten Backups automatisch"""
    try:
        from app.utils.backup_manager import backup_manager
        converted_backups = backup_manager.convert_all_old_backups()

        return jsonify({
            'status': 'success',
            'message': f'{len(converted_backups)} Backups erfolgreich konvertiert',
            'converted_backups': converted_backups
        })

    except Exception as e:
        logger.error(f"Fehler bei der Massenkonvertierung: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler bei der Massenkonvertierung: [Interner Fehler]'
        }), 500

@bp.route('/backup/list-old', methods=['GET'])
@admin_required
def list_old_backups():
    """Listet alle Backups auf, die noch im alten Format sind"""
    try:
        from app.utils.backup_manager import backup_manager
        old_backups = backup_manager.list_old_backups()

        return jsonify({
            'status': 'success',
            'old_backups': old_backups,
            'count': len(old_backups)
        })

    except Exception as e:
        logger.error(f"Fehler beim Auflisten alter Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Auflisten alter Backups: [Interner Fehler]'
        }), 500

@bp.route('/debug/backup-info')
@login_required
def debug_backup_info():
    """Debug-Route für Backup-Informationen"""
    try:
        # Verwende den AdminDebugService
        backup_info = AdminDebugService.debug_backup_info()
        return jsonify(backup_info)
    except Exception as e:
        return jsonify({
            'error': 'Ein interner Fehler ist aufgetreten.',
            'traceback': str(e.__traceback__)
        }), 500

@bp.route('/import_all_data', methods=['POST'])
@admin_required
def import_all_data():
    """Importiert Daten aus einer Excel-Datei"""
    try:
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('admin.system'))

        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('admin.system'))

        if not file.filename.endswith('.xlsx'):
            flash('Nur Excel-Dateien (.xlsx) werden unterstützt', 'error')
            return redirect(url_for('admin.system'))

        # Speichere temporäre Datei
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            file.save(tmp_file.name)
            tmp_file_path = tmp_file.name

        try:
            # Lese Excel-Datei
            import pandas as pd

            # Lese alle Arbeitsblätter
            excel_file = pd.ExcelFile(tmp_file_path)

            imported_count = 0
            errors = []

            # Importiere Werkzeuge
            if 'Werkzeuge' in excel_file.sheet_names:
                try:
                    df_tools = pd.read_excel(excel_file, sheet_name='Werkzeuge')
                    for index, row in df_tools.iterrows():
                        try:
                            tool_data = row.to_dict()
                            tool_data = fix_id_for_import(tool_data)

                            # Prüfe ob Barcode vorhanden ist
                            if not tool_data.get('barcode'):
                                errors.append(f"Zeile {index + 2}: Werkzeug ohne Barcode übersprungen")
                                continue

                            existing = mongodb.find_one('tools', {'barcode': tool_data.get('barcode')})
                            if not existing:
                                mongodb.insert_one('tools', tool_data)
                                imported_count += 1
                            else:
                                # Update existierendes Werkzeug
                                mongodb.update_one('tools', {'barcode': tool_data.get('barcode')}, {'$set': tool_data})
                                imported_count += 1
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Werkzeug: [Interner Fehler]")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Werkzeuge-Tabelle: [Interner Fehler]")

            # Importiere Mitarbeiter
            if 'Mitarbeiter' in excel_file.sheet_names:
                try:
                    df_workers = pd.read_excel(excel_file, sheet_name='Mitarbeiter')
                    for index, row in df_workers.iterrows():
                        try:
                            worker_data = row.to_dict()
                            worker_data = fix_id_for_import(worker_data)

                            # Prüfe ob Barcode vorhanden ist
                            if not worker_data.get('barcode'):
                                errors.append(f"Zeile {index + 2}: Mitarbeiter ohne Barcode übersprungen")
                                continue

                            existing = mongodb.find_one('workers', {'barcode': worker_data.get('barcode')})
                            if not existing:
                                mongodb.insert_one('workers', worker_data)
                                imported_count += 1
                            else:
                                # Update existierenden Mitarbeiter
                                mongodb.update_one('workers', {'barcode': worker_data.get('barcode')}, {'$set': worker_data})
                                imported_count += 1
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Mitarbeiter: [Interner Fehler]")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Mitarbeiter-Tabelle: [Interner Fehler]")

            # Importiere Verbrauchsmaterial
            if 'Verbrauchsmaterial' in excel_file.sheet_names:
                try:
                    df_consumables = pd.read_excel(excel_file, sheet_name='Verbrauchsmaterial')
                    for index, row in df_consumables.iterrows():
                        try:
                            consumable_data = row.to_dict()
                            consumable_data = fix_id_for_import(consumable_data)

                            # Prüfe ob Barcode vorhanden ist
                            if not consumable_data.get('barcode'):
                                errors.append(f"Zeile {index + 2}: Verbrauchsmaterial ohne Barcode übersprungen")
                                continue

                            existing = mongodb.find_one('consumables', {'barcode': consumable_data.get('barcode')})
                            if not existing:
                                mongodb.insert_one('consumables', consumable_data)
                                imported_count += 1
                            else:
                                # Update existierendes Verbrauchsmaterial
                                mongodb.update_one('consumables', {'barcode': consumable_data.get('barcode')}, {'$set': consumable_data})
                                imported_count += 1
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Verbrauchsmaterial: [Interner Fehler]")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Verbrauchsmaterial-Tabelle: [Interner Fehler]")

            # Importiere Settings (Kategorien, Standorte, Abteilungen)
            if 'Settings' in excel_file.sheet_names:
                try:
                    df_settings = pd.read_excel(excel_file, sheet_name='Settings')
                    for index, row in df_settings.iterrows():
                        try:
                            setting_data = row.to_dict()
                            setting_data = fix_id_for_import(setting_data)
                            valid_settings = ['categories', 'locations', 'departments', 'ticket_categories',
                                            'label_tools_name', 'label_tools_icon', 'label_consumables_name',
                                            'label_consumables_icon', 'label_tickets_name', 'label_tickets_icon']

                            if setting_data.get('key') in valid_settings:
                                existing = mongodb.find_one('settings', {'key': setting_data.get('key')})
                                if not existing:
                                    mongodb.insert_one('settings', setting_data)
                                    imported_count += 1
                                else:
                                    mongodb.update_one('settings',
                                                     {'key': setting_data.get('key')},
                                                     {'$set': setting_data})
                                    imported_count += 1
                            else:
                                errors.append(f"Zeile {index + 2}: Ungültige Setting '{setting_data.get('key')}' übersprungen")
                        except Exception as e:
                            errors.append(f"Zeile {index + 2}: Fehler bei Setting: [Interner Fehler]")
                except Exception as e:
                    errors.append(f"Fehler beim Lesen der Settings-Tabelle: [Interner Fehler]")

            # Zeige Erfolgsmeldung und eventuelle Fehler
            if errors:
                error_message = f'{imported_count} Datensätze importiert. {len(errors)} Fehler aufgetreten: ' + '; '.join(errors[:5])
                if len(errors) > 5:
                    error_message += f'... und {len(errors) - 5} weitere'
                flash(error_message, 'warning')
            else:
                flash(f'{imported_count} Datensätze erfolgreich importiert', 'success')

        finally:
            os.unlink(tmp_file_path)

        return redirect(url_for('admin.system'))

    except Exception as e:
        logger.error(f"Fehler beim Importieren der Daten: {str(e)}")
        flash(f'Fehler beim Importieren: [Interner Fehler]', 'error')
        return redirect(url_for('admin.system'))

@bp.route('/backup/auto/status')
@login_required
@admin_required
def auto_backup_status():
    """Gibt den Status des automatischen Backup-Systems zurück"""
    try:
        from app.utils.auto_backup import get_auto_backup_status
        status = get_auto_backup_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen des Auto-Backup-Status: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Abrufen des Status: [Interner Fehler]'
        })

@bp.route('/backup/auto/start', methods=['POST'])
@login_required
@admin_required
def start_auto_backup():
    """Startet das automatische Backup-System"""
    try:
        from app.utils.auto_backup import start_auto_backup
        start_auto_backup()
        return jsonify({
            'success': True,
            'message': 'Automatisches Backup-System gestartet'
        })
    except Exception as e:
        logger.error(f"Fehler beim Starten des Auto-Backup-Systems: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Starten: [Interner Fehler]'
        })

@bp.route('/backup/auto/stop', methods=['POST'])
@login_required
@admin_required
def stop_auto_backup():
    """Stoppt das automatische Backup-System"""
    try:
        from app.utils.auto_backup import stop_auto_backup
        stop_auto_backup()
        return jsonify({
            'success': True,
            'message': 'Automatisches Backup-System gestoppt'
        })
    except Exception as e:
        logger.error(f"Fehler beim Stoppen des Auto-Backup-Systems: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Stoppen: [Interner Fehler]'
        })

@bp.route('/backup/auto/logs')
@login_required
@admin_required
def auto_backup_logs():
    """Gibt die Auto-Backup-Logs zurück"""
    try:
        from app.utils.auto_backup import auto_backup_scheduler
        log_file = auto_backup_scheduler.log_file

        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()
            # Letzte 50 Zeilen
            recent_logs = logs[-50:] if len(logs) > 50 else logs
            return jsonify({
                'success': True,
                'logs': recent_logs
            })
        else:
            return jsonify({
                'success': True,
                'logs': ['Keine Logs verfügbar']
            })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Auto-Backup-Logs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Abrufen der Logs: [Interner Fehler]'
        })

@bp.route('/auto-backup', methods=['GET', 'POST'])
@login_required
@admin_required
def auto_backup():
    """Automatisches Backup-System Verwaltungsseite"""
    try:
        from app.utils.auto_backup import auto_backup_scheduler

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'save_times':
                # Backup-Zeiten speichern
                times_input = request.form.get('backup_times', '')
                times_list = [t.strip() for t in times_input.split(',') if t.strip()]

                success, message = auto_backup_scheduler.save_backup_times(times_list)

                if success:
                    flash('Backup-Zeiten erfolgreich gespeichert.', 'success')
                else:
                    flash(f'Fehler beim Speichern der Backup-Zeiten: {message}', 'error')

            elif action == 'save_weekly_time':
                # Wöchentliche Backup-Zeit speichern
                weekly_time = request.form.get('weekly_backup_time', '').strip()

                success, message = auto_backup_scheduler.save_weekly_backup_time(weekly_time)

                if success:
                    flash('Wöchentliche Backup-Zeit erfolgreich gespeichert.', 'success')
                else:
                    flash(f'Fehler beim Speichern der wöchentlichen Backup-Zeit: {message}', 'error')

            elif action == 'save_weekly_email':
                # E-Mail für wöchentliche Backups speichern
                weekly_email = request.form.get('weekly_backup_email', '').strip()

                if weekly_email and '@' in weekly_email:
                    try:
                        from app.models.mongodb_database import mongodb
                        mongodb.update_one('settings',
                                         {'key': 'weekly_backup_email'},
                                         {'$set': {'value': weekly_email}},
                                         upsert=True)
                        flash('E-Mail-Adresse für wöchentliche Backups erfolgreich gespeichert.', 'success')
                    except Exception as e:
                        logger.error(f"Fehler beim Speichern der wöchentlichen Backup-E-Mail: {e}")
                        flash(f'Fehler beim Speichern der E-Mail-Adresse: [Interner Fehler]', 'error')
                else:
                    flash('Bitte geben Sie eine gültige E-Mail-Adresse ein.', 'error')

        # Lade aktuelle Einstellungen
        current_times = auto_backup_scheduler.get_backup_times()
        current_weekly_time = auto_backup_scheduler.get_weekly_backup_time()
        current_weekly_email = auto_backup_scheduler._get_weekly_backup_email()

        return render_template('admin/auto_backup.html',
                             backup_times=current_times,
                             weekly_backup_time=current_weekly_time,
                             weekly_backup_email=current_weekly_email)

    except Exception as e:
        logger.error(f"Fehler bei Auto-Backup-Einstellungen: {e}")
        flash('Fehler beim Laden der Auto-Backup-Einstellungen.', 'error')
        return render_template('admin/auto_backup.html',
                             backup_times=['06:00', '18:00'],
                             weekly_backup_time='17:00',
                             weekly_backup_email='')

@bp.route('/backup/weekly/test', methods=['POST'])
@login_required
@admin_required
def test_weekly_backup():
    """Sendet das wöchentliche Backup-Archiv manuell"""
    try:
        from app.utils.auto_backup import auto_backup_scheduler

        # Führe wöchentliches Backup-Archiv manuell aus
        auto_backup_scheduler._create_weekly_backup_archive()

        return jsonify({
            'success': True,
            'message': 'Backup-Archiv erfolgreich erstellt, versendet und ZIP-Datei gelöscht'
        })
    except Exception as e:
        logger.error(f"Fehler beim Versenden des Backup-Archivs: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Versenden: [Interner Fehler]'
        })

@bp.route('/backup/import_json', methods=['GET', 'POST'])
@login_required
@admin_required
def import_json_backup_scoped():
    """Importiert ein altes JSON-Backup in eine benannte Abteilung."""
    try:
        if request.method == 'POST':
            dept_name = (request.form.get('department_name') or '').strip()
            file = request.files.get('backup_file')
            if not dept_name:
                flash('Bitte Abteilungsnamen angeben', 'error')
                return redirect(url_for('admin.import_json_backup_scoped'))
            if not file or file.filename == '':
                flash('Bitte eine JSON-Backup-Datei auswählen', 'error')
                return redirect(url_for('admin.import_json_backup_scoped'))
            if not file.filename.lower().endswith('.json'):
                flash('Ungültiges Dateiformat. Bitte eine .json Datei wählen', 'error')
                return redirect(url_for('admin.import_json_backup_scoped'))

            # Datei temporär speichern
            filename = secure_filename(file.filename)
            tmp_dir = tempfile.mkdtemp()
            tmp_path = os.path.join(tmp_dir, filename)
            file.save(tmp_path)

            # Import als Hintergrund-Job starten, um Timeouts zu vermeiden
            from app.utils.unified_backup_manager import unified_backup_manager
            job_id = unified_backup_manager.start_import_job(tmp_path, dept_name)

            # Abteilung in den Systemeinstellungen anlegen und Benutzerberechtigungen erweitern
            try:
                # Departments-Liste pflegen
                existing_depts_doc = mongodb.find_one('settings', {'key': 'departments'})
                if existing_depts_doc and isinstance(existing_depts_doc.get('value'), list):
                    if dept_name not in existing_depts_doc['value']:
                        new_list = existing_depts_doc['value'] + [dept_name]
                        mongodb.update_one('settings', {'_id': existing_depts_doc['_id']}, {'$set': {'value': new_list}})
                else:
                    mongodb.insert_one('settings', {'key': 'departments', 'value': [dept_name]})

                # Aktuellen Benutzer für die neue Abteilung berechtigen
                if hasattr(current_user, 'username'):
                    mongodb.update_one('users', {'username': current_user.username}, {'$addToSet': {'allowed_departments': dept_name}})
            except Exception as dep_e:
                logger.warning(f"Konnte Abteilung/Berechtigung nicht automatisch anlegen: {dep_e}")
            if not job_id:
                flash('Import konnte nicht gestartet werden.', 'error')
                return redirect(url_for('admin.import_json_backup_scoped'))

            # Weiterleitung auf Status-Seite
            return redirect(url_for('admin.import_json_backup_status', job_id=job_id))

        return render_template('admin/import_json_backup.html')
    except Exception as e:
        logger.error(f"Fehler beim JSON-Import: {e}")
        flash('Fehler beim Import', 'error')
        return redirect(url_for('admin.import_json_backup_scoped'))

@bp.route('/backup/import_json/job/<job_id>.json', methods=['GET'])
@login_required
@admin_required
def import_json_backup_job_status(job_id: str):
    try:
        from app.utils.unified_backup_manager import unified_backup_manager
        job = unified_backup_manager.get_import_job(job_id)
        return jsonify(job)
    except Exception as e:
        return jsonify({'exists': False, 'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/backup/import_json/status/<job_id>', methods=['GET'])
@login_required
@admin_required
def import_json_backup_status(job_id: str):
    try:
        return render_template('admin/import_json_backup_status.html', job_id=job_id)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Status-Seite: {e}")
        flash('Fehler beim Laden des Status', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/debug/fix-backup-fields', methods=['GET', 'POST'])
@admin_required
def fix_backup_fields():
    """Korrigiert fehlende Felder in der Datenbank nach Backup-Restore"""
    try:
        from app.services.admin_backup_service import AdminBackupService

        # Führe die Korrektur aus
        fixed_count = AdminBackupService._fix_missing_created_at_fields()

        # Zusätzliche Korrekturen für Dashboard-Probleme
        dashboard_fixes = 0

        # Stelle sicher, dass alle Tools ein gültiges created_at Feld haben
        all_tools = mongodb.find('tools', {})
        for tool in all_tools:
            created_at = tool.get('created_at')
            if created_at is None:
                # Verwende updated_at oder aktuelles Datum
                fallback_date = tool.get('updated_at') or datetime.now()
                if isinstance(fallback_date, str):
                    try:
                        fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            fallback_date = datetime.now()

                mongodb.update_one('tools',
                                 {'_id': tool['_id']},
                                 {'$set': {'created_at': fallback_date}})
                dashboard_fixes += 1

        # Stelle sicher, dass alle Workers ein gültiges created_at Feld haben
        all_workers = mongodb.find('workers', {})
        for worker in all_workers:
            created_at = worker.get('created_at')
            if created_at is None:
                fallback_date = worker.get('updated_at') or datetime.now()
                if isinstance(fallback_date, str):
                    try:
                        fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            fallback_date = datetime.now()

                mongodb.update_one('workers',
                                 {'_id': worker['_id']},
                                 {'$set': {'created_at': fallback_date}})
                dashboard_fixes += 1

        total_fixes = fixed_count + dashboard_fixes

        return jsonify({
            'success': True,
            'message': f'{total_fixes} fehlende Felder wurden ergänzt (Backup-Service: {fixed_count}, Dashboard-Fixes: {dashboard_fixes})',
            'fixed_count': total_fixes,
            'backup_service_fixes': fixed_count,
            'dashboard_fixes': dashboard_fixes
        })

    except Exception as e:
        logger.error(f"Fehler beim Korrigieren der Backup-Felder: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Korrigieren: [Interner Fehler]'
        }), 500

@bp.route('/debug/test-backup-restore/<filename>', methods=['GET'])
@admin_required
def test_backup_restore(filename):
    """Testet die Backup-Wiederherstellung für eine spezifische Datei"""
    try:
        from app.utils.backup_manager import backup_manager

        # Prüfe ob die Datei existiert
        backup_path = backup_manager.backup_dir / filename
        if not backup_path.exists():
            return jsonify({
                'success': False,
                'message': f'Backup-Datei "{filename}" nicht gefunden',
                'backup_path': str(backup_path)
            })

        # Teste die Backup-Wiederherstellung ohne sie tatsächlich durchzuführen
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)

            # Validiere Backup-Daten
            is_valid, validation_message = backup_manager._validate_backup_data(backup_data)

            return jsonify({
                'success': True,
                'message': f'Backup "{filename}" ist gültig',
                'validation_message': validation_message,
                'collections': list(backup_data.keys()),
                'total_documents': sum(len(docs) for docs in backup_data.values()),
                'file_size': backup_path.stat().st_size
            })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Fehler beim Testen des Backups: [Interner Fehler]',
                'backup_path': str(backup_path)
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Unerwarteter Fehler: [Interner Fehler]'
        }), 500

@bp.route('/test/json-backups')
@admin_required
def test_json_backups():
    """Test-Route für JSON-Backups"""
    try:
        from app.services.admin_backup_service import AdminBackupService

        json_backups = AdminBackupService.get_backup_list()

        return jsonify({
            'status': 'success',
            'json_backups': json_backups,
            'count': len(json_backups)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Ein interner Fehler ist aufgetreten.'
        }), 500
