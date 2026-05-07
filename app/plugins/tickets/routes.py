from app.utils.id_helpers import convert_id_for_query, find_document_by_id
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash, abort, send_file, render_template_string, current_app
from app.models.mongodb_models import MongoDBTicket
from app.models.mongodb_database import mongodb, is_feature_enabled
from flask import g
from app.utils.decorators import login_required, admin_required, not_teilnehmer_required
from app.utils.permissions import permission_required
from app.utils.database_helpers import get_ticket_categories_from_settings, get_categories_from_settings, get_next_ticket_number, get_departments_from_settings
from app.models.user import User
from app.services.ticket_service import TicketService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Ticket Service Instanz
def get_ticket_service():
    """Gibt eine Instanz des TicketService zurück"""
    return TicketService()

from flask_login import current_user
from docxtpl import DocxTemplate
import os
from bson import ObjectId
from typing import Union

bp = Blueprint('tickets', __name__)



# Debug Routen

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('tickets', 'create')
def create():
    """Erstellt ein neues Ticket"""
    # Prüfe ob Ticketsystem aktiviert ist
    if not is_feature_enabled('ticket_system'):
        flash('Ticketsystem ist deaktiviert', 'error')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            # Ticket-Daten sammeln
            ticket_data = {
                'title': request.form.get('title', '').strip(),
                'description': request.form.get('description', '').strip(),
                'category': request.form.get('category', '').strip(),
                'priority': request.form.get('priority', 'normal'),
                'status': 'offen',
                'created_by': current_user.id,
                'created_at': datetime.now(),
                'assigned_to': None,
                'department': request.form.get('department', '').strip()
            }
            
            # Validierung
            if not ticket_data['title'] or not ticket_data['description']:
                flash('Titel und Beschreibung sind erforderlich', 'error')
                return render_template('tickets/create.html', form_data=ticket_data)
            
            # Ticket erstellen
            ticket_service = get_ticket_service()
            success, message, ticket_id = ticket_service.create_ticket(ticket_data)
            
            if success:
                flash(message, 'success')
                return redirect(url_for('tickets.detail', ticket_id=ticket_id))
            else:
                flash(message, 'error')
                # Bei Fehlern müssen wir auch die Ticket-Listen laden
                from app.services.ticket_category_service import ticket_category_service
                categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
                departments = get_departments_from_settings()
                show_all_tickets = current_user.role in ['admin', 'mitarbeiter']
                return render_template('tickets/create.html', 
                                     form_data=ticket_data,
                                     categories=categories,
                                     departments=departments,
                                     show_all_tickets=show_all_tickets,
                                     open_tickets=[],
                                     assigned_tickets=[],
                                     all_tickets=[],
                                     status_colors={},
                                     priority_colors={},
                                     now=datetime.now())
                
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Tickets: [Interner Fehler]")
            flash('Fehler beim Erstellen des Tickets', 'error')
            # Bei Fehlern müssen wir auch die Ticket-Listen laden
            from app.services.ticket_category_service import ticket_category_service
            categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
            departments = get_departments_from_settings()
            show_all_tickets = current_user.role in ['admin', 'mitarbeiter']
            return render_template('tickets/create.html', 
                                 form_data=ticket_data,
                                 categories=categories,
                                 departments=departments,
                                 show_all_tickets=show_all_tickets,
                                 open_tickets=[],
                                 assigned_tickets=[],
                                 all_tickets=[],
                                 status_colors={},
                                 priority_colors={},
                                 now=datetime.now())
    
    # GET Request - Formular anzeigen
    try:
        from app.services.ticket_category_service import ticket_category_service
        categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
        departments = get_departments_from_settings()
        
        # Prüfe ob der User ein Admin ist (für "Alle Tickets" Tab)
        show_all_tickets = current_user.role in ['admin', 'mitarbeiter']
        
        # Verwende Ticket-Service für korrekte Handlungsfeld-Filterung
        ticket_service = get_ticket_service()
        
        # Hole Handlungsfelder des Benutzers (für alle Rollen außer Admin)
        user_handlungsfelder = []
        if current_user.role != 'admin':
            # Hole Handlungsfelder aus der Benutzer-Konfiguration
            user_settings = mongodb.find_one('users', {'username': current_user.username})
            if user_settings and user_settings.get('handlungsfelder'):
                user_handlungsfelder = user_settings['handlungsfelder']
                print(f"DEBUG: Benutzer {current_user.username} (Rolle: {current_user.role}) hat Handlungsfelder: {user_handlungsfelder}")
            else:
                print(f"DEBUG: Benutzer {current_user.username} (Rolle: {current_user.role}) hat keine Handlungsfelder zugewiesen")
        
        # Lade Tickets mit korrekter Filterung
        tickets_data = ticket_service.get_tickets_by_user(
            username=current_user.username,
            role=current_user.role,
            handlungsfelder=user_handlungsfelder
        )
        
        open_tickets = tickets_data['open_tickets']
        assigned_tickets = tickets_data['assigned_tickets']
        all_tickets = tickets_data['all_tickets']
                
        # Status und Priorität Colors
        status_colors = {
            'offen': 'info',
            'in_bearbeitung': 'warning',
            'wartet_auf_antwort': 'warning',
            'gelöst': 'success',
            'geschlossen': 'ghost'
        }
        
        priority_colors = {
            'niedrig': 'ghost',
            'normal': 'info',
            'hoch': 'warning',
            'dringend': 'error'
        }
        
        return render_template('tickets/create.html',
                             categories=categories,
                             departments=departments,
                             show_all_tickets=show_all_tickets,
                             open_tickets=open_tickets,
                             assigned_tickets=assigned_tickets,
                             all_tickets=all_tickets,
                             status_colors=status_colors,
                             priority_colors=priority_colors,
                             now=datetime.now())
    except Exception as e:
        logger.error(f"Fehler beim Laden des Ticket-Formulars: [Interner Fehler]")
        flash('Fehler beim Laden des Formulars', 'error')
        return redirect(url_for('main.index'))

