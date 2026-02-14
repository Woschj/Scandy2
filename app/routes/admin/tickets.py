from .blueprint import bp
from .shared import *
@bp.route('/tickets/<ticket_id>')
@login_required
@mitarbeiter_required
def ticket_detail(ticket_id):
    """Zeigt die Details eines Tickets für Administratoren."""
    ticket = mongodb.find_one('tickets', {'_id': convert_id_for_query(ticket_id)})

    if not ticket:
        return render_template('404.html'), 404

    # Füge id-Feld hinzu (für Template-Kompatibilität)
    ticket['id'] = str(ticket['_id'])

    # Konvertiere alle Datumsfelder zu datetime-Objekten
    date_fields = ['created_at', 'updated_at', 'resolved_at', 'due_date']
    for field in date_fields:
        if ticket.get(field):
            try:
                ticket[field] = datetime.strptime(ticket[field], '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                ticket[field] = None

    # Hole die Notizen für das Ticket
    notes = mongodb.find('ticket_notes', {'ticket_id': convert_id_for_query(ticket_id)})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': convert_id_for_query(ticket_id)})
    # Formatiere die Nachrichten für das Template
    formatted_messages = []
    for msg in messages:
        formatted_msg = dict(msg)
        # Konvertiere created_at zu String-Format
        if isinstance(formatted_msg.get('created_at'), datetime):
            formatted_msg['created_at'] = formatted_msg['created_at'].strftime('%d.%m.%Y %H:%M')
        # Setze is_admin Flag basierend auf dem Sender
        formatted_msg['is_admin'] = formatted_msg.get('sender') == current_user.username
        formatted_messages.append(formatted_msg)

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': convert_id_for_query(ticket_id)})
    logging.info(f"DEBUG: auftrag_details für Ticket {ticket_id}: {auftrag_details}")

    # Hole die Materialliste
    material_list = mongodb.find('auftrag_material', {'ticket_id': convert_id_for_query(ticket_id)})

    # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
    users = mongodb.find('users', {'is_active': True})
    users = [dict(user) for user in users]

    # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
    assigned_users = mongodb.find('ticket_assignments', {'ticket_id': convert_id_for_query(ticket_id)})

    # Hole Kategorien der aktuellen Abteilung
    from app.services.ticket_category_service import ticket_category_service
    categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))

    # Hole Arbeitszeiten
    arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': convert_id_for_query(ticket_id)}))

    # Hole Notizen
    notes = list(mongodb.find('ticket_notes', {'ticket_id': convert_id_for_query(ticket_id)}, sort=[('created_at', -1)]))

    # Hole Nachrichten
    messages = list(mongodb.find('ticket_messages', {'ticket_id': convert_id_for_query(ticket_id)}, sort=[('created_at', -1)]))

    # Hole alle Mitarbeiter für Zuweisung
    workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}, sort=[('lastname', 1)]))

    # Hole alle Abteilungen
    departments = get_departments_from_settings()

    # Hole alle Standorte
    locations = get_locations_from_settings()

    return render_template('admin/ticket_detail.html',
                         ticket=ticket,
                         notes=notes,
                         messages=formatted_messages,
                         users=users,
                         workers=users,  # Template erwartet 'workers'
                         assigned_users=assigned_users,
                         auftrag_details=auftrag_details,
                         material_list=material_list,
                         categories=categories,
                         now=datetime.now(),
                         arbeit_list=arbeit_list)

