"""
Admin Tickets Module - Ticket-Verwaltung

Dieses Modul enthält alle Admin-Funktionen für:
- Ticket-Management
- Ticket-Kategorien
- Ticket-Nachrichten
- Ticket-Export
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import current_user
from app.utils.decorators import admin_required
from app.models.mongodb_database import mongodb
from app.services.admin_ticket_service import AdminTicketService
from app.utils.database_helpers import get_ticket_categories_from_settings
from docxtpl import DocxTemplate
import logging
from datetime import datetime
from io import BytesIO
import json

logger = logging.getLogger(__name__)

bp = Blueprint('admin_tickets', __name__, url_prefix='/admin')

@bp.route('/tickets/<ticket_id>')
@admin_required
def ticket_details(ticket_id):
    """Ticket-Details anzeigen (Admin-Ansicht)"""
    try:
        # Ticket laden
        ticket = mongodb.find_one('tickets', {'_id': ticket_id})
        if not ticket:
            flash('Ticket nicht gefunden', 'error')
            return redirect(url_for('tickets.view', ticket_id=1))  # Fallback

        # Zusätzliche Daten laden
        messages = list(mongodb.find('ticket_messages',
                                   {'ticket_id': ticket_id},
                                   sort=[('created_at', 1)]))
        notes = list(mongodb.find('ticket_notes',
                                {'ticket_id': ticket_id},
                                sort=[('created_at', -1)]))

        # Auftragsdetails laden
        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id})
        material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id}))

        # Zuweisungen laden
        assigned_users = list(mongodb.find('ticket_assignments', {'ticket_id': ticket_id}))

        # Nutzer für Zuweisung laden
        users = list(mongodb.find('users', {'is_active': True}))
        categories = get_ticket_categories_from_settings()

        return render_template('admin/ticket_detail.html',
                             ticket=ticket,
                             messages=messages,
                             notes=notes,
                             auftrag_details=auftrag_details,
                             material_list=material_list,
                             assigned_users=assigned_users,
                             users=users,
                             categories=categories)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Ticket-Details {ticket_id}: {str(e)}")
        flash('Fehler beim Laden der Ticket-Details', 'error')
        return redirect(url_for('tickets.view', ticket_id=1))

@bp.route('/tickets/<ticket_id>/message', methods=['POST'])
@admin_required
def add_ticket_message(ticket_id):
    """Nachricht zu Ticket hinzufügen"""
    try:
        message_text = request.form.get('message', '').strip()

        if not message_text:
            return jsonify({'success': False, 'message': 'Nachricht darf nicht leer sein'}), 400

        message_data = {
            'ticket_id': ticket_id,
            'message': message_text,
            'sender': current_user.username,
            'sender_role': current_user.role,
            'created_at': datetime.now(),
            'is_admin_message': True
        }

        # Nachricht speichern
        message_id = mongodb.insert_one('ticket_messages', message_data)

        # Ticket aktualisieren
        mongodb.update_one('tickets',
                         {'_id': ticket_id},
                         {'$set': {'updated_at': datetime.now()}})

        return jsonify({
            'success': True,
            'message': 'Nachricht erfolgreich hinzugefügt',
            'message_id': str(message_id)
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Nachricht zu Ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Speichern der Nachricht: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/note', methods=['POST'])
@admin_required
def add_ticket_note(ticket_id):
    """Notiz zu Ticket hinzufügen"""
    try:
        note_text = request.form.get('note', '').strip()

        if not note_text:
            return jsonify({'success': False, 'message': 'Notiz darf nicht leer sein'}), 400

        note_data = {
            'ticket_id': ticket_id,
            'note': note_text,
            'author': current_user.username,
            'created_at': datetime.now(),
            'is_admin_note': True
        }

        # Notiz speichern
        mongodb.insert_one('ticket_notes', note_data)

        # Ticket aktualisieren
        mongodb.update_one('tickets',
                         {'_id': ticket_id},
                         {'$set': {'updated_at': datetime.now()}})

        return jsonify({
            'success': True,
            'message': 'Notiz erfolgreich hinzugefügt'
        })

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Notiz zu Ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Speichern der Notiz: {str(e)}'
        }), 500

@bp.route('/tickets/<ticket_id>/update', methods=['POST'])
@admin_required
def update_ticket(ticket_id):
    """Ticket aktualisieren"""
    try:
        update_data = {
            'title': request.form.get('title', '').strip(),
            'description': request.form.get('description', '').strip(),
            'status': request.form.get('status', 'offen'),
            'priority': request.form.get('priority', 'normal'),
            'category': request.form.get('category', ''),
            'assigned_to': request.form.get('assigned_to', ''),
            'updated_at': datetime.now()
        }

        # Nicht-leere Felder filtern
        update_data = {k: v for k, v in update_data.items() if v != ''}

        result = mongodb.update_one('tickets',
                                  {'_id': ticket_id},
                                  {'$set': update_data})

        if result.modified_count > 0:
            return jsonify({
                'success': True,
                'message': 'Ticket erfolgreich aktualisiert'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ticket nicht gefunden oder keine Änderungen'
            }), 404

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Tickets {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Aktualisieren: {str(e)}'
        }), 500

@bp.route('/tickets/<id>/export')
@admin_required
def export_ticket(id):
    """Ticket als Dokument exportieren"""
    try:
        # Ticket laden
        ticket = mongodb.find_one('tickets', {'_id': id})
        if not ticket:
            flash('Ticket nicht gefunden', 'error')
            return redirect(url_for('tickets.view', ticket_id=id))

        # Template laden und Daten einfügen
        template_path = os.path.join(current_app.root_path, 'templates', 'ticket_export_template.docx')

        if not os.path.exists(template_path):
            # Fallback: Einfache Text-Generierung
            output = BytesIO()
            content = f"""
