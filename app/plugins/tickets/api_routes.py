from flask import Blueprint, request, jsonify, render_template, current_app, redirect, url_for, flash, g
from flask_login import current_user
from datetime import datetime
from app.utils.decorators import login_required, admin_required
from app.utils.permissions import permission_required
from app.models.mongodb_database import mongodb, is_feature_enabled
from app.utils.id_helpers import convert_id_for_query, find_document_by_id
from bson import ObjectId
import logging

from .routes import bp, get_ticket_service
from app.services.ticket_service import TicketService
from app.services.ticket_history_service import ticket_history_service
from app.services.notification_service import NotificationService
notification_service = NotificationService()

logger = logging.getLogger(__name__)

@bp.route('/<ticket_id>/messages')
@login_required
@permission_required('tickets', 'view')
def get_ticket_messages(ticket_id):
    """Lädt Nachrichten für ein Ticket"""
    logging.info(f"get_ticket_messages aufgerufen für Ticket {ticket_id}")
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', ticket_id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Prüfe Berechtigungen
        has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))

        if not has_permission:
            return jsonify({'success': False, 'message': 'Sie haben keine Berechtigung, dieses Ticket zu bearbeiten'}), 403

        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(ticket_id)

        # Hole alle Nachrichten für das Ticket
        all_messages = list(mongodb.find('ticket_messages', {'ticket_id': ticket_id_for_query}))

        # Sortiere Nachrichten nach Datum (älteste zuerst)
        all_messages.sort(key=lambda x: x.get('created_at', datetime.min))

        # Formatiere Datum für jede Nachricht
        for msg in all_messages:
            if isinstance(msg.get('created_at'), datetime):
                msg['formatted_date'] = msg['created_at'].strftime('%d.%m.%Y %H:%M')
            else:
                msg['formatted_date'] = str(msg.get('created_at', ''))

        logging.info(f"Nachrichten erfolgreich geladen: {len(all_messages)} Nachrichten")
        return jsonify({
            'success': True,
            'messages': all_messages
        })

    except Exception as e:
        logging.error(f"Fehler beim Laden der Nachrichten: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500


@bp.route('/<ticket_id>/add-message', methods=['POST'])
@login_required
@permission_required('tickets', 'edit')
def add_message(ticket_id):
    """Fügt eine neue Nachricht zu einem Ticket hinzu"""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', ticket_id)
        if not ticket:
            logging.error(f"Ticket {ticket_id} nicht gefunden")
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Prüfe Berechtigungen
        has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))

        if not has_permission:
            return jsonify({'success': False, 'message': 'Sie haben keine Berechtigung, dieses Ticket zu bearbeiten'}), 403

        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(ticket_id)

        # Hole die Nachricht aus dem Request (FormData für Datei-Upload)
        message = request.form.get('message', '').strip()
        if not message:
            logging.error("Leere Nachricht")
            return jsonify({'success': False, 'message': 'Nachricht darf nicht leer sein'}), 400

        logging.info(f"Versuche Nachricht zu speichern: Ticket {ticket_id}, Benutzer {current_user.username}, Nachricht: {message}")

        # Verwende mongodb.insert_one für die Nachrichtenspeicherung
        message_data = {
            'ticket_id': ticket_id_for_query,
            'message': message,
            'sender': current_user.username,
            'created_at': datetime.now()
        }

        result = mongodb.insert_one('ticket_messages', message_data)

        logging.info(f"Nachricht erfolgreich gespeichert")

        # History-Logging für Nachricht
        try:
            from app.services.ticket_history_service import ticket_history_service
            ticket_history_service.log_message_added(
                ticket_id=str(ticket_id),
                message="Nachricht gesendet",  # Kein Inhalt, nur dass eine Nachricht gesendet wurde
                added_by=current_user.username
            )
        except Exception as history_error:
            logging.error(f"Fehler beim History-Logging für Nachricht: {history_error}")

        # Hole die aktuelle Zeit für die Antwort
        created_at = datetime.now()
        formatted_date = created_at.strftime('%d.%m.%Y, %H:%M')

        return jsonify({
            'success': True,
            'message': {
                'text': message,
                'sender': current_user.username,
                'created_at': formatted_date
            }
        })

    except Exception as e:
        logging.error(f"Fehler beim Hinzufügen der Nachricht: [Interner Fehler]", exc_info=True)
        return jsonify({'success': False, 'message': 'Ein Fehler ist aufgetreten'}), 500