@bp.route('/tickets/<ticket_id>/message', methods=['POST'])
@login_required
@admin_required
def add_ticket_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu."""
    try:
        # Hole die Nachricht aus dem Request
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Ungültiges Anfrageformat. JSON erwartet.'
            }), 400

        data = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({
                'success': False,
                'message': 'Nachricht darf nicht leer sein'
            }), 400

        # Verwende den AdminTicketService
        success, result_message = AdminTicketService.add_ticket_message(ticket_id, message, 'message')

        if success:
            return jsonify({
                'success': True,
                'message': {
                    'sender': current_user.username,
                    'text': message,
                    'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': result_message
            }), 400

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Nachricht: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Speichern der Nachricht: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/note', methods=['POST'])
@login_required
@admin_required
def add_ticket_note(ticket_id):
    """Fügt eine neue Notiz zu einem Ticket hinzu"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        note_text = data.get('note', '').strip()

        if not note_text:
            return jsonify({'success': False, 'message': 'Notiz darf nicht leer sein'}), 400

        # Erstelle die Notiz
        note_data = {
            'ticket_id': convert_id_for_query(ticket_id),
            'note': note_text,
            'created_by': current_user.username,
            'created_at': datetime.now()
        }

        result = mongodb.insert_one('ticket_notes', note_data)

        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Speichern der Notiz'}), 500

        return jsonify({
            'success': True,
            'message': 'Notiz erfolgreich hinzugefügt',
            'note': {
                'id': str(result),
                'text': note_text,
                'created_by': current_user.username,
                'created_at': datetime.now().strftime('%d.%m.%Y %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Notiz: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/tickets/<ticket_id>/update', methods=['POST'])
@login_required
@admin_required
def update_ticket(ticket_id):
    """Aktualisiert ein Ticket"""
    try:
        data = request.get_json()
        logging.info(f"Empfangene Daten für Ticket {ticket_id}: {data}")

        # Verarbeite ausgeführte Arbeiten
        arbeit_list = data.get('arbeit_list', [])
        ausgefuehrte_arbeiten = '\n'.join([
            f"{arbeit['arbeit']}|{arbeit['arbeitsstunden']}|{arbeit['leistungskategorie']}"
            for arbeit in arbeit_list
        ])
        logging.info(f"Verarbeitete ausgeführte Arbeiten: {ausgefuehrte_arbeiten}")

        # Bereite die Auftragsdetails vor
        auftrag_details = {
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': data.get('auftraggeber_typ') == 'intern',
            'auftraggeber_extern': data.get('auftraggeber_typ') == 'extern',
            'auftraggeber_name': data.get('auftraggeber_name', ''),
            'kontakt': data.get('kontakt', ''),
            'auftragsbeschreibung': data.get('auftragsbeschreibung', ''),
            'ausgefuehrte_arbeiten': ausgefuehrte_arbeiten,
            'arbeitsstunden': data.get('arbeitsstunden', ''),
            'leistungskategorie': data.get('leistungskategorie', ''),
            'fertigstellungstermin': data.get('fertigstellungstermin', ''),
            'gesamtsumme': data.get('gesamtsumme', 0)
        }

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id

        # Aktualisiere die Auftragsdetails
        if not mongodb.update_one('auftrag_details', {'ticket_id': ticket_id_for_update}, {'$set': auftrag_details}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Auftragsdetails'})

        # Aktualisiere die Materialliste
        material_list = data.get('material_list', [])
        if not mongodb.update_many('auftrag_material', {'ticket_id': ticket_id_for_update}, {'$set': {'menge': m['menge'], 'einzelpreis': m['einzelpreis']} for m in material_list}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Materialliste'})

        return jsonify({'success': True})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets {ticket_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/tickets/<ticket_id>/update-details', methods=['POST'])
@login_required
@admin_required
def update_ticket_details(ticket_id):
    """Aktualisiert die Details eines Tickets."""
    try:
        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})

        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Hole die Daten aus dem Request
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Ungültiges Anfrageformat. JSON erwartet.'
            }), 400

        data = request.get_json()

        # Auftragsdetails aktualisieren
        auftrag_details = {
            'ticket_id': ticket_id_for_update,
            'auftrag_an': data.get('auftrag_an', ''),
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': data.get('auftraggeber_typ') == 'intern',
            'auftraggeber_extern': data.get('auftraggeber_typ') == 'extern',
            'beschreibung': data.get('beschreibung', ''),
            'prioritaet': data.get('prioritaet', 'normal'),
            'deadline': data.get('deadline'),
            'updated_at': datetime.now()
        }

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id

        if not mongodb.update_one('auftrag_details', {'ticket_id': ticket_id_for_update}, {'$set': auftrag_details}):
            mongodb.insert_one('auftrag_details', auftrag_details)

        # Materialliste aktualisieren
        material_list = data.get('material_list', [])
        if material_list:
            # Lösche alte Materialeinträge
            mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id_for_update})

            # Füge neue Materialeinträge hinzu
            for material in material_list:
                material['ticket_id'] = ticket_id_for_update
                material['created_at'] = datetime.now()
                mongodb.insert_one('auftrag_material', material)

        # Ticket selbst aktualisieren
        ticket_update = {
            'title': data.get('title', ticket.get('title', '')),
            'description': data.get('description', ticket.get('description', '')),
            'priority': data.get('prioritaet', ticket.get('priority', 'normal')),
            'updated_at': datetime.now()
        }

        # Verarbeite estimated_time (wird in Minuten gespeichert)
        if 'estimated_time' in data:
            estimated_time = data['estimated_time']
            if estimated_time is not None and estimated_time != '':
                ticket_update['estimated_time'] = float(estimated_time)
            else:
                ticket_update['estimated_time'] = None

        # Verarbeite category
        if 'category' in data:
            ticket_update['category'] = data['category']

        # Verarbeite due_date
        if 'due_date' in data:
            due_date = data['due_date']
            if due_date:
                try:
                    # Versuche verschiedene Datumsformate zu parsen
                    if 'T' in due_date:
                        due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                    else:
                        due_date = datetime.strptime(due_date, '%Y-%m-%d')
                    ticket_update['due_date'] = due_date
                except ValueError:
                    return jsonify({'success': False, 'message': 'Ungültiges Datumsformat'}), 400
            else:
                ticket_update['due_date'] = None

        if not mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': ticket_update}):
            return jsonify({
                'success': False,
                'message': 'Fehler beim Aktualisieren des Tickets'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Ticket-Details erfolgreich aktualisiert'
        })

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Ticket-Details: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Interner Fehler: {str(e)}'
        }), 500

