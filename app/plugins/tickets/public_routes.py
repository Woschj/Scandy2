from flask import Blueprint, request, jsonify, render_template, current_app, redirect, url_for, flash, g
from flask_login import current_user
from datetime import datetime
from app.utils.decorators import login_required, admin_required
from app.utils.permissions import permission_required
from app.models.mongodb_database import mongodb, is_feature_enabled
from app.utils.id_helpers import convert_id_for_query
from bson import ObjectId
import logging
from app.services.ticket_category_service import ticket_category_service
from app.utils.database_helpers import get_departments_from_settings, get_categories_from_settings, get_ticket_categories_from_settings, get_next_ticket_number

from .routes import bp, get_ticket_service

logger = logging.getLogger(__name__)

@bp.route('/auftrag-neu', methods=['GET', 'POST'])
@login_required
@permission_required('tickets', 'view')
def public_create_order():
    """Interne Auftragserstellung für eingeloggte Benutzer."""
    if request.method == 'GET':
        from app.services.ticket_category_service import ticket_category_service
        # Alle Abteilungen für die Auswahl (nicht nur erlaubte)
        departments_all = get_departments_from_settings() or []
        selected_department = request.args.get('target_department')
        if selected_department:
            categories = ticket_category_service.get_ticket_categories_for_department(selected_department)
        else:
            categories = []  # initial leer, bis im Formular eine Abteilung gewählt wird
        return render_template('tickets/create_auftrag.html',
                             categories=categories,
                             selected_department=selected_department,
                             departments_all=departments_all,
                             error=None)
    return _handle_auftrag_creation()


@bp.route('/auftrag-extern', methods=['GET', 'POST'])
def external_create_order():
    """Externe Auftragserstellung ohne Login für externe Einbindungen."""
    if request.method == 'POST':
        return _handle_auftrag_creation(external=True)
    from app.services.ticket_category_service import ticket_category_service
    selected_department = request.args.get('target_department')
    if selected_department:
        categories = ticket_category_service.get_ticket_categories_for_department(selected_department)
    else:
        categories = []
    return render_template('tickets/auftrag_external_embed.html',
                         categories=categories,
                         selected_department=selected_department,
                         error=None)


