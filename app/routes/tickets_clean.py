"""
Tickets Routes - Production Version

Bereinigte Version der tickets.py Route-Datei ohne Debug-Code.
Enthält nur produktive Routen für Ticket-Management.

Original: 2382 Zeilen
Clean: ~800 Zeilen (Reduzierung um 66%)
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, render_template_string, current_app
from app.models.mongodb_models import MongoDBTicket
from app.models.mongodb_database import mongodb, is_feature_enabled
from flask import g
from app.utils.decorators import login_required, admin_required, not_teilnehmer_required
from app.utils.permissions import permission_required
from app.utils.database_helpers import get_ticket_categories_from_settings, get_categories_from_settings, get_next_ticket_number, get_departments_from_settings
from app.utils.id_helpers import convert_id_for_query
from app.models.user import User
from app.services.ticket_service import TicketService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

bp = Blueprint('tickets', __name__, url_prefix='/tickets')

# Ticket Service Instanz
def get_ticket_service():
    """Gibt eine Instanz des TicketService zurück"""
    return TicketService()

def check_ticket_permission(ticket, username, role):
    """
    Prüft ob ein Nutzende Berechtigung für ein Ticket hat

    Args:
        ticket: Ticket-Daten
        username: Nutzendename
        role: Nutzenderolle

    Returns:
        bool: True wenn Berechtigung vorhanden, False sonst
    """
    # Admins können alle Tickets sehen
    if role == 'admin':
        return True

    # Department-Gleichheit prüfen: Ticket muss in gleicher Abteilung liegen (falls gesetzt)
    try:
        current_dept = getattr(g, 'current_department', None)
        if current_dept:
            ticket_dept = ticket.get('department')
            if ticket_dept and ticket_dept != current_dept:
                return False
    except Exception:
        pass

    # Erstellt von dem Nutzende
    if ticket.get('created_by') == username:
        return True

    # Verantwortliche Person hat Zugriff (volle Rechte für Micro-Administration)
    if ticket.get('responsible') == username:
        return True

    # Zugewiesen an den Nutzende (Legacy + Mehrfachzuweisung)
    # Prüfe Legacy-Zuweisung
    if ticket.get('assigned_to') == username:
        return True

    # Prüfe Mehrfachzuweisung
    ticket_id_for_query = convert_id_for_query(str(ticket['_id']))
    user_assignments = mongodb.find('ticket_assignments', {'ticket_id': ticket_id_for_query, 'assigned_to': username})
    if list(user_assignments):  # Wenn Einträge gefunden wurden
        return True

    # Falls nicht zugewiesen, prüfe Handlungsfeld
    # Hole Handlungsfelder des Nutzendes
    user_settings = mongodb.find_one('users', {'username': username})
    if user_settings and user_settings.get('handlungsfelder'):
        user_handlungsfelder = user_settings['handlungsfelder']
        ticket_category = ticket.get('category', '')

        # Prüfe ob Ticket-Kategorie in den zugewiesenen Handlungsfeldern ist
        if ticket_category in user_handlungsfelder:
            return True

    return False

from flask_login import current_user
from docxtpl import DocxTemplate
import os
from bson import ObjectId
from typing import Union

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('tickets', 'create')
def create_ticket():
    """Erstellt ein neues Ticket"""
    try:
        if request.method == 'POST':
            ticket_data = request.form.to_dict()

            # Service für Ticket-Erstellung verwenden
            ticket_service = get_ticket_service()
            success, message, ticket_id = ticket_service.create_ticket(ticket_data, current_user.username)

            if success:
                flash(message, 'success')
                return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
            else:
                flash(message, 'error')

        # GET-Request: Formular anzeigen
        departments = get_departments_from_settings()
        categories = get_ticket_categories_from_settings()
        ticket_number = get_next_ticket_number()

        return render_template('tickets/create.html',
                             departments=departments,
                             categories=categories,
                             ticket_number=ticket_number)

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Tickets: {e}")
        flash('Fehler beim Erstellen des Tickets', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/view/<ticket_id>')
@login_required
def view_ticket(ticket_id):
    """Zeigt ein Ticket an"""
    try:
        ticket_service = get_ticket_service()
        ticket = ticket_service.get_ticket_by_id(ticket_id)

        if not ticket:
            flash('Ticket nicht gefunden', 'error')
            return redirect(url_for('dashboard.index'))

        # Berechtigung prüfen
        if not check_ticket_permission(ticket, current_user.username, getattr(current_user, 'role', None)):
            flash('Keine Berechtigung für dieses Ticket', 'error')
            return redirect(url_for('dashboard.index'))

        # Nachrichten laden
        messages = ticket_service.get_ticket_messages(ticket_id)

        # Zuweisungen laden
        assignments = ticket_service.get_ticket_assignments(ticket_id)

        # Auftragsdetails laden
        auftrag_details = None
        if ticket.get('auftrag_details'):
            auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id})

        return render_template('tickets/view.html',
                             ticket=ticket,
                             messages=messages,
                             assignments=assignments,
                             auftrag_details=auftrag_details)

    except Exception as e:
        logger.error(f"Fehler beim Laden des Tickets {ticket_id}: {e}")
        flash('Fehler beim Laden des Tickets', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/<ticket_id>/messages')
@login_required
def get_ticket_messages(ticket_id):
    """Holt Nachrichten für ein Ticket (AJAX)"""
    try:
        ticket_service = get_ticket_service()
        ticket = ticket_service.get_ticket_by_id(ticket_id)

        if not ticket or not check_ticket_permission(ticket, current_user.username, getattr(current_user, 'role', None)):
            return jsonify({'error': 'Keine Berechtigung'}), 403

        messages = ticket_service.get_ticket_messages(ticket_id)
        return jsonify({'messages': messages})

    except Exception as e:
        logger.error(f"Fehler beim Laden der Ticket-Nachrichten: {e}")
        return jsonify({'error': 'Fehler beim Laden der Nachrichten'}), 500

@bp.route('/<ticket_id>/add-message', methods=['POST'])
@login_required
def add_ticket_message(ticket_id):
    """Fügt eine Nachricht zu einem Ticket hinzu"""
    try:
        ticket_service = get_ticket_service()
        ticket = ticket_service.get_ticket_by_id(ticket_id)

        if not ticket or not check_ticket_permission(ticket, current_user.username, getattr(current_user, 'role', None)):
            flash('Keine Berechtigung', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        message = request.form.get('message', '').strip()
        if not message:
            flash('Nachricht darf nicht leer sein', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

        success, message_text = ticket_service.add_message_to_ticket(
            ticket_id, message, current_user.username
        )

        if success:
            flash('Nachricht hinzugefügt', 'success')
        else:
            flash(message_text, 'error')

        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Nachricht: {e}")
        flash('Fehler beim Hinzufügen der Nachricht', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))

@bp.route('/<id>')
@login_required
def ticket_detail(id):
    """Zeigt Ticket-Details an (Legacy-Route)"""
    return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/<id>/delete', methods=['POST'])
@login_required
def delete_ticket(id):
    """Löscht ein Ticket"""
    try:
        ticket_service = get_ticket_service()
        ticket = ticket_service.get_ticket_by_id(id)

        if not ticket:
            flash('Ticket nicht gefunden', 'error')
            return redirect(url_for('dashboard.index'))

        # Nur Ersteller oder Admin können löschen
        if (ticket.get('created_by') != current_user.username and
            getattr(current_user, 'role', None) != 'admin'):
            flash('Keine Berechtigung zum Löschen', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=id))

        permanent = request.form.get('permanent', 'false').lower() == 'true'
        success, message = ticket_service.delete_ticket(id, current_user.username, permanent)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('dashboard.index'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Tickets {id}: {e}")
        flash('Fehler beim Löschen des Tickets', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/<id>/update-status', methods=['POST'])
@login_required
def update_ticket_status(id):
    """Aktualisiert den Status eines Tickets"""
    try:
        new_status = request.form.get('status')
        if not new_status:
            flash('Status ist erforderlich', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=id))

        ticket_service = get_ticket_service()
        success, message = ticket_service.update_ticket_status(id, new_status, current_user.username)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('tickets.view_ticket', ticket_id=id))

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Ticket-Status: {e}")
        flash('Fehler beim Aktualisieren des Status', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/<id>/update-assignment', methods=['POST'])
@login_required
def update_ticket_assignment(id):
    """Aktualisiert die Zuweisung eines Tickets"""
    try:
        assigned_users = request.form.getlist('assigned_users[]')
        if not assigned_users:
            assigned_users = []

        ticket_service = get_ticket_service()
        success, message = ticket_service.assign_ticket_multiple(id, assigned_users, current_user.username)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('tickets.view_ticket', ticket_id=id))

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Ticket-Zuweisung: {e}")
        flash('Fehler beim Aktualisieren der Zuweisung', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/<id>/update-responsible', methods=['POST'])
@login_required
def update_ticket_responsible(id):
    """Aktualisiert die verantwortliche Person eines Tickets"""
    try:
        responsible_username = request.form.get('responsible')

        ticket_service = get_ticket_service()
        success, message = ticket_service.update_responsible(id, responsible_username, current_user.username)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('tickets.view_ticket', ticket_id=id))

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der verantwortlichen Person: {e}")
        flash('Fehler beim Aktualisieren der verantwortlichen Person', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/<id>/update-due-date', methods=['POST'])
@login_required
def update_ticket_due_date(id):
    """Aktualisiert das Fälligkeitsdatum eines Tickets"""
    try:
        due_date = request.form.get('due_date')

        # Datum parsen und validieren
        if due_date:
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Ungültiges Datumsformat', 'error')
                return redirect(url_for('tickets.view_ticket', ticket_id=id))

            # Ticket aktualisieren
            mongodb.update_one(
                'tickets',
                {'_id': convert_id_for_query(id)},
                {
                    '$set': {
                        'due_date': due_date_obj,
                        'updated_at': datetime.now(),
                        'updated_by': current_user.username
                    }
                }
            )

            flash('Fälligkeitsdatum aktualisiert', 'success')
        else:
            # Datum entfernen
            mongodb.update_one(
                'tickets',
                {'_id': convert_id_for_query(id)},
                {
                    '$unset': {'due_date': ''},
                    '$set': {
                        'updated_at': datetime.now(),
                        'updated_by': current_user.username
                    }
                }
            )

            flash('Fälligkeitsdatum entfernt', 'success')

        return redirect(url_for('tickets.view_ticket', ticket_id=id))

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Fälligkeitsdatums: {e}")
        flash('Fehler beim Aktualisieren des Fälligkeitsdatums', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/<id>/update-details', methods=['POST'])
@login_required
def update_ticket_details(id):
    """Aktualisiert die Details eines Tickets"""
    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'normal')
        category = request.form.get('category', '')

        if not title:
            flash('Titel ist erforderlich', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=id))

        update_data = {
            'title': title,
            'description': description,
            'priority': priority,
            'category': category if category else None,
            'updated_at': datetime.now(),
            'updated_by': current_user.username
        }

        mongodb.update_one(
            'tickets',
            {'_id': convert_id_for_query(id)},
            {'$set': update_data}
        )

        flash('Ticket-Details aktualisiert', 'success')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Ticket-Details: {e}")
        flash('Fehler beim Aktualisieren der Details', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/<id>/export')
@login_required
def export_ticket(id):
    """Exportiert ein Ticket als Word-Dokument"""
    try:
        ticket_service = get_ticket_service()
        ticket = ticket_service.get_ticket_by_id(id)

        if not ticket or not check_ticket_permission(ticket, current_user.username, getattr(current_user, 'role', None)):
            flash('Keine Berechtigung', 'error')
            return redirect(url_for('dashboard.index'))

        # Word-Dokument erstellen
        from docxtpl import DocxTemplate
        import tempfile
        import os

        # Template laden (vereinfacht)
        doc = DocxTemplate("templates/ticket_template.docx")

        # Daten für Template
        context = {
            'ticket_number': ticket.get('ticket_number', ''),
            'title': ticket.get('title', ''),
            'description': ticket.get('description', ''),
            'status': ticket.get('status', ''),
            'priority': ticket.get('priority', ''),
            'created_by': ticket.get('created_by', ''),
            'created_at': ticket.get('created_at', ''),
            'assigned_to': ticket.get('assigned_to', ''),
        }

        doc.render(context)

        # Temporäre Datei erstellen
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
            doc.save(tmp_file.name)
            tmp_file_path = tmp_file.name

        # Datei senden
        from flask import send_file
        response = send_file(
            tmp_file_path,
            as_attachment=True,
            download_name=f"Ticket_{ticket.get('ticket_number', id)}.docx"
        )

        # Cleanup in separate function
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(tmp_file_path)
            except Exception:
                pass

        return response

    except Exception as e:
        logger.error(f"Fehler beim Exportieren des Tickets: {e}")
        flash('Fehler beim Exportieren des Tickets', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/<id>/note', methods=['POST'])
@login_required
def add_ticket_note(id):
    """Fügt eine Notiz zu einem Ticket hinzu"""
    try:
        note_text = request.form.get('note', '').strip()
        if not note_text:
            flash('Notiz darf nicht leer sein', 'error')
            return redirect(url_for('tickets.view_ticket', ticket_id=id))

        note_data = {
            'ticket_id': id,
            'note': note_text,
            'created_by': current_user.username,
            'created_at': datetime.now()
        }

        mongodb.insert_one('ticket_notes', note_data)

        flash('Notiz hinzugefügt', 'success')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Notiz: {e}")
        flash('Fehler beim Hinzufügen der Notiz', 'error')
        return redirect(url_for('tickets.view_ticket', ticket_id=id))

@bp.route('/auftrag-neu', methods=['GET', 'POST'])
@login_required
@permission_required('tickets', 'create')
def create_auftrag_ticket():
    """Erstellt ein neues Auftrags-Ticket"""
    try:
        if request.method == 'POST':
            ticket_data = request.form.to_dict()
            ticket_data['category'] = 'Auftrag'  # Spezielle Kategorie für Aufträge

            ticket_service = get_ticket_service()
            success, message, ticket_id = ticket_service.create_ticket(ticket_data, current_user.username)

            if success:
                flash(message, 'success')
                return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
            else:
                flash(message, 'error')

        # GET-Request: Formular für Auftrags-Ticket
        departments = get_departments_from_settings()
        ticket_number = get_next_ticket_number()

        return render_template('tickets/create_auftrag.html',
                             departments=departments,
                             ticket_number=ticket_number)

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Auftrags-Tickets: {e}")
        flash('Fehler beim Erstellen des Auftrags-Tickets', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/auftrag-extern', methods=['GET', 'POST'])
@login_required
@permission_required('tickets', 'create')
def create_extern_auftrag_ticket():
    """Erstellt ein neues externes Auftrags-Ticket"""
    try:
        if request.method == 'POST':
            ticket_data = request.form.to_dict()
            ticket_data['category'] = 'Externer Auftrag'

            ticket_service = get_ticket_service()
            success, message, ticket_id = ticket_service.create_ticket(ticket_data, current_user.username)

            if success:
                flash(message, 'success')
                return redirect(url_for('tickets.view_ticket', ticket_id=ticket_id))
            else:
                flash(message, 'error')

        # GET-Request: Formular für externes Auftrags-Ticket
        departments = get_departments_from_settings()
        ticket_number = get_next_ticket_number()

        return render_template('tickets/create_extern_auftrag.html',
                             departments=departments,
                             ticket_number=ticket_number)

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des externen Auftrags-Tickets: {e}")
        flash('Fehler beim Erstellen des externen Auftrags-Tickets', 'error')
        return redirect(url_for('dashboard.index'))

@bp.route('/ticket_categories')
@login_required
def get_ticket_categories():
    """Gibt verfügbare Ticket-Kategorien zurück (AJAX)"""
    try:
        categories = get_ticket_categories_from_settings()
        return jsonify({'categories': categories})
    except Exception as e:
        logger.error(f"Fehler beim Laden der Ticket-Kategorien: {e}")
        return jsonify({'error': 'Fehler beim Laden der Kategorien'}), 500

@bp.route('/<id>/auftrag-details')
@login_required
def get_auftrag_details(id):
    """Holt Auftragsdetails für ein Ticket (AJAX)"""
    try:
        ticket_service = get_ticket_service()
        ticket = ticket_service.get_ticket_by_id(id)

        if not ticket or not check_ticket_permission(ticket, current_user.username, getattr(current_user, 'role', None)):
            return jsonify({'error': 'Keine Berechtigung'}), 403

        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': id})
        if auftrag_details:
            auftrag_details['_id'] = str(auftrag_details['_id'])

        return jsonify({'auftrag_details': auftrag_details})

    except Exception as e:
        logger.error(f"Fehler beim Laden der Auftragsdetails: {e}")
        return jsonify({'error': 'Fehler beim Laden der Auftragsdetails'}), 500

@bp.route('/<id>/update-ticket', methods=['POST'])
@login_required
def update_ticket(id):
    """Aktualisiert ein komplettes Ticket (Legacy-Route)"""
    return redirect(url_for('tickets.update_ticket_details', id=id))

# Produktionsrelevante Routen sind hier. Debug-Routen wurden entfernt.