@bp.route('/view/<ticket_id>')
@login_required
@permission_required('tickets', 'view')
def view(ticket_id):
    """Zeigt die Details eines Tickets für den Benutzer."""
    logging.info(f"Lade Ticket {ticket_id} für Benutzer {current_user.username}")
    
    # Robuste ID-Behandlung für verschiedene ID-Typen
    ticket = find_document_by_id('tickets', ticket_id)
    
    if not ticket:
        logging.error(f"Ticket {ticket_id} nicht gefunden")
        flash('Ticket nicht gefunden.', 'error')
        return redirect(url_for('tickets.create'))
        
    # Prüfe ob der Benutzer berechtigt ist, das Ticket zu sehen
    has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))
    
    if not has_permission:
        logging.error(f"Benutzer {current_user.username} hat keine Berechtigung für Ticket {ticket_id}")
        flash('Sie haben keine Berechtigung, dieses Ticket zu sehen.', 'error')
        return redirect(url_for('tickets.create'))
    
    # Hole die Nachrichten für das Ticket
    logging.info(f"Hole Nachrichten für Ticket {ticket_id}")
    
    try:
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(ticket_id)
        
        messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id_for_query})
        messages = list(messages)
        
        # Sortiere Nachrichten nach Datum (älteste zuerst)
        messages.sort(key=lambda x: x.get('created_at', datetime.min))
        
        # Formatiere Datum für jede Nachricht
        for msg in messages:
            if isinstance(msg.get('created_at'), datetime):
                msg['formatted_date'] = msg['created_at'].strftime('%d.%m.%Y %H:%M')
            else:
                msg['formatted_date'] = str(msg.get('created_at', ''))
        
        logging.info(f"Nachrichtenabfrage ergab {len(messages)} Nachrichten")
        
        # Füge id-Feld hinzu (für Template-Kompatibilität)
        ticket['id'] = str(ticket['_id'])
        
        # Hole die Auftragsdetails
        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query})
        
        # Hole Materialliste
        material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query}))
        
        # Hole Arbeitsliste
        arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': ticket_id_for_query}))
        
        # Berechne die Summe der Arbeitsstunden aus der Arbeitsliste
        total_arbeitsstunden = 0
        if arbeit_list:
            for arbeit in arbeit_list:
                arbeitsstunden = arbeit.get('arbeitsstunden', 0)
                if isinstance(arbeitsstunden, (int, float)):
                    total_arbeitsstunden += arbeitsstunden
                elif isinstance(arbeitsstunden, str):
                    try:
                        total_arbeitsstunden += float(arbeitsstunden)
                    except ValueError:
                        pass
        
        # Formatiere das Fertigstellungstermin-Datum
        if auftrag_details and auftrag_details.get('fertigstellungstermin'):
            try:
                fertigstellungstermin = auftrag_details['fertigstellungstermin']
                if isinstance(fertigstellungstermin, str):
                    # Versuche verschiedene Datumsformate zu parsen
                    if 'T' in fertigstellungstermin:
                        fertigstellungstermin = datetime.strptime(fertigstellungstermin, '%Y-%m-%dT%H:%M')
                    else:
                        fertigstellungstermin = datetime.strptime(fertigstellungstermin, '%Y-%m-%d')
                    auftrag_details['fertigstellungstermin_formatted'] = fertigstellungstermin.strftime('%d.%m.%Y')
                elif isinstance(fertigstellungstermin, datetime):
                    auftrag_details['fertigstellungstermin_formatted'] = fertigstellungstermin.strftime('%d.%m.%Y')
                else:
                    auftrag_details['fertigstellungstermin_formatted'] = str(fertigstellungstermin)
            except (ValueError, TypeError):
                auftrag_details['fertigstellungstermin_formatted'] = str(auftrag_details['fertigstellungstermin'])
        
        # Füge die berechneten Arbeitsstunden zu den Auftragsdetails hinzu
        if auftrag_details:
            auftrag_details['total_arbeitsstunden'] = total_arbeitsstunden
            
            # Extrahiere nur die ausgeführten Arbeiten (ohne Stunden und Leistungskategorie)
            if auftrag_details.get('ausgefuehrte_arbeiten'):
                arbeit_zeilen = auftrag_details['ausgefuehrte_arbeiten'].split('\n')
                nur_arbeiten = []
                for zeile in arbeit_zeilen:
                    if zeile.strip():
                        teile = zeile.split('|')
                        if len(teile) > 0 and teile[0].strip():
                            nur_arbeiten.append(teile[0].strip())
                auftrag_details['ausgefuehrte_arbeiten_nur_text'] = '\n'.join(nur_arbeiten)
        
        # Hole Kategorien der aktuellen Abteilung
        from app.services.ticket_category_service import ticket_category_service
        categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))
        
        # Hole alle Benutzer für die Zuweisung (falls benötigt)
        users = mongodb.find('users', {'is_active': True})
        users = [dict(user) for user in users]
        
        # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
        assigned_users_raw = mongodb.find('ticket_assignments', {'ticket_id': ticket_id_for_query})
        assigned_users = [assignment['assigned_to'] for assignment in assigned_users_raw]
        
        # Falls keine Mehrfachzuweisungen vorhanden, verwende die Legacy-Zuweisung
        if not assigned_users and ticket.get('assigned_to'):
            assigned_users = [ticket['assigned_to']]
        
        return render_template('tickets/view.html', 
                             ticket=ticket, 
                             messages=messages,
                             auftrag_details=auftrag_details,
                             categories=categories,
                             workers=users,
                             assigned_users=assigned_users,
                             now=datetime.now(),
                             status_colors={
                                 'offen': 'info',
                                 'in_bearbeitung': 'warning',
                                 'wartet_auf_antwort': 'warning',
                                 'gelöst': 'success',
                                 'geschlossen': 'ghost'
                             })
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Nachrichten: [Interner Fehler]")
        flash('Fehler beim Laden der Nachrichten.', 'error')
        return redirect(url_for('tickets.create'))