@bp.route('/<id>/delete', methods=['POST'])
@login_required
@permission_required('tickets', 'delete')
def delete(id):
    """Löscht ein Ticket."""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)

        if not ticket:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden'
            }), 404

        # Prüfe Berechtigungen: Nur Admins und Mitarbeiter können Tickets löschen
        if current_user.role not in ['admin', 'mitarbeiter']:
            return jsonify({
                'success': False,
                'message': 'Sie haben keine Berechtigung, Tickets zu löschen'
            }), 403

        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)

        # Lösche das Ticket
        if not mongodb.delete_one('tickets', {'_id': ticket_id_for_query}):
            return jsonify({
                'success': False,
                'message': 'Fehler beim Löschen des Tickets'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Ticket wurde gelöscht'
        })

    except Exception as e:
        logging.error(f"Fehler beim Löschen des Tickets #{id}: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Löschen des Tickets'
        }), 500


@bp.route('/<id>/update-status', methods=['POST'])
@login_required
@permission_required('tickets', 'edit')
def update_status(id):
    """Aktualisiert den Status eines Tickets und weist es ggf. automatisch zu"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({'success': False, 'message': 'Status ist erforderlich'}), 400

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Prüfe Berechtigungen: Admin oder verantwortliche Person
        if not (current_user.role == 'admin' or ticket.get('responsible') == current_user.username):
            return jsonify({'success': False, 'message': 'Nur Admins oder die verantwortliche Person dürfen den Status ändern'}), 403

        # Speichere alten Status für History
        old_status = ticket.get('status', 'unbekannt')

        update_fields = {'status': new_status, 'updated_at': datetime.now()}

        # Automatische Zuweisung: Wenn Status von 'offen' auf etwas anderes wechselt und noch niemand zugewiesen ist
        if new_status != 'offen' and (not ticket.get('assigned_to')):
            update_fields['assigned_to'] = current_user.username
        # Wenn Status auf 'offen' gesetzt wird, Zuweisung entfernen
        elif new_status == 'offen':
            update_fields['assigned_to'] = None

        # Verwende die gleiche ID für das Update
        result = mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': update_fields})
        # print(f"DEBUG: update_one Erfolg: {result}")  # Debug-Ausgabe entfernt

        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren des Status'})

        # History-Logging für Status-Änderung
        try:
            from app.services.ticket_history_service import ticket_history_service, TicketStatusChange
            change = TicketStatusChange(
                old_status=old_status,
                new_status=new_status,
                changed_by=current_user.username
            )
            ticket_history_service.log_status_change(ticket_id=str(id), change=change)
        except Exception as history_error:
            logging.error(f"Fehler beim History-Logging für Status-Änderung: {history_error}")

        # Spezielle Nachricht bei automatischer Zuweisung
        if new_status != 'offen' and (not ticket.get('assigned_to')):
            return jsonify({
                'success': True,
                'message': f'Status erfolgreich auf "{new_status}" geändert. Ticket wurde automatisch Ihnen zugewiesen.'
            })
        elif new_status == 'offen':
            return jsonify({
                'success': True,
                'message': f'Status erfolgreich auf "{new_status}" geändert. Zuweisung wurde entfernt.'
            })
        else:
            return jsonify({'success': True, 'message': 'Status erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Status: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500


@bp.route('/<id>/update-assignment', methods=['POST'])
@login_required
@permission_required('tickets', 'assign')
def update_assignment(id):
    """Aktualisiert die Zuweisung eines Tickets (unterstützt Mehrfachzuweisungen)"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        assigned_users = data.get('assigned_users', [])

        # Falls assigned_to noch verwendet wird (Legacy-Support)
        if 'assigned_to' in data:
            assigned_to = data.get('assigned_to')
            if assigned_to:
                assigned_users = [assigned_to]
            else:
                assigned_users = []

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Prüfe Berechtigungen: Admin oder verantwortliche Person
        if not (current_user.role == 'admin' or ticket.get('responsible') == current_user.username):
            return jsonify({'success': False, 'message': 'Nur Admins oder die verantwortliche Person dürfen Zuweisungen ändern'}), 403

        # Speichere alte Zuweisungen für History
        old_assigned_users = []

        # Prüfe Legacy-Zuweisung
        if ticket.get('assigned_to'):
            old_assigned_users.append(ticket['assigned_to'])

        # Prüfe Mehrfach-Zuweisungen
        existing_assignments = list(mongodb.find('ticket_assignments', {'ticket_id': str(ticket_id_for_update)}))
        for assignment in existing_assignments:
            if assignment.get('assigned_to') not in old_assigned_users:
                old_assigned_users.append(assignment['assigned_to'])

        # Verwende den TicketService für die Mehrfachzuweisung
        ticket_service = TicketService()
        success, message = ticket_service.assign_ticket_multiple(str(ticket_id_for_update), assigned_users, current_user.username)

        if success:
            # History-Logging für Zuweisungsänderung
            try:
                from app.services.ticket_history_service import ticket_history_service, AssignmentDetails
                old_assignment_str = ', '.join(old_assigned_users) if old_assigned_users else 'Nicht zugewiesen'
                new_assignment_str = ', '.join(assigned_users) if assigned_users else 'Nicht zugewiesen'

                details = AssignmentDetails(
                    old_assignee=old_assignment_str,
                    new_assignee=new_assignment_str
                )

                ticket_history_service.log_assignment(
                    ticket_id=str(id),
                    details=details,
                    changed_by=current_user.username
                )
            except Exception as history_error:
                logging.error(f"Fehler beim History-Logging für Zuweisungsänderung: {history_error}")

            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Zuweisung: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500


