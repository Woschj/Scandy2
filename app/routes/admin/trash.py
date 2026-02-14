from .blueprint import bp
from .shared import *
@bp.route('/trash')
@mitarbeiter_required
def trash():
    """Zeigt den Papierkorb mit gelöschten Einträgen an"""
    try:
        # Gelöschte Werkzeuge
        tools = mongodb.find('tools', {'deleted': True}, sort=[('deleted_at', -1)])

        # Gelöschte Verbrauchsmaterialien
        consumables = mongodb.find('consumables', {'deleted': True}, sort=[('deleted_at', -1)])

        # Gelöschte Mitarbeiter
        workers = mongodb.find('workers', {'deleted': True}, sort=[('deleted_at', -1)])

        # Gelöschte Tickets
        tickets = mongodb.find('tickets', {'deleted': True}, sort=[('deleted_at', -1)])

        # Gelöschte Benutzer (global, nicht gescoped)
        deleted_users = mongodb.find('users', {'deleted': True}, sort=[('deleted_at', -1)])
        return render_template('admin/trash.html',
                           tools=tools,
                           consumables=consumables,
                           workers=workers,
                           tickets=tickets,
                           users=deleted_users)
    except Exception as e:
        logger.error(f"Fehler beim Laden des Papierkorbs: {str(e)}", exc_info=True)
        flash('Fehler beim Laden des Papierkorbs', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/trash/restore/<type>/<barcode>', methods=['POST'])
@mitarbeiter_required
def restore_item(type, barcode):
    """Stellt einen gelöschten Eintrag wieder her"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)

        if type == 'tool':
            # Prüfe ob das Werkzeug existiert
            tool = mongodb.find_one('tools', {'barcode': decoded_barcode, 'deleted': True})

            if not tool:
                return jsonify({
                    'success': False,
                    'message': 'Werkzeug nicht gefunden'
                }), 404

            # Stelle das Werkzeug wieder her
            mongodb.update_one('tools',
                             {'barcode': decoded_barcode},
                             {'$set': {'deleted': False, 'deleted_at': None}})

        elif type == 'consumable':
            # Prüfe ob das Verbrauchsmaterial existiert
            consumable = mongodb.find_one('consumables', {'barcode': decoded_barcode, 'deleted': True})

            if not consumable:
                return jsonify({
                    'success': False,
                    'message': 'Verbrauchsmaterial nicht gefunden'
                }), 404

            # Stelle das Verbrauchsmaterial wieder her
            mongodb.update_one('consumables',
                             {'barcode': decoded_barcode},
                             {'$set': {'deleted': False, 'deleted_at': None}})

        elif type == 'worker':
            # Prüfe ob der Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': decoded_barcode, 'deleted': True})

            if not worker:
                return jsonify({
                    'success': False,
                    'message': 'Mitarbeiter nicht gefunden'
                }), 404

            # Stelle den Mitarbeiter wieder her
            mongodb.update_one('workers',
                             {'barcode': decoded_barcode},
                             {'$set': {'deleted': False, 'deleted_at': None}})

        elif type == 'ticket':
            # Prüfe ob das Ticket existiert
            ticket = mongodb.find_one('tickets', {'_id': convert_id_for_query(decoded_barcode), 'deleted': True})

            if not ticket:
                return jsonify({
                    'success': False,
                    'message': 'Ticket nicht gefunden'
                }), 404

            # Stelle das Ticket wieder her
            mongodb.update_one('tickets',
                             {'_id': convert_id_for_query(decoded_barcode)},
                             {'$set': {'deleted': False, 'deleted_at': None}})
        elif type == 'user':
            # Benutzer wiederherstellen (global)
            try:
                from bson import ObjectId
                oid = ObjectId(decoded_barcode) if len(decoded_barcode) == 24 else decoded_barcode
            except Exception:
                oid = decoded_barcode
            user = mongodb.find_one('users', {'_id': oid, 'deleted': True})
            if not user:
                return jsonify({'success': False, 'message': 'Benutzer nicht gefunden'}), 404
            mongodb.update_one('users', {'_id': oid}, {'$set': {'deleted': False, 'deleted_at': None, 'is_active': True}})
        else:
            return jsonify({
                'success': False,
                'message': 'Ungültiger Typ'
            }), 400

        return jsonify({
            'success': True,
            'message': 'Eintrag wurde wiederhergestellt'
        })

    except Exception as e:
        logger.error(f"Fehler beim Wiederherstellen des Eintrags: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Wiederherstellen: {str(e)}'
        }), 500

@bp.route('/tools/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_tool_soft_json():
    """Werkzeug soft löschen (markieren als gelöscht) - Barcode aus JSON-Body"""
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400

        barcode = data['barcode'].strip()  # Barcode bereinigen
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode zu lang (max. 50 Zeichen)'}), 400

        # Prüfe ob das Werkzeug existiert
        tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}})

        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404

        # Prüfe ob das Werkzeug ausgeliehen ist
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': barcode,
            'returned_at': None
        })

        if active_lending:
            return jsonify({
                'success': False,
                'message': 'Werkzeug ist noch ausgeliehen und kann nicht gelöscht werden'
            }), 400

        # Führe das Soft-Delete durch
        mongodb.update_one('tools', {'barcode': barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })

        return jsonify({
            'success': True,
            'message': 'Werkzeug wurde erfolgreich gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/tools/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_tool_soft(barcode):
    """Werkzeug soft löschen (markieren als gelöscht) - Barcode aus URL (Legacy)"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)

        # Prüfe ob das Werkzeug existiert
        tool = mongodb.find_one('tools', {'barcode': decoded_barcode, 'deleted': {'$ne': True}})

        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden'
            }), 404

        # Prüfe ob das Werkzeug ausgeliehen ist
        active_lending = mongodb.find_one('lendings', {
            'tool_barcode': decoded_barcode,
            'returned_at': None
        })

        if active_lending:
            return jsonify({
                'success': False,
                'message': 'Werkzeug ist noch ausgeliehen und kann nicht gelöscht werden'
            }), 400

        # Führe das Soft-Delete durch
        mongodb.update_one('tools', {'barcode': decoded_barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })

        return jsonify({
            'success': True,
            'message': 'Werkzeug wurde erfolgreich gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/tools/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_tool_permanent(barcode):
    """Werkzeug endgültig löschen"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)

        # Prüfe ob das Werkzeug existiert und gelöscht ist
        tool = mongodb.find_one('tools', {'barcode': decoded_barcode, 'deleted': True})

        if not tool:
            return jsonify({
                'success': False,
                'message': 'Werkzeug nicht gefunden oder nicht gelöscht'
            }), 404

        # Lösche das Werkzeug endgültig
        mongodb.delete_one('tools', {'barcode': decoded_barcode})

        return jsonify({
            'success': True,
            'message': 'Werkzeug wurde endgültig gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim endgültigen Löschen des Werkzeugs: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/consumables/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_consumable_soft():
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400

        barcode = data['barcode'].strip()  # Barcode bereinigen
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode zu lang (max. 50 Zeichen)'}), 400

        # Prüfe ob das Verbrauchsmaterial existiert
        consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden'}), 404

        # Führe das Soft-Delete durch
        mongodb.update_one('consumables', {'barcode': barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial erfolgreich gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Verbrauchsmaterials: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/consumables/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_consumable_permanent(barcode):
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)

        # Prüfe ob das Verbrauchsmaterial existiert und gelöscht ist
        consumable = mongodb.find_one('consumables', {'barcode': decoded_barcode, 'deleted': True})
        if not consumable:
            return jsonify({'success': False, 'message': 'Verbrauchsmaterial nicht gefunden oder nicht gelöscht'}), 404

        # Führe das permanente Löschen durch
        mongodb.delete_one('consumables', {'barcode': decoded_barcode})
        return jsonify({'success': True, 'message': 'Verbrauchsmaterial permanent gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Verbrauchsmaterials: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/workers/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_soft_json():
    """Mitarbeiter soft löschen (markieren als gelöscht) - Barcode aus JSON-Body"""
    try:
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'success': False, 'message': 'Kein Barcode angegeben'}), 400

        barcode = data['barcode'].strip()  # Barcode bereinigen
        if len(barcode) > 50:
            return jsonify({'success': False, 'message': 'Barcode zu lang (max. 50 Zeichen)'}), 400

        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})

        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404

        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings_count = mongodb.count_documents('lendings', {
            'worker_barcode': barcode,
            'returned_at': None
        })

        if active_lendings_count > 0:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter hat noch aktive Ausleihen'
            }), 400

        # Führe das Soft-Delete durch
        mongodb.update_one('workers', {'barcode': barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })

        return jsonify({
            'success': True,
            'message': 'Mitarbeiter wurde erfolgreich gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Mitarbeiters: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/workers/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_soft(barcode):
    """Mitarbeiter soft löschen (markieren als gelöscht) - Barcode aus URL (Legacy)"""
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)

        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': decoded_barcode, 'deleted': {'$ne': True}})

        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404

        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings_count = mongodb.count_documents('lendings', {
            'worker_barcode': decoded_barcode,
            'returned_at': None
        })

        if active_lendings_count > 0:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter hat noch aktive Ausleihen'
            }), 400

        # Führe das Soft-Delete durch
        mongodb.update_one('workers', {'barcode': decoded_barcode}, {
            '$set': {
                'deleted': True,
                'deleted_at': datetime.now()
            }
        })

        return jsonify({
            'success': True,
            'message': 'Mitarbeiter wurde erfolgreich gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Mitarbeiters: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/workers/<barcode>/delete-permanent', methods=['DELETE'])
@mitarbeiter_required
def delete_worker_permanent(barcode):
    try:
        # Barcode URL-dekodieren
        decoded_barcode = unquote(barcode)

        # Prüfe ob der Mitarbeiter existiert (auch gelöschte)
        worker = mongodb.find_one('workers', {'barcode': decoded_barcode})
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeiter nicht gefunden'}), 404

        # Prüfe ob der Mitarbeiter aktive Ausleihen hat
        active_lendings_count = mongodb.count_documents('lendings', {
            'worker_barcode': decoded_barcode,
            'returned_at': None
        })
        if active_lendings_count > 0:
            return jsonify({'success': False, 'message': 'Mitarbeiter hat noch aktive Ausleihen'}), 400

        # Führe das permanente Löschen durch
        mongodb.delete_one('workers', {'barcode': decoded_barcode})
        return jsonify({'success': True, 'message': 'Mitarbeiter permanent gelöscht'})

    except Exception as e:
        logger.error(f"Fehler beim permanenten Löschen des Mitarbeiters: {e}")
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/delete-logo/<filename>', methods=['POST'])
@admin_required
def delete_logo(filename):
    """Logo löschen"""
    try:
        import os
        logo_path = os.path.join(current_app.root_path, 'static', 'uploads', 'logos', filename)
        if os.path.exists(logo_path):
            os.remove(logo_path)
            return jsonify({'success': True, 'message': 'Logo erfolgreich gelöscht'})
        else:
            return jsonify({'success': False, 'message': 'Logo nicht gefunden'}), 404
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Logos: {e}")
        return jsonify({'success': False, 'message': 'Fehler beim Löschen des Logos'}), 500

@bp.route('/delete_ticket_category/<category>', methods=['POST'])
@admin_required
def delete_ticket_category(category):
    """Löscht eine Ticket-Kategorie"""
    try:
        # Überprüfen, ob die Ticket-Kategorie in Verwendung ist
        tickets_with_category = mongodb.db.tickets.find_one({'category': category})
        if tickets_with_category:
            flash('Die Ticket-Kategorie kann nicht gelöscht werden, da sie noch von Tickets verwendet wird.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie aus der Liste entfernen
        mongodb.update_one_array(
            'settings',
            {'key': 'ticket_categories'},
            {'$pull': {'value': category}}
        )

        flash('Ticket-Kategorie erfolgreich gelöscht.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/departments/delete/<name>', methods=['POST'])
@mitarbeiter_required
def delete_department(name):
    try:
        # URL-dekodieren
        from urllib.parse import unquote
        decoded_name = unquote(name)

        # Verwende den AdminSystemSettingsService
        success, message = AdminSystemSettingsService.delete_department(decoded_name)

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Abteilung: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/categories/delete/<name>', methods=['POST'])
@mitarbeiter_required
def delete_category(name):
    try:
        # URL-dekodieren
        decoded_name = unquote(name)
        # Aktuelle Abteilung bestimmen
        from flask import g
        current_dept = getattr(g, 'current_department', None)

        if not current_dept:
            return jsonify({'success': False, 'message': 'Keine Abteilung ausgewählt.'})

        # Überprüfen, ob die Kategorie in Verwendung ist (nur aktuelle Abteilung)
        tools_with_category = mongodb.db.tools.find_one({'category': decoded_name, 'department': current_dept})
        if tools_with_category:
            return jsonify({
                'success': False,
                'message': 'Die Kategorie kann nicht gelöscht werden, da sie noch von Werkzeugen verwendet wird.'
            })

        # Verwende den neuen CategoryService
        from app.services.category_service import category_service
        if category_service.delete_category(decoded_name, current_dept):
            return jsonify({
                'success': True,
                'message': 'Kategorie erfolgreich gelöscht.'
            })
        else:
            return jsonify({'success': False, 'message': 'Kategorie nicht gefunden (Abteilung prüfen).'}), 404

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Kategorie: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/locations/delete/<name>', methods=['POST'])
@mitarbeiter_required
def delete_location(name):
    try:
        # URL-dekodieren
        decoded_name = unquote(name)
        from flask import g
        current_dept = getattr(g, 'current_department', None)

        if not current_dept:
            return jsonify({'success': False, 'message': 'Keine Abteilung ausgewählt.'})

        # Überprüfen, ob der Standort in Verwendung ist (nur aktuelle Abteilung)
        tools_with_location = mongodb.db.tools.find_one({'location': decoded_name, 'department': current_dept})
        if tools_with_location:
            return jsonify({
                'success': False,
                'message': 'Der Standort kann nicht gelöscht werden, da er noch von Werkzeugen verwendet wird.'
            })

        # Verwende den neuen LocationService
        from app.services.location_service import location_service
        success = location_service.delete_location(decoded_name, current_dept)
        if success:
            return jsonify({
                'success': True,
                'message': 'Standort erfolgreich gelöscht.'
            })
        else:
            return jsonify({'success': False, 'message': 'Standort nicht gefunden (Abteilung prüfen).'}), 404

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Standorts '{decoded_name}' in {current_dept}: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/ticket_categories/delete/<name>', methods=['POST'])
@admin_required
def delete_ticket_category_json(name):
    """Löscht (soft) eine Ticket-Kategorie der aktuellen Abteilung"""
    try:
        # URL-dekodieren
        decoded_name = unquote(name)
        # Überprüfen, ob die Ticket-Kategorie in Verwendung ist (nur aktuelle Abteilung)
        from flask import g
        current_dept = getattr(g, 'current_department', None)

        if not current_dept:
            return jsonify({'success': False, 'message': 'Keine Abteilung ausgewählt.'})

        tickets_with_category = mongodb.db.tickets.find_one({'category': decoded_name, 'department': current_dept})
        if tickets_with_category:
            return jsonify({
                'success': False,
                'message': 'Die Ticket-Kategorie kann nicht gelöscht werden, da sie noch von Tickets verwendet wird.'
            })

        # Verwende den neuen HandlungsfeldService
        from app.services.handlungsfeld_service import handlungsfeld_service
        if handlungsfeld_service.delete_handlungsfeld(decoded_name, current_dept):
            return jsonify({
            'success': True,
            'message': 'Ticket-Kategorie erfolgreich gelöscht.'
        })
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/delete_ticket_category/<category>', methods=['POST'])
@admin_required
def delete_ticket_category_legacy(category):
    """Löscht eine Ticket-Kategorie (Legacy-Route)"""
    try:
        # Überprüfen, ob die Ticket-Kategorie in Verwendung ist
        tickets_with_category = mongodb.db.tickets.find_one({'category': category})
        if tickets_with_category:
            flash('Die Ticket-Kategorie kann nicht gelöscht werden, da sie noch von Tickets verwendet wird.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie aus der Liste entfernen
        mongodb.update_one_array(
            'settings',
            {'key': 'ticket_categories'},
            {'$pull': {'value': category}}
        )

        flash('Ticket-Kategorie erfolgreich gelöscht.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/backup/delete/<filename>', methods=['DELETE'])
@admin_required
def delete_backup(filename):
    """Löscht ein Backup (JSON oder Native)"""
    try:
        from app.utils.backup_manager import backup_manager
        import shutil

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
            # Lösche ZIP Backup (Datei)
            backup_path.unlink()
            backup_type = 'zip'
        elif is_native:
            # Lösche natives Backup (Verzeichnis)
            shutil.rmtree(backup_path)
            backup_type = 'native'
        else:
            # Lösche JSON Backup (Datei)
            backup_path.unlink()
            backup_type = 'json'

        return jsonify({
            'status': 'success',
            'message': f'{backup_type.capitalize()} Backup erfolgreich gelöscht',
            'backup_type': backup_type
        })

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Backups: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Löschen des Backups: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_ticket(ticket_id):
    """Ticket soft löschen (markieren als gelöscht)"""
    try:
        # Verwende den AdminTicketService
        success, message = AdminTicketService.delete_ticket(ticket_id, permanent=False)

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Tickets: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/delete-permanent', methods=['DELETE'])
@login_required
@admin_required
def delete_ticket_permanent(ticket_id):
    """Ticket endgültig löschen"""
    try:
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id

        # Prüfe ob das Ticket existiert und gelöscht ist
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update, 'deleted': True})

        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden oder nicht gelöscht'
            }), 404

        # Lösche das Ticket und alle zugehörigen Daten endgültig
        mongodb.delete_one('tickets', {'_id': ticket_id_for_update})
        mongodb.delete_many('ticket_notes', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('ticket_messages', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('ticket_assignments', {'ticket_id': ticket_id_for_update})
        mongodb.delete_one('auftrag_details', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id_for_update})
        mongodb.delete_many('auftrag_arbeit', {'ticket_id': ticket_id_for_update})

        return jsonify({
            'success': True,
            'message': 'Ticket wurde endgültig gelöscht'
        })

    except Exception as e:
        logger.error(f"Fehler beim endgültigen Löschen des Tickets: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
        }), 500