@bp.route('/<id>')
@login_required
@permission_required('tickets', 'view')
def detail(id):
    """Zeigt die Details eines Tickets."""
    try:
        print(f"DEBUG: Ticket-Detail aufgerufen für ID: {id}")
        
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        
        if not ticket:
            print(f"DEBUG: Ticket nicht gefunden für ID: {id}")
            return render_template('404.html'), 404
        
        # Prüfe Berechtigungen
        has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))
        
        if not has_permission:
            flash('Sie haben keine Berechtigung, dieses Ticket zu sehen.', 'error')
            return redirect(url_for('tickets.create'))
        
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
        notes = mongodb.find('ticket_notes', {'ticket_id': convert_id_for_query(id)})

        # Hole die Nachrichten für das Ticket
        messages = mongodb.find('ticket_messages', {'ticket_id': convert_id_for_query(id)})

        # Hole die Auftragsdetails
        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': convert_id_for_query(id)})
        
        # Hole Materialliste
        material_list = list(mongodb.find('auftrag_material', {'ticket_id': convert_id_for_query(id)}))
        
        # Hole Arbeitsliste
        arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': convert_id_for_query(id)}))

        # Hole alle Benutzer aus der Hauptdatenbank und wandle sie in Dicts um
        users = mongodb.find('users', {'is_active': True})
        users = [dict(user) for user in users]

        # Hole alle zugewiesenen Nutzer (Mehrfachzuweisung)
        assigned_users_raw = mongodb.find('ticket_assignments', {'ticket_id': convert_id_for_query(id)})
        assigned_users = [assignment['assigned_to'] for assignment in assigned_users_raw]
        
        # Falls keine Mehrfachzuweisungen vorhanden, verwende die Legacy-Zuweisung
        if not assigned_users and ticket.get('assigned_to'):
            assigned_users = [ticket['assigned_to']]

        # Hole Kategorien der aktuellen Abteilung
        from app.services.ticket_category_service import ticket_category_service
        categories = ticket_category_service.get_ticket_categories_for_department(getattr(g, 'current_department', None))

        # Bestimme Berechtigungen
        can_edit = current_user.role in ['admin', 'mitarbeiter', 'teilnehmer'] or ticket.get('created_by') == current_user.username
        can_assign = current_user.role in ['admin', 'mitarbeiter']
        can_change_status = current_user.role in ['admin', 'mitarbeiter']
        can_delete = current_user.role in ['admin', 'mitarbeiter']

        return render_template('tickets/detail.html', 
                             ticket=ticket, 
                             notes=notes,
                             messages=messages,
                             users=users,
                             assigned_users=assigned_users,
                             auftrag_details=auftrag_details,
                             material_list=material_list,
                             categories=categories,
                             can_edit=can_edit,
                             can_assign=can_assign,
                             can_change_status=can_change_status,
                             can_delete=can_delete,
                             now=datetime.now())
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Ticket-Details: [Interner Fehler]")
        flash('Fehler beim Laden der Ticket-Details.', 'error')
        return redirect(url_for('tickets.create'))