@bp.route('/<id>/update-responsible', methods=['POST'])
@login_required
@permission_required('tickets', 'assign')
def update_responsible(id):
    """Setzt oder entfernt die verantwortliche Person (Ticket-Leitung)"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        responsible = data.get('responsible')  # username oder None

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            ticket_id_for_update = ObjectId(id)
        except Exception:
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Prüfe Berechtigungen: Nur Admin oder aktuelle verantwortliche Person dürfen die Hauptverantwortung ändern
        current_responsible = ticket.get('responsible')
        if not (current_user.role == 'admin' or current_responsible == current_user.username):
            return jsonify({'success': False, 'message': 'Nur Admins oder die aktuelle verantwortliche Person dürfen dies ändern'}), 403

        # Service verwenden
        ticket_service = TicketService()
        success, message = ticket_service.update_responsible(str(ticket_id_for_update), responsible, current_user.username)
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der verantwortlichen Person: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500


@bp.route('/<id>/update-due-date', methods=['POST'])
@login_required
@permission_required('tickets', 'edit')
def update_due_date(id):
    """Aktualisiert das Fälligkeitsdatum eines Tickets"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        due_date = data.get('due_date')

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Prüfe Berechtigungen
        has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))

        if not has_permission:
            return jsonify({'success': False, 'message': 'Sie haben keine Berechtigung, dieses Ticket zu bearbeiten'}), 403

        # Verarbeite due_date
        update_data = {'updated_at': datetime.now()}
        if due_date:
            try:
                # Versuche verschiedene Datumsformate zu parsen
                if 'T' in due_date:
                    due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
                else:
                    due_date = datetime.strptime(due_date, '%Y-%m-%d')
                update_data['due_date'] = due_date
            except ValueError as e:
                return jsonify({'success': False, 'message': 'Ungültiges Datumsformat'}), 400
        else:
            update_data['due_date'] = None

        # Führe das Update aus
        result = mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': update_data})

        if not result:
            return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren des Fälligkeitsdatums'})

        return jsonify({'success': True, 'message': 'Fälligkeitsdatum erfolgreich aktualisiert'})

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Fälligkeitsdatums: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500