def _handle_auftrag_creation(external=False):
    """Gemeinsame Logik für interne und externe Auftragserstellung."""
    if request.method == 'POST':
        try:
            # Hole die Formulardaten
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            priority = request.form.get('priority', 'normal')
            due_date = request.form.get('due_date')
            estimated_time = request.form.get('estimated_time')
            auftraggeber_name = request.form.get('name', '')  # Name des Auftraggebers (Feldname im Template: 'name')
            kontakt = request.form.get('kontakt', '')  # Kontaktdaten
            bereich = request.form.get('bereich', '')  # Bereich
            auftraggeber_typ = request.form.get('auftraggeber_typ', 'extern')  # Intern/Extern
            # Ziel-Abteilung (optional, nur intern relevant)
            target_department = request.form.get('target_department')
            current_dept = getattr(g, 'current_department', None)
            if target_department == '':
                target_department = None
            # Verifiziere, dass die gewählte Kategorie zur gewählten Abteilung gehört
            try:
                from app.services.ticket_category_service import ticket_category_service
                effective_dept = target_department or current_dept
                valid_categories = ticket_category_service.get_ticket_categories_for_department(effective_dept)
                if category and category not in valid_categories:
                    # Ungültige Kategorie für die gewählte Abteilung -> Fehlermeldung und aktuelle Kategorien der gewählten Abteilung laden
                    categories = valid_categories
                    error_msg = 'Das gewählte Handlungsfeld gehört nicht zur ausgewählten Abteilung.'
                    if external or not current_user.is_authenticated:
                        return render_template('tickets/auftrag_external_embed.html',
                                             categories=categories,
                                             error=error_msg)
                    else:
                        # Alle Abteilungen erneut bereitstellen
                        departments_all = get_departments_from_settings() or []
                        return render_template('tickets/create_auftrag.html',
                                             categories=categories,
                                             departments_all=departments_all,
                                             selected_department=effective_dept,
                                             error=error_msg)
            except Exception:
                pass

            # Validiere die Pflichtfelder
            if not title:
                from app.services.ticket_category_service import ticket_category_service
                categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
                if external or not current_user.is_authenticated:
                    return render_template('tickets/auftrag_external_embed.html',
                                         categories=categories,
                                         error='Titel ist erforderlich.')
                else:
                    departments_all = get_departments_from_settings() or []
                    return render_template('tickets/create_auftrag.html',
                                         categories=categories,
                                         departments_all=departments_all,
                                         error='Titel ist erforderlich.')

            if not description:
                from app.services.ticket_category_service import ticket_category_service
                categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
                if external or not current_user.is_authenticated:
                    return render_template('tickets/auftrag_external_embed.html',
                                         categories=categories,
                                         error='Beschreibung ist erforderlich.')
                else:
                    departments_all = get_departments_from_settings() or []
                    return render_template('tickets/create_auftrag.html',
                                         categories=categories,
                                         departments_all=departments_all,
                                         error='Beschreibung ist erforderlich.')

            # Kategorie ist optional, daher entfernen wir die Validierung
            # if not category:
            #     flash('Kategorie ist erforderlich.', 'error')
            #     return redirect(url_for('tickets.public_create_order'))

            # Erstelle das Ticket
            ticket_data = {
                'title': title,
                'description': description,
                'priority': priority,
                'created_by': auftraggeber_name or 'Gast',  # Verwende den eingegebenen Namen oder "Gast" als Fallback
                'category': category,
                'due_date': due_date,
                'estimated_time': estimated_time,
                'status': 'offen',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'ticket_number': get_next_ticket_number(),  # Neue Auftragsnummer
                'is_external': not current_user.is_authenticated,  # Markiere externe Aufträge
                'department': (target_department or current_dept)
            }

            result = mongodb.insert_one('tickets', ticket_data)
            ticket_id = str(result)

            # Erstelle auch die Auftragsdetails mit dem Namen des Auftraggebers
            auftrag_details_data = {
                'ticket_id': ticket_id,  # Verwende die String-ID direkt
                'bereich': bereich or category,  # Verwende bereich oder category als Fallback
                'auftraggeber_intern': auftraggeber_typ == 'intern',
                'auftraggeber_extern': auftraggeber_typ == 'extern',
                'auftraggeber_name': auftraggeber_name,
                'kontakt': kontakt,
                'auftragsbeschreibung': description,
                'fertigstellungstermin': due_date,
                'gesamtsumme': 0
            }

            mongodb.insert_one('auftrag_details', auftrag_details_data)

            # Sende Bestätigungs-E-Mail
            if kontakt:  # Nur wenn Kontaktdaten vorhanden sind
                try:
                    from app.utils.email_utils import send_auftrag_confirmation_email
                    # Datum formatieren für E-Mail
                    ticket_data_for_email = ticket_data.copy()
                    if ticket_data_for_email.get('created_at'):
                        ticket_data_for_email['created_at'] = ticket_data_for_email['created_at'].strftime('%d.%m.%Y %H:%M Uhr')

                    send_auftrag_confirmation_email(
                        ticket_data=ticket_data_for_email,
                        auftrag_details=auftrag_details_data,
                        recipient_email=kontakt
                    )
                except Exception as email_error:
                    logger.error(f"Fehler beim Senden der Bestätigungs-E-Mail: {str(email_error)}")
                    # E-Mail-Fehler soll den Auftrag nicht verhindern

            # Für alle Benutzer zur Bestätigungsseite
            return render_template('tickets/public_success.html',
                                 ticket_number=ticket_data['ticket_number'],
                                 ticket=ticket_data)

        except Exception as e:
            logging.error(f"Fehler bei der öffentlichen Auftragserstellung: [Interner Fehler]", exc_info=True)
            from app.services.ticket_category_service import ticket_category_service
            categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
            if external or not current_user.is_authenticated:
                return render_template('tickets/auftrag_external_embed.html',
                                     categories=categories,
                                     error='Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.')
            else:
                flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')
                return redirect(url_for('tickets.public_create_order'))

    # Hole die Kategorien für das Formular (abteilungsgebunden)
    from app.services.ticket_category_service import ticket_category_service
    categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
    departments_all = get_departments_from_settings() or []

    if external or not current_user.is_authenticated:
        return render_template('tickets/auftrag_external_embed.html',
                             categories=categories,
                             error=None)
    return render_template('tickets/create_auftrag.html',
                         categories=categories,
                         departments_all=departments_all,
                         priority_colors={
                             'niedrig': 'secondary',
                             'normal': 'primary',
                             'hoch': 'error',
                             'dringend': 'error'
                         })


@bp.route('/ticket_categories')
def public_ticket_categories():
    """Gibt Ticket-Kategorien (Handlungsfelder) für eine angegebene Abteilung zurück.
    Öffentlich nutzbar für Formular-UI (kein Login erforderlich)."""
    try:
        req_dept = request.args.get('dept')
        if not req_dept:
            return jsonify({'success': True, 'categories': [], 'department': None})
        from app.services.handlungsfeld_service import handlungsfeld_service
        categories = handlungsfeld_service.get_handlungsfelder_for_department(req_dept)
        return jsonify({'success': True, 'department': req_dept, 'categories': [{'name': n} for n in categories]})
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Ticket-Kategorien (public): [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Fehler beim Laden der Ticket-Kategorien'})