def _get_auftrag_details_data(ticket, id):
    """Zentralisierte Logik zum Laden der Auftragsdetails, Notizen, Nachrichten und Arbeitslisten."""
    # Verwende die Ticket-ID für alle Abfragen
    ticket_id_for_query = convert_id_for_query(id)

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
    notes = mongodb.find('ticket_notes', {'ticket_id': ticket_id_for_query})

    # Hole die Nachrichten für das Ticket
    messages = mongodb.find('ticket_messages', {'ticket_id': ticket_id_for_query})

    # Hole die Auftragsdetails
    auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query})

    # Hole Materialliste
    material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query}))

    # Hole Arbeitsliste (Priorität: strukturierte DB-Einträge)
    arbeit_list = list(mongodb.find('auftrag_arbeit', {'ticket_id': ticket_id_for_query}))

    # Fallback: Verarbeite die ausgeführten Arbeiten aus den Auftragsdetails, falls DB-Liste leer ist
    if not arbeit_list and auftrag_details and auftrag_details.get('ausgefuehrte_arbeiten'):
        arbeit_zeilen = auftrag_details['ausgefuehrte_arbeiten'].split('\n')
        for zeile in arbeit_zeilen:
            if zeile.strip():
                teile = zeile.split('|')
                arbeit_list.append({
                    'arbeit': teile[0] if len(teile) > 0 else '',
                    'arbeitsstunden': float(teile[1]) if len(teile) > 1 and teile[1] else 0,
                    'leistungskategorie': teile[2] if len(teile) > 2 else ''
                })

    # Füge die Auftragsdetails zum Ticket hinzu, damit das Template darauf zugreifen kann
    if auftrag_details:
        ticket['auftrag_details'] = auftrag_details
        # Füge die Material- und Arbeitslisten hinzu
        ticket['auftrag_details']['material_list'] = material_list
        ticket['auftrag_details']['arbeit_list'] = arbeit_list
    else:
        # Falls keine Auftragsdetails vorhanden sind, verwende die Ticket-Daten als Fallback
        ticket['auftrag_details'] = {
            'bereich': ticket.get('category', ''),
            'auftraggeber_name': ticket.get('created_by', ''),
            'auftragsbeschreibung': ticket.get('description', ''),
            'material_list': material_list,
            'arbeit_list': arbeit_list
        }

    return ticket, notes, messages, auftrag_details, material_list, arbeit_list