@bp.route('/<id>/update-details', methods=['POST'])
@login_required
@permission_required('tickets', 'edit')
def update_details(id):
    """Aktualisiert die Auftragsdetails eines Tickets"""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        if not ticket:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404
            else:
                flash('Ticket nicht gefunden', 'error')
                return redirect(url_for('tickets.create'))

        # Prüfe Berechtigungen
        has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))

        if not has_permission:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Sie haben keine Berechtigung, dieses Ticket zu bearbeiten'}), 403
            else:
                flash('Sie haben keine Berechtigung, dieses Ticket zu bearbeiten', 'error')
                return redirect(url_for('tickets.create'))

        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)

        # Verarbeite die Daten je nach Request-Typ
        if request.is_json:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400
        else:
            # Formular-Daten verarbeiten
            form_data = request.form.to_dict()
            data = {}

            # Basis-Formulardaten
            for key, value in form_data.items():
                data[key] = value

            # Verarbeite den Auftraggeber-Typ (Radio-Button)
            auftraggeber_typ = data.get('auftraggeber_typ', '')
            data['auftraggeber_intern'] = auftraggeber_typ == 'intern'
            data['auftraggeber_extern'] = auftraggeber_typ == 'extern'

            # Materialliste aus Formular sammeln
            material_list = []
            material_names = request.form.getlist('material')
            material_mengen = request.form.getlist('menge')
            material_preise = request.form.getlist('einzelpreis')

            for i in range(len(material_names)):
                if material_names[i] or material_mengen[i] or material_preise[i]:
                    material_list.append({
                        'material': material_names[i],
                        'menge': float(material_mengen[i]) if material_mengen[i] else 0,
                        'einzelpreis': float(material_preise[i]) if material_preise[i] else 0
                    })

            # Arbeitsliste aus Formular sammeln
            arbeit_list = []
            arbeit_names = request.form.getlist('arbeit')
            arbeit_stunden = request.form.getlist('arbeitsstunden')
            arbeit_kategorien = request.form.getlist('leistungskategorie')

            for i in range(len(arbeit_names)):
                if arbeit_names[i] or arbeit_stunden[i] or arbeit_kategorien[i]:
                    arbeit_list.append({
                        'arbeit': arbeit_names[i],
                        'arbeitsstunden': float(arbeit_stunden[i]) if arbeit_stunden[i] else 0,
                        'leistungskategorie': arbeit_kategorien[i]
                    })

            data['material_list'] = material_list
            data['arbeit_list'] = arbeit_list

        logging.info(f"Empfangene Daten für Ticket {id}: {data}")

        # Verarbeite ausgeführte Arbeiten
        arbeit_list = data.get('arbeit_list', [])

        # Filtere nur wirklich leere Zeilen heraus (alle Felder leer)
        filtered_arbeit_list = []
        for arbeit in arbeit_list:
            arbeit_name = arbeit.get('arbeit', '').strip()
            arbeitsstunden = arbeit.get('arbeitsstunden', 0)
            leistungskategorie = arbeit.get('leistungskategorie', '').strip()

            # Nur hinzufügen wenn mindestens ein Feld ausgefüllt ist
            if arbeit_name or arbeitsstunden > 0 or leistungskategorie:
                filtered_arbeit_list.append(arbeit)

        ausgefuehrte_arbeiten = '\n'.join([
            f"{arbeit.get('arbeit', '')}|{arbeit.get('arbeitsstunden', '')}|{arbeit.get('leistungskategorie', '')}"
            for arbeit in filtered_arbeit_list
        ])
        logging.info(f"Verarbeitete ausgeführte Arbeiten: {ausgefuehrte_arbeiten}")

        # Bereite die Auftragsdetails vor
        auftrag_details_daten = {
            'ticket_id': ticket_id_for_query,
            'bereich': data.get('bereich', ''),
            'auftraggeber_intern': data.get('auftraggeber_intern', False),
            'auftraggeber_extern': data.get('auftraggeber_extern', False),
            'auftraggeber_name': data.get('auftraggeber_name', ''),
            'kontakt': data.get('kontakt', ''),
            'auftragsbeschreibung': data.get('auftragsbeschreibung', ''),
            'ausgefuehrte_arbeiten': ausgefuehrte_arbeiten,
            'fertigstellungstermin': data.get('fertigstellungstermin'),
            'gesamtsumme': data.get('gesamtsumme', 0)
        }

        # Speichere oder aktualisiere die Auftragsdetails
        existing_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query})

        # History-Logging für Auftragsdetails-Änderungen
        try:
            from app.services.ticket_history_service import ticket_history_service

            # Vergleiche wichtige Felder für History
            if existing_details:
                # Prüfe auf Änderungen in wichtigen Feldern
                important_fields = ['auftrag_an', 'bereich', 'beschreibung', 'prioritaet', 'deadline', 'fertigstellungstermin']
                for field in important_fields:
                    old_value = existing_details.get(field)
                    new_value = auftrag_details_daten.get(field)

                    if old_value != new_value:
                        field_name = {
                            'auftrag_an': 'Auftrag an',
                            'bereich': 'Bereich',
                            'beschreibung': 'Beschreibung',
                            'prioritaet': 'Priorität',
                            'deadline': 'Deadline',
                            'fertigstellungstermin': 'Fertigstellungstermin'
                        }.get(field, field)

                        from app.services.ticket_history_service import ChangeContext
                        ticket_history_service.log_change(
                            ticket_id=str(id),
                            field=field_name,
                            old_value=old_value,
                            new_value=new_value,
                            changed_by=current_user.username,
                            context=ChangeContext(change_type='update')
                        )

                mongodb.update_one('auftrag_details', {'ticket_id': ticket_id_for_query}, {'$set': auftrag_details_daten})
            else:
                # Neue Auftragsdetails erstellt
                from app.services.ticket_history_service import ChangeContext
                ticket_history_service.log_change(
                    ticket_id=str(id),
                    field='auftragsdetails',
                    old_value=None,
                    new_value='Auftragsdetails hinzugefügt',
                    changed_by=current_user.username,
                    context=ChangeContext(change_type='update')
                )
                mongodb.insert_one('auftrag_details', auftrag_details_daten)
        except Exception as history_error:
            logging.error(f"Fehler beim History-Logging für Auftragsdetails: {history_error}")
            # Führe Update/Insert trotzdem aus
            if existing_details:
                mongodb.update_one('auftrag_details', {'ticket_id': ticket_id_for_query}, {'$set': auftrag_details_daten})
            else:
                mongodb.insert_one('auftrag_details', auftrag_details_daten)

        # Verarbeite die Materialliste
        material_list = data.get('material_list', [])
        mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id_for_query})

        if material_list:
            # Filtere nur wirklich leere Zeilen heraus (alle Felder leer)
            filtered_material_list = []
            for m in material_list:
                material = m.get('material', '').strip()
                menge = m.get('menge', 0)
                einzelpreis = m.get('einzelpreis', 0)

                # Nur hinzufügen wenn mindestens ein Feld ausgefüllt ist
                if material or menge > 0 or einzelpreis > 0:
                    filtered_material_list.append({
                        'ticket_id': ticket_id_for_query,
                        'material': material,
                        'menge': menge,
                        'einzelpreis': einzelpreis
                    })

            if filtered_material_list:
                mongodb.insert_many('auftrag_material', filtered_material_list)

        # Verarbeite die Arbeitsliste
        mongodb.delete_many('auftrag_arbeit', {'ticket_id': ticket_id_for_query})

        if filtered_arbeit_list:
            arbeit_daten = [{
                'ticket_id': ticket_id_for_query,
                'arbeit': arbeit.get('arbeit', ''),
                'arbeitsstunden': arbeit.get('arbeitsstunden', 0),
                'leistungskategorie': arbeit.get('leistungskategorie', '')
            } for arbeit in filtered_arbeit_list]
            mongodb.insert_many('auftrag_arbeit', arbeit_daten)

        # Setze das 'updated_at' Feld am Ticket selbst
        mongodb.update_one('tickets', {'_id': ticket_id_for_query}, {'$set': {'updated_at': datetime.now()}})

        # Rückgabe je nach Request-Typ
        if request.is_json:
            return jsonify({'success': True, 'message': 'Auftragsdetails erfolgreich gespeichert'})
        else:
            flash('Auftragsdetails erfolgreich gespeichert', 'success')
            return redirect(url_for('tickets.view', ticket_id=id))

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren der Auftragsdetails: [Interner Fehler]", exc_info=True)
        if request.is_json:
            return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500
        else:
            flash(f'Fehler beim Speichern: [Interner Fehler]', 'error')
            return redirect(url_for('tickets.auftrag_details_page', id=id))