Ticket #{ticket.get('ticket_number', id)}

Titel: {ticket.get('title', 'N/A')}
Status: {ticket.get('status', 'N/A')}
Priorität: {ticket.get('priority', 'N/A')}

Beschreibung:
{ticket.get('description', 'N/A')}

Erstellt am: {ticket.get('created_at', 'N/A')}
Erstellt von: {ticket.get('created_by', 'N/A')}
"""
            output.write(content.encode('utf-8'))
            output.seek(0)

            return send_file(
                output,
                as_attachment=True,
                download_name=f'ticket_{ticket.get("ticket_number", id)}.txt',
                mimetype='text/plain'
            )

        # Word-Dokument generieren
        doc = DocxTemplate(template_path)
        context = {
            'ticket_number': ticket.get('ticket_number', id),
            'title': ticket.get('title', 'N/A'),
            'status': ticket.get('status', 'N/A'),
            'priority': ticket.get('priority', 'N/A'),
            'description': ticket.get('description', 'N/A'),
            'created_by': ticket.get('created_by', 'N/A'),
            'created_at': ticket.get('created_at', 'N/A'),
            'assigned_to': ticket.get('assigned_to', 'N/A')
        }

        doc.render(context)
        output = BytesIO()
        doc.save(output)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name=f'ticket_{ticket.get("ticket_number", id)}.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        logger.error(f"Fehler beim Exportieren des Tickets {id}: {str(e)}")
        flash('Fehler beim Exportieren des Tickets', 'error')
        return redirect(url_for('tickets.view', ticket_id=id))

@bp.route('/tickets/<ticket_id>/update-details', methods=['POST'])
@admin_required
def update_ticket_details(ticket_id):
    """Auftragsdetails aktualisieren"""
    try:
        # Auftragsdetails aktualisieren
        details_data = {
            'customer_name': request.form.get('customer_name', ''),
            'customer_contact': request.form.get('customer_contact', ''),
            'project_details': request.form.get('project_details', ''),
            'estimated_hours': float(request.form.get('estimated_hours', 0)),
            'actual_hours': float(request.form.get('actual_hours', 0)),
            'updated_at': datetime.now()
        }

        mongodb.update_one('auftrag_details',
                         {'ticket_id': ticket_id},
                         {'$set': details_data},
                         upsert=True)

        # Materialliste aktualisieren
        material_data = request.form.get('materials', '[]')
        try:
            materials = json.loads(material_data)
            # Vorhandene Materialien löschen
            mongodb.delete_many('auftrag_material', {'ticket_id': ticket_id})

            # Neue Materialien einfügen
            for material in materials:
                material['ticket_id'] = ticket_id
                mongodb.insert_one('auftrag_material', material)
        except json.JSONDecodeError:
            logger.warning(f"Ungültige Materialdaten für Ticket {ticket_id}")

        return jsonify({
            'success': True,
            'message': 'Auftragsdetails erfolgreich aktualisiert'
        })

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren der Auftragsdetails für Ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Aktualisieren: {str(e)}'
        }), 500

# Ticket-Kategorien-Management
@bp.route('/add_ticket_category', methods=['POST'])
@admin_required
def add_ticket_category():
    """Ticket-Kategorie hinzufügen"""
    try:
        category_name = request.form.get('category_name', '').strip()

        if not category_name:
            flash('Kategoriename ist erforderlich', 'error')
            return redirect(url_for('admin_system.system_settings'))

        # Bestehende Kategorien laden
        categories_data = mongodb.find_one('settings', {'key': 'ticket_categories'})
        categories = categories_data.get('value', []) if categories_data else []

        if category_name in categories:
            flash('Kategorie existiert bereits', 'warning')
            return redirect(url_for('admin_system.system_settings'))

        categories.append(category_name)

        # Aktualisierte Kategorien speichern
        mongodb.update_one('settings',
                         {'key': 'ticket_categories'},
                         {'$set': {'value': categories, 'updated_at': datetime.now()}},
                         upsert=True)

        flash('Ticket-Kategorie erfolgreich hinzugefügt', 'success')
        return redirect(url_for('admin_system.system_settings'))

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Ticket-Kategorie: {str(e)}")
        flash('Fehler beim Hinzufügen der Kategorie', 'error')
        return redirect(url_for('admin_system.system_settings'))

@bp.route('/delete_ticket_category/<category>', methods=['POST'])
@admin_required
def delete_ticket_category(category):
    """Ticket-Kategorie löschen"""
    try:
        # Bestehende Kategorien laden
        categories_data = mongodb.find_one('settings', {'key': 'ticket_categories'})
        categories = categories_data.get('value', []) if categories_data else []

        if category not in categories:
            flash('Kategorie nicht gefunden', 'error')
            return redirect(url_for('admin_system.system_settings'))

        categories.remove(category)

        # Aktualisierte Kategorien speichern
        mongodb.update_one('settings',
                         {'key': 'ticket_categories'},
                         {'$set': {'value': categories, 'updated_at': datetime.now()}})

        flash('Ticket-Kategorie erfolgreich gelöscht', 'success')
        return redirect(url_for('admin_system.system_settings'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen der Ticket-Kategorie {category}: {str(e)}")
        flash('Fehler beim Löschen der Kategorie', 'error')
        return redirect(url_for('admin_system.system_settings'))