@bp.route('/<id>/auftrag-details-modal')
@login_required
@permission_required('tickets', 'view')
def auftrag_details_modal(id):
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        
        if not ticket:
            return render_template('404.html'), 404
        
        ticket, notes, messages, auftrag_details, material_list, arbeit_list = _get_auftrag_details_data(ticket, id)

        return render_template('tickets/auftrag_details_modal.html', 
                             ticket=ticket, 
                             notes=notes,
                             messages=messages,
                             auftrag_details=auftrag_details,
                             material_list=material_list,
                             arbeit_list=arbeit_list,
                             now=datetime.now())
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Auftragsdetails-Modal: [Interner Fehler]")
        flash('Fehler beim Laden der Auftragsdetails.', 'error')
        return redirect(url_for('tickets.create'))






@bp.route('/<id>/export')
@login_required
@permission_required('tickets', 'export')
@admin_required
def export_ticket(id):
    """Exportiert das Ticket als ausgefülltes Word-Dokument."""
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        if not ticket:
            logging.error(f"Ticket nicht gefunden: {id}")
            flash('Ticket nicht gefunden.', 'error')
            return redirect(url_for('tickets.create'))
        
        # Verwende die Ticket-ID für alle Abfragen
        ticket_id_for_query = convert_id_for_query(id)
        
        auftrag_details = mongodb.find_one('auftrag_details', {'ticket_id': ticket_id_for_query}) or {}
        material_list = list(mongodb.find('auftrag_material', {'ticket_id': ticket_id_for_query})) or []

        # --- Auftragnehmer (Vorname Nachname) ---
        auftragnehmer_user = None
        if ticket.get('assigned_to'):
            from app.models.mongodb_models import MongoDBUser
            auftragnehmer_user = MongoDBUser.get_by_username(ticket['assigned_to'])
        if auftragnehmer_user:
            # MongoDBUser.get_by_username() gibt ein Dictionary zurück, kein Objekt
            auftragnehmer_name = f"{auftragnehmer_user.get('firstname', '') or ''} {auftragnehmer_user.get('lastname', '') or ''}".strip()
        else:
            auftragnehmer_name = ''

        # --- Checkboxen für Auftraggeber intern/extern ---
        intern_checkbox = '☒' if auftrag_details.get('auftraggeber_intern') else '☐'
        extern_checkbox = '☒' if auftrag_details.get('auftraggeber_extern') else '☐'

        # --- Ausgeführte Arbeiten (bis zu 5) ---
        arbeiten_liste = auftrag_details.get('ausgefuehrte_arbeiten', '')
        arbeiten_zeilen = []
        if arbeiten_liste:
            for zeile in arbeiten_liste.split('\n'):
                if not zeile.strip():
                    continue
                teile = [t.strip() for t in zeile.split('|')]
                eintrag = {
                    'arbeiten': teile[0] if len(teile) > 0 else '',
                    'arbeitsstunden': teile[1] if len(teile) > 1 else '',
                    'leistungskategorie': teile[2] if len(teile) > 2 else ''
                }
                arbeiten_zeilen.append(eintrag)
        # Fülle auf 5 Zeilen auf
        while len(arbeiten_zeilen) < 5:
            arbeiten_zeilen.append({'arbeiten':'','arbeitsstunden':'','leistungskategorie':''})

        # Materialdaten aufbereiten
        material_rows = []
        summe_material = 0
        for m in material_list:
            menge = float(m.get('menge') or 0)
            einzelpreis = float(m.get('einzelpreis') or 0)
            gesamtpreis = menge * einzelpreis
            summe_material += gesamtpreis
            material_rows.append({
                'material': m.get('material', '') or '',
                'materialmenge': f"{menge:.2f}".replace('.', ',') if menge else '',
                'materialpreis': f"{einzelpreis:.2f}".replace('.', ',') if einzelpreis else '',
                'materialpreisges': f"{gesamtpreis:.2f}".replace('.', ',') if gesamtpreis else ''
            })
        while len(material_rows) < 5:
            material_rows.append({'material':'','materialmenge':'','materialpreis':'','materialpreisges':''})

        arbeitspausch = 0
        ubertrag = 0
        zwischensumme = summe_material + arbeitspausch + ubertrag
        mwst = zwischensumme * 0.07
        gesamtsumme = zwischensumme + mwst

        # --- Kontext für docxtpl bauen ---
        context = {
            'auftragnehmer': auftragnehmer_name,
            'auftragnummer': ticket.get('ticket_number', id),
            'datum': datetime.now().strftime('%d.%m.%Y'),
            'internchk': '☒' if auftrag_details.get('auftraggeber_intern') else '☐',
            'externchk': '☒' if auftrag_details.get('auftraggeber_extern') else '☐',
            'auftraggebername': auftrag_details.get('auftraggeber_name', ''),
            'auftraggebermail': auftrag_details.get('kontakt', ''),
            'bereich': auftrag_details.get('bereich', ''),
            'auftragsbeschreibung': auftrag_details.get('auftragsbeschreibung', ''),
            'duedate': auftrag_details.get('fertigstellungstermin', ''),
            'gesamtsumme': f"{gesamtsumme:.2f}".replace('.', ','),
            'matsum': f"{summe_material:.2f}".replace('.', ','),
            'ubertrag': f"{ubertrag:.2f}".replace('.', ','),
            'arpausch': f"{arbeitspausch:.2f}".replace('.', ','),
            'zwsum': f"{zwischensumme:.2f}".replace('.', ','),
            'mwst': f"{mwst:.2f}".replace('.', ','),
            'arbeitenblock': '\n'.join([arbeit['arbeiten'] for arbeit in arbeiten_zeilen]),
            'stundenblock': '\n'.join([arbeit['arbeitsstunden'] for arbeit in arbeiten_zeilen]),
            'kategorieblock': '\n'.join([arbeit['leistungskategorie'] for arbeit in arbeiten_zeilen]),
            'materialblock': '\n'.join([material['material'] for material in material_rows]),
            'mengenblock': '\n'.join([material['materialmenge'] for material in material_rows]),
            'preisblock': '\n'.join([material['materialpreis'] for material in material_rows]),
            'gesamtblock': '\n'.join([material['materialpreisges'] for material in material_rows])
        }

        # --- Word-Dokument generieren ---
        logging.info(f"Starte Export für Ticket {id}")
        
        # Lade das Template
        template_path = os.path.join(current_app.root_path, 'static', 'word', 'btzauftrag.docx')
        logging.info(f"Template-Pfad: {template_path}")
        
        if not os.path.exists(template_path):
            logging.error(f"Template-Datei nicht gefunden: {template_path}")
            flash('Word-Template nicht gefunden.', 'error')
            return redirect(url_for('tickets.create'))
        
        from docxtpl import DocxTemplate
        doc = DocxTemplate(template_path)
        logging.info("Template erfolgreich geladen")
        
        # Rendere das Dokument
        logging.info(f"Rendere Dokument mit Kontext: {context}")
        doc.render(context)
        logging.info("Dokument erfolgreich gerendert")
        
        # Erstelle das uploads-Verzeichnis falls es nicht existiert
        uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Speichere das generierte Dokument
        ticket_number = ticket.get('ticket_number', id)
        output_path = os.path.join(uploads_dir, f'ticket_{ticket_number}_export.docx')
        
        logging.info(f"Speichere Dokument unter: {output_path}")
        doc.save(output_path)
        logging.info("Dokument erfolgreich gespeichert")
        
        logging.info(f"Word-Dokument erfolgreich generiert: {output_path}")
        
        # Sende das Dokument
        return send_file(output_path, as_attachment=True, download_name=f'ticket_{ticket_number}_export.docx')
        
    except Exception as e:
        logging.error(f"Fehler beim Generieren des Word-Dokuments: [Interner Fehler]", exc_info=True)
        flash(f'Fehler beim Generieren des Dokuments: [Interner Fehler]', 'error')
        return redirect(url_for('tickets.create'))