@bp.route('/add_ticket_category', methods=['POST'])
@admin_required
def add_ticket_category():
    """Fügt eine neue Ticket-Kategorie hinzu"""
    try:
        name = request.form.get('category')
        if not name:
            flash('Bitte geben Sie einen Namen ein.', 'error')
            return redirect(url_for('tickets.create'))

        # Prüfen ob Ticket-Kategorie bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
        if settings and name in settings.get('value', []):
            flash('Diese Ticket-Kategorie existiert bereits.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie zur Liste hinzufügen
        if settings:
            mongodb.update_one_array(
                'settings',
                {'key': 'ticket_categories'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.insert_one('settings', {
                'key': 'ticket_categories',
                'value': [name]
            })

        flash('Ticket-Kategorie erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/ticket_categories')
@mitarbeiter_required
def get_ticket_categories():
    """Gibt alle Ticket-Kategorien (Handlungsfelder) der aktuellen/angefragten Abteilung zurück."""
    try:
        req_dept = request.args.get('dept')
        from flask import g
        current_dept = req_dept or getattr(g, 'current_department', None)
        if not current_dept:
            return jsonify({'success': True, 'categories': [], 'department': None})

        # Verwende den neuen HandlungsfeldService
        from app.services.handlungsfeld_service import handlungsfeld_service
        categories = handlungsfeld_service.get_handlungsfelder_for_department(current_dept)
        return jsonify({'success': True, 'department': current_dept, 'categories': [{'name': n} for n in categories]})
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Ticket-Kategorien: {str(e)}")
        return jsonify({'success': False, 'message': 'Fehler beim Laden der Ticket-Kategorien'})

@bp.route('/ticket_categories/add', methods=['POST'])
@admin_required
def add_ticket_category_json():
    """Fügt eine neue Ticket-Kategorie (Handlungsfeld) abteilungsgebunden hinzu"""
    try:
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('category', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Verwende den neuen HandlungsfeldService
        from flask import g
        req_dept = request.form.get('dept')
        current_dept = req_dept or getattr(g, 'current_department', None)
        if not current_dept:
            return jsonify({'success': False, 'message': 'Keine Abteilung ausgewählt.'})

        from app.services.handlungsfeld_service import handlungsfeld_service
        if handlungsfeld_service.create_handlungsfeld(name, current_dept):
            return jsonify({
                'success': True,
                'message': 'Ticket-Kategorie erfolgreich hinzugefügt.'
            })
        else:
            return jsonify({'success': False, 'message': 'Diese Ticket-Kategorie existiert bereits in dieser Abteilung.'})

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/add_ticket_category', methods=['POST'])
@admin_required
def add_ticket_category_legacy():
    """Fügt eine neue Ticket-Kategorie hinzu (Legacy-Route)"""
    try:
        name = request.form.get('category')
        if not name:
            flash('Bitte geben Sie einen Namen ein.', 'error')
            return redirect(url_for('tickets.create'))

        # Prüfen ob Ticket-Kategorie bereits existiert
        settings = mongodb.db.settings.find_one({'key': 'ticket_categories'})
        if settings and name in settings.get('value', []):
            flash('Diese Ticket-Kategorie existiert bereits.', 'error')
            return redirect(url_for('tickets.create'))

        # Ticket-Kategorie zur Liste hinzufügen
        if settings:
            mongodb.update_one_array(
                'settings',
                {'key': 'ticket_categories'},
                {'$push': {'value': name}}
            )
        else:
            mongodb.insert_one('settings', {
                'key': 'ticket_categories',
                'value': [name]
            })

        flash('Ticket-Kategorie erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('tickets.create'))
    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        flash('Ein Fehler ist aufgetreten.', 'error')
        return redirect(url_for('tickets.create'))

@bp.route('/tickets/<ticket_id>/update-assignment', methods=['POST'])
@login_required
@admin_required
def update_ticket_assignment(ticket_id):
    """Aktualisiert die Zuweisung eines Tickets"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        assigned_to = data.get('assigned_to')

        # Wenn assigned_to leer ist, setze es auf None
        if not assigned_to or assigned_to == "":
            assigned_to = None

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id

        # Aktualisiere die Zuweisung direkt im Ticket
        if not mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': {'assigned_to': assigned_to, 'updated_at': datetime.now()}}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Zuweisung'})

        # Wenn die Zuweisung entfernt wurde, setze Status auf 'offen' (sofern nicht final)
        if assigned_to is None:
            try:
                ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
                if ticket and ticket.get('status') not in ['gelöst', 'geschlossen']:
                    mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': {'status': 'offen', 'updated_at': datetime.now()}})
            except Exception as _e:
                logger.error(f"Fehler beim Setzen von Status 'offen' für Ticket {ticket_id}: {_e}")

        return jsonify({'success': True, 'message': 'Zuweisung erfolgreich aktualisiert'})

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Zuweisung: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/tickets/<ticket_id>/update-responsible', methods=['POST'])
@login_required
@admin_required
def update_ticket_responsible(ticket_id):
    """Setzt oder entfernt die verantwortliche Person (Ticket-Leitung)"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        responsible = data.get('responsible')

        from bson import ObjectId
        try:
            ticket_id_for_update = ObjectId(ticket_id)
        except Exception:
            ticket_id_for_update = ticket_id

        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Optional: Validierung Nutzer
        if responsible:
            user = mongodb.find_one('users', {'username': responsible})
            if not user:
                return jsonify({'success': False, 'message': 'Benutzer nicht gefunden'}), 400

        # Update durchführen
        if not mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': {'responsible': responsible or None, 'updated_at': datetime.now()}}):
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren der Verantwortlichen-Information'})

        return jsonify({'success': True, 'message': 'Verantwortliche Person aktualisiert'})
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der verantwortlichen Person: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/tickets/<ticket_id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_ticket_status(ticket_id):
    """Ticket-Status aktualisieren"""
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'success': False, 'message': 'Status nicht angegeben'}), 400

        new_status = data['status']

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(ticket_id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = ticket_id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Aktualisiere den Status
        mongodb.update_one('tickets',
                          {'_id': ticket_id_for_update},
                          {
                              '$set': {
                                  'status': new_status,
                                  'updated_at': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
                              }
                          })

        return jsonify({
            'success': True,
            'message': f'Status wurde auf "{new_status}" geändert'
        })

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Status: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