@bp.route('/<id>/note', methods=['POST'])
@login_required
@permission_required('tickets', 'edit')
@admin_required
def add_note(id):
    """Fügt eine neue Notiz zu einem Ticket hinzu"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat'}), 400

        data = request.get_json()
        note_text = data.get('note', '').strip()

        if not note_text:
            return jsonify({'success': False, 'message': 'Notiz darf nicht leer sein'}), 400

        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        if not ticket:
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)

        # Erstelle die Notiz
        note_data = {
            'ticket_id': ticket_id_for_query,
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
        logging.error(f"Fehler beim Hinzufügen der Notiz: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Ein interner Fehler ist aufgetreten.'}), 500


@bp.route('/<id>/update-ticket', methods=['POST'])
@login_required
@permission_required('tickets', 'edit')
def update_ticket(id):
    """Aktualisiert die grundlegenden Ticket-Details wie estimated_time, category, due_date"""
    try:
        logging.info(f"DEBUG: update_ticket aufgerufen für ID: {id}")

        # Import für History-Logging
        from app.services.ticket_history_service import ticket_history_service

        # Verwende die ursprüngliche ID direkt für das Update
        from bson import ObjectId
        try:
            # Versuche zuerst mit ObjectId
            ticket_id_for_update = ObjectId(id)
        except:
            # Falls das fehlschlägt, verwende die ursprüngliche ID als String
            ticket_id_for_update = id

        # Prüfe ob das Ticket existiert und speichere alte Werte für History
        ticket = mongodb.find_one('tickets', {'_id': ticket_id_for_update})
        if not ticket:
            logging.error(f"DEBUG: Ticket nicht gefunden für ID: {id}")
            return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        # Speichere alte Werte für History-Logging
        old_values = dict(ticket)

        logging.info(f"DEBUG: Ticket gefunden: {ticket.get('title', 'No Title')}")

        # Prüfe Berechtigungen: Normale User können nur ihre eigenen oder zugewiesenen Tickets bearbeiten
        has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))

        if not has_permission:
            logging.error(f"DEBUG: Keine Berechtigung für User {current_user.username}")
            return jsonify({'success': False, 'message': 'Sie haben keine Berechtigung, dieses Ticket zu bearbeiten'}), 403

        logging.info(f"DEBUG: Berechtigung OK")

        # Hole die Daten aus dem Request
        if not request.is_json:
            logging.error(f"DEBUG: Request ist kein JSON")
            return jsonify({'success': False, 'message': 'Ungültiges Anfrageformat. JSON erwartet.'}), 400

        data = request.get_json()
        logging.info(f"DEBUG: Request-Daten: {data}")

        # Bereite die Update-Daten vor
        update_data = {
            'updated_at': datetime.now()
        }
        logging.info(f"DEBUG: Basis-Update-Daten: {update_data}")

        # Verarbeite estimated_time (wird in Minuten gespeichert)
        if 'estimated_time' in data:
            estimated_time = data['estimated_time']
            if estimated_time is not None and estimated_time != '':
                update_data['estimated_time'] = float(estimated_time)
                logging.info(f"DEBUG: estimated_time gesetzt: {update_data['estimated_time']}")
            else:
                update_data['estimated_time'] = None
                logging.info(f"DEBUG: estimated_time auf None gesetzt")

        # Verarbeite category
        if 'category' in data:
            update_data['category'] = data['category']
            logging.info(f"DEBUG: category gesetzt: {update_data['category']}")

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
                    update_data['due_date'] = due_date
                    logging.info(f"DEBUG: due_date gesetzt: {update_data['due_date']}")
                except ValueError as e:
                    logging.error(f"DEBUG: Fehler beim Parsen von due_date: [Interner Fehler]")
                    return jsonify({'success': False, 'message': 'Ungültiges Datumsformat'}), 400
            else:
                update_data['due_date'] = None
                logging.info(f"DEBUG: due_date auf None gesetzt")

        # Verarbeite priority
        if 'priority' in data:
            update_data['priority'] = data['priority']
            logging.info(f"DEBUG: priority gesetzt: {update_data['priority']}")

        logging.info(f"DEBUG: Finale Update-Daten: {update_data}")

        # Debug-Logs hinzufügen
        logging.info(f"DEBUG: Aktualisiere Ticket {id} mit ticket_id_for_update: {ticket_id_for_update}")
        logging.info(f"DEBUG: Update-Daten: {update_data}")
        logging.info(f"DEBUG: ticket_id_for_update Typ: {type(ticket_id_for_update).__name__}")
        logging.info(f"DEBUG: ticket_id_for_update Wert: {ticket_id_for_update}")

        try:
            # Verwende die bewährte mongodb-Wrapper-Klasse
            logging.info(f"DEBUG: Führe Update aus mit Filter: {{'_id': {ticket_id_for_update}}}")
            logging.info(f"DEBUG: Update-Daten: {update_data}")

            result = mongodb.update_one('tickets', {'_id': ticket_id_for_update}, {'$set': update_data})
            logging.info(f"DEBUG: Update-Ergebnis: {result}")

            # Betrachte als erfolgreich, wenn die Operation erfolgreich war
            if result:
                logging.info(f"DEBUG: Update erfolgreich")

                # History-Logging für alle Änderungen
                try:
                    ticket_history_service.log_bulk_update(
                        ticket_id=str(id),
                        updates=update_data,
                        old_values=old_values,
                        changed_by=current_user.username
                    )
                except Exception as history_error:
                    logging.error(f"Fehler beim History-Logging: {history_error}")

                return jsonify({'success': True, 'message': 'Ticket erfolgreich aktualisiert'})
            else:
                logging.error(f"DEBUG: Update fehlgeschlagen - Kein Dokument gefunden")
                return jsonify({'success': False, 'message': 'Ticket nicht gefunden'}), 404

        except Exception as db_error:
            logging.error(f"DEBUG: Datenbankfehler beim Update: {db_error}")
            return jsonify({'success': False, 'message': f'Datenbankfehler: {str(db_error)}'}), 500

    except Exception as e:
        logging.error(f"Fehler beim Aktualisieren des Tickets {id}: [Interner Fehler]", exc_info=True)
        return jsonify({'success': False, 'message': f'Interner Fehler: [Interner Fehler]'}), 500