def get_unassigned_ticket_count():
    """Zählt offene, nicht zugewiesene Tickets nur im aktuellen Department,
    die der eingeloggte Nutzer sehen darf."""
    try:
        from flask import g
        from flask_login import current_user
        # Basis-Filter
        filter_query = {
            '$and': [
                {
                    '$or': [
                        {'assigned_to': None},
                        {'assigned_to': ''},
                        {'assigned_to': {'$exists': False}}
                    ]
                },
                {'status': 'offen'},
                {'deleted': {'$ne': True}}
            ]
        }
        # Department-Filter anwenden
        current_dept = getattr(g, 'current_department', None)
        if current_dept:
            filter_query['department'] = current_dept

        # Sichtbarkeit nach Rolle einschränken
        if getattr(current_user, 'role', None) != 'admin':
            username = getattr(current_user, 'username', None)
            role = getattr(current_user, 'role', None)
            # Sichtbare Tickets für Nicht‑Admins: eigene, zugewiesene oder in erlaubten Bereichen
            or_visibility = [
                {'created_by': username},
                {'assigned_to': username},
            ]
            if role:
                or_visibility.append({'visible_roles': role})
            filter_query['$and'].append({'$or': or_visibility})

        return mongodb.count_documents('tickets', filter_query)
    except Exception:
        return 0

# Kontextprozessor für alle Templates
@bp.app_context_processor
def inject_unread_tickets_count():
    count = get_unassigned_ticket_count()
    return dict(unread_tickets_count=count)





@bp.route('/<id>/auftrag-details')
@login_required
@permission_required('tickets', 'view')
def auftrag_details_page(id):
    try:
        # Robuste ID-Behandlung für verschiedene ID-Typen
        ticket = find_document_by_id('tickets', id)
        
        if not ticket:
            return render_template('404.html'), 404
        
        # Prüfe Berechtigungen: Admins/Mitarbeiter/Teilnehmer können alle Tickets sehen, normale User nur ihre eigenen oder zugewiesenen
        has_permission = get_ticket_service().check_ticket_permission(ticket, current_user.username, current_user.role, getattr(g, "current_department", None))
        
        if not has_permission:
            flash('Sie haben keine Berechtigung, dieses Ticket zu sehen.', 'error')
            return redirect(url_for('tickets.create'))
        
        ticket, notes, messages, auftrag_details, material_list, arbeit_list = _get_auftrag_details_data(ticket, id)
        
        logging.info(f"DEBUG: arbeit_list für Ticket {id}: {arbeit_list}")
        
        return render_template('tickets/auftrag_details_page.html', 
                             ticket=ticket, 
                             notes=notes,
                             messages=messages,
                             auftrag_details=auftrag_details,
                             material_list=material_list,
                             arbeit_list=arbeit_list)
                             
    except Exception as e:
        logging.error(f"Fehler beim Laden der Auftragsdetails-Seite: [Interner Fehler]")
        flash('Fehler beim Laden der Auftragsdetails.', 'error')
        return redirect(url_for('tickets.create'))



# Import debug routes after all functions are defined
from . import debug_routes
from . import api_routes, public_routes
