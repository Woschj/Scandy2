from app.utils.id_helpers import find_document_by_id
from app.utils.id_helpers import convert_id_for_query
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file
import logging
from app.models.mongodb_models import MongoDBWorker
from app.models.mongodb_database import mongodb, is_feature_enabled
from app.utils.decorators import login_required, admin_required, mitarbeiter_required, teilnehmer_required
from app.utils.permissions import permission_required
from app.utils.database_helpers import get_departments_from_settings
from app.services.statistics_service import StatisticsService
from datetime import datetime, timedelta
from flask_login import current_user
import os
import tempfile
from docxtpl import DocxTemplate
from bson import ObjectId
from typing import Union

bp = Blueprint('workers', __name__)

logger = logging.getLogger(__name__)




@bp.route('/')
@mitarbeiter_required
@permission_required('workers', 'view')
def index():
    """Zeigt die Mitarbeiter-Übersicht an"""
    try:
        # Hole alle nicht gelöschten Mitarbeiter der aktuellen Abteilung
        from flask import g
        worker_filter = {'deleted': {'$ne': True}}
        if getattr(g, 'current_department', None):
            worker_filter['department'] = g.current_department
        workers = mongodb.find('workers', worker_filter)
        workers = list(workers)
        
        # Für jeden Mitarbeiter die aktiven Ausleihen zählen und Benutzer-Informationen hinzufügen
        for worker in workers:
            active_lendings_count = mongodb.count_documents('lendings', {
                'worker_barcode': worker.get('barcode'),
                'returned_at': None
            })
            worker['active_lendings'] = active_lendings_count
            
            # Hole Benutzer-Informationen falls vorhanden
            if worker.get('user_id'):
                user = mongodb.find_one('users', {'_id': worker['user_id']})
                if user:
                    worker['username'] = user.get('username', '')
                    worker['user_role'] = user.get('role', '')
                    worker['user_active'] = user.get('is_active', True)
                else:
                    worker['username'] = ''
                    worker['user_role'] = ''
                    worker['user_active'] = False
            elif worker.get('username'):
                # Fallback für direkte username-Verknüpfung
                user = mongodb.find_one('users', {'username': worker['username']})
                if user:
                    worker['user_role'] = user.get('role', '')
                    worker['user_active'] = user.get('is_active', True)
                else:
                    worker['user_role'] = ''
                    worker['user_active'] = False
        
        # Hole alle Abteilungen für Filter
        departments = get_departments_from_settings()
        
        # Sortiere nach Nachname
        workers.sort(key=lambda x: x.get('lastname', ''))
        
        return render_template('workers/index.html', 
                           workers=workers,
                           departments=departments,
                           is_admin=current_user.is_admin)
                           
    except Exception as e:
        logger.error(f"Fehler beim Laden der Mitarbeiter: [Interner Fehler]", exc_info=True)
        flash('Fehler beim Laden der Mitarbeiter', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/add', methods=['GET', 'POST'])
@mitarbeiter_required
@permission_required('workers', 'create')
def add():
    # Lade Abteilungen
    departments = get_departments_from_settings()
    
    if request.method == 'POST':
        barcode = (request.form.get('barcode') or '').strip()
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        from flask import g
        current_dept = getattr(g, 'current_department', None)
        if not current_dept:
            flash('Bitte Abteilung wählen, bevor Sie einen Mitarbeiter anlegen', 'error')
            return render_template('workers/add.html', departments=departments, form_data=request.form)
        department = current_dept
        email = request.form.get('email', '')
        
        try:
            # Validierung: erlauben nur ASCII-Barcodes, sonst automatisch generieren
            if barcode:
                try:
                    barcode.encode('ascii')
                except Exception:
                    flash('Barcode enthält nicht unterstützte Zeichen (nur A-Z, a-z, 0-9 und gängige ASCII-Zeichen erlaubt). Bitte anpassen oder Feld leer lassen für automatische Vergabe.', 'error')
                    return render_template('workers/add.html', departments=departments, form_data=request.form)
            # Automatischen Barcode erzeugen, wenn leer
            if not barcode:
                import unicodedata

                def _to_ascii_upper(text: str) -> str:
                    if not text:
                        return ''
                    # Deutsche Umlaute und ß ersetzen
                    mapping = {
                        'ä': 'AE', 'ö': 'OE', 'ü': 'UE', 'ß': 'SS',
                        'Ä': 'AE', 'Ö': 'OE', 'Ü': 'UE'
                    }
                    replaced = ''.join(mapping.get(ch, ch) for ch in text)
                    normalized = unicodedata.normalize('NFKD', replaced)
                    ascii_only = normalized.encode('ascii', 'ignore').decode('ascii')
                    return ascii_only.upper()

                fn = _to_ascii_upper((firstname or '').strip())
                ln = _to_ascii_upper((lastname or '').strip())
                first_letter = fn[:1] if fn else ''
                last_three = ln[:3] if ln else ''
                base = f"{first_letter}{last_three}" or 'W'
                # Nur A-Z und Ziffern erlauben
                base = ''.join(ch for ch in base if ch.isalnum())
                # Maximal sinnvolle Basislänge begrenzen
                base = base[:8]

                # Prüfe Uniqueness innerhalb der Abteilung: zunächst Basis ohne Nummer zulassen
                candidate = base
                def _exists_any(cand: str) -> bool:
                    exists_tool = mongodb.find_one('tools', {'barcode': cand, 'deleted': {'$ne': True}, 'department': department})
                    exists_cons = mongodb.find_one('consumables', {'barcode': cand, 'deleted': {'$ne': True}, 'department': department})
                    exists_work = mongodb.find_one('workers', {'barcode': cand, 'deleted': {'$ne': True}, 'department': department})
                    return bool(exists_tool or exists_cons or exists_work)

                if _exists_any(candidate):
                    # Laufende dreistellige Nummer anhängen bis eindeutig
                    number = 1
                    while number < 1000:
                        candidate = f"{base}{number:03d}"
                        if not _exists_any(candidate):
                            break
                        number += 1
                barcode = candidate
            # Prüfe ob der Barcode bereits existiert
            existing_tool = mongodb.find_one('tools', {'barcode': barcode, 'deleted': {'$ne': True}, 'department': department})
            existing_consumable = mongodb.find_one('consumables', {'barcode': barcode, 'deleted': {'$ne': True}, 'department': department})
            existing_worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}, 'department': department})
            
            if existing_tool or existing_consumable or existing_worker:
                flash('Dieser Barcode existiert bereits', 'error')
                # Gebe die Formulardaten zurück an das Template
                return render_template('workers/add.html',
                                   departments=departments,
                                   form_data={
                                       'barcode': barcode,
                                       'firstname': firstname,
                                       'lastname': lastname,
                                       'department': department,
                                       'email': email
                                   })
            
            # Wenn Barcode eindeutig ist, füge den Mitarbeiter hinzu
            worker_data = {
                'barcode': barcode,
                'firstname': firstname,
                'lastname': lastname,
                'department': department,
                'email': email,
                'created_at': datetime.now(),
                'modified_at': datetime.now(),
                'deleted': False
            }
            
            mongodb.insert_one('workers', worker_data)
            # Cache invalidieren nach Datenänderung
            StatisticsService.invalidate_dashboard_cache()
            flash('Mitarbeiter erfolgreich hinzugefügt', 'success')
            return redirect(url_for('workers.index'))
        except Exception as e:
            flash(f'Fehler beim Hinzufügen: [Interner Fehler]', 'error')
            # Gebe die Formulardaten zurück an das Template
            return render_template('workers/add.html',
                               departments=departments,
                               form_data={
                                   'barcode': barcode,
                                   'firstname': firstname,
                                   'lastname': lastname,
                                   'department': department,
                                   'email': email
                               })
            
    # GET: aktive Abteilung vorausgewählt anzeigen
    try:
        from flask import g
        current_dept = getattr(g, 'current_department', None)
    except Exception:
        current_dept = None
    return render_template('workers/add.html', departments=departments, form_data={'department': current_dept} )

@bp.route('/<string:original_barcode>', methods=['GET', 'POST'])
@mitarbeiter_required
@permission_required('workers', 'view')
def details(original_barcode):
    """Details eines Mitarbeiters anzeigen und bearbeiten"""
    try:
        departments = get_departments_from_settings()
        
        if request.method == 'POST':
            data = request.form
            new_barcode = data.get('barcode').strip()
            firstname = data.get('firstname').strip()
            lastname = data.get('lastname').strip()
            department = data.get('department', '')
            email = data.get('email', '').strip()

            if not all([new_barcode, firstname, lastname]):
                flash('Barcode, Vorname und Nachname sind Pflichtfelder.', 'error')
                return redirect(url_for('workers.details', original_barcode=original_barcode))

            # Prüfen, ob der Mitarbeiter existiert
            worker = mongodb.find_one('workers', {'barcode': original_barcode, 'deleted': {'$ne': True}})
            if not worker:
                flash('Mitarbeiter nicht gefunden.', 'error')
                return redirect(url_for('workers.index'))

            barcode_changed = (new_barcode != original_barcode)

            if barcode_changed:
                # Prüfen, ob der neue Barcode bereits existiert
                existing_tool = mongodb.find_one('tools', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                existing_consumable = mongodb.find_one('consumables', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                existing_worker = mongodb.find_one('workers', {'barcode': new_barcode, 'deleted': {'$ne': True}})
                
                if existing_tool or existing_consumable or existing_worker:
                    flash(f'Der Barcode "{new_barcode}" existiert bereits. Bitte wählen Sie einen anderen.', 'error')
                    return redirect(url_for('workers.details', original_barcode=original_barcode))
                
                # Update Barcode in referenzierenden Tabellen
                mongodb.update_many('lendings', 
                                  {'worker_barcode': original_barcode}, 
                                  {'$set': {'worker_barcode': new_barcode}})
                mongodb.update_many('consumable_usages', 
                                  {'worker_barcode': original_barcode}, 
                                  {'$set': {'worker_barcode': new_barcode}})

            # Update der Mitarbeiterdaten
            update_data = {
                'barcode': new_barcode,
                'firstname': firstname,
                'lastname': lastname,
                'department': department,
                'email': email,
                'modified_at': datetime.now()
            }
            
            mongodb.update_one('workers', 
                             {'barcode': original_barcode}, 
                             {'$set': update_data})

            # Cache invalidieren nach Datenänderung
            StatisticsService.invalidate_dashboard_cache()
            flash('Mitarbeiter erfolgreich aktualisiert', 'success')
            return redirect(url_for('workers.details', original_barcode=new_barcode))

        # GET-Methode: Details anzeigen
        worker = mongodb.find_one('workers', {'barcode': original_barcode, 'deleted': {'$ne': True}})
        if not worker:
            flash('Mitarbeiter nicht gefunden', 'error')
            return redirect(url_for('workers.index'))
        
        # Hole Benutzer-Informationen falls vorhanden
        if worker.get('user_id'):
            user = mongodb.find_one('users', {'_id': worker['user_id']})
            if user:
                worker['username'] = user.get('username', '')
                worker['user_role'] = user.get('role', '')
                worker['user_active'] = user.get('is_active', True)
            else:
                worker['username'] = ''
                worker['user_role'] = ''
                worker['user_active'] = False
        elif worker.get('username'):
            # Fallback für direkte username-Verknüpfung
            user = mongodb.find_one('users', {'username': worker['username']})
            if user:
                worker['user_role'] = user.get('role', '')
                worker['user_active'] = user.get('is_active', True)
            else:
                worker['user_role'] = ''
                worker['user_active'] = False

        # Hole aktuelle Ausleihen
        active_lendings = mongodb.find('lendings', {
            'worker_barcode': original_barcode,
            'returned_at': None
        })
        active_lendings = list(active_lendings)
        
        # Füge Tool-Informationen hinzu
        for lending in active_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            if tool:
                lending['tool_name'] = tool['name']
            
            # Stelle sicher, dass das Datum korrekt formatiert ist
            if isinstance(lending.get('lent_at'), str):
                try:
                    lending['lent_at'] = datetime.strptime(lending['lent_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['lent_at'] = datetime.now()

        # Hole Verlauf aller Ausleihen
        all_lendings = mongodb.find('lendings', {'worker_barcode': original_barcode})
        all_lendings = list(all_lendings)
        
        # Hole Verbrauchsmaterial-Ausgaben des Mitarbeiters
        from app.services.lending_service import LendingService
        consumable_usages = LendingService.get_worker_consumable_history(original_barcode)
        
        # Kombiniere Ausleihen und Verbrauchsmaterial-Ausgaben für eine vollständige Historie
        combined_history = []
        
        # Füge Ausleihen hinzu
        for lending in all_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            if tool:
                lending['tool_name'] = tool['name']
            
            # Stelle sicher, dass die Datumsfelder korrekt formatiert sind
            if isinstance(lending.get('lent_at'), str):
                try:
                    lending['lent_at'] = datetime.strptime(lending['lent_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['lent_at'] = datetime.now()
            
            if isinstance(lending.get('returned_at'), str):
                try:
                    lending['returned_at'] = datetime.strptime(lending['returned_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['returned_at'] = None
            
            # Füge Typ-Information hinzu
            lending['type'] = 'tool'
            lending['action_type'] = 'Ausleihe/Rückgabe'
            lending['action_date'] = lending.get('lent_at')
            
            combined_history.append(lending)
        
        # Füge Verbrauchsmaterial-Ausgaben hinzu
        for usage in consumable_usages:
            # Stelle sicher, dass das Datum korrekt formatiert ist
            if isinstance(usage.get('used_at'), str):
                try:
                    usage['used_at'] = datetime.strptime(usage['used_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    usage['used_at'] = datetime.now()
            
            # Füge Typ-Information hinzu
            usage['type'] = 'consumable'
            usage['action_type'] = 'Verbrauchsmaterial-Ausgabe'
            usage['action_date'] = usage.get('used_at')
            usage['quantity_abs'] = abs(usage.get('quantity', 0))
            
            combined_history.append(usage)
        
        # Sortiere nach Datum (neueste zuerst) - sicherer Vergleich
        def safe_date_key(item):
            action_date = item.get('action_date')
            if isinstance(action_date, str):
                try:
                    return datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    return datetime.min
            elif isinstance(action_date, datetime):
                return action_date
            else:
                return datetime.min
        
        combined_history.sort(key=safe_date_key, reverse=True)
        
        # Sortiere auch aktive Ausleihen nach Datum
        active_lendings.sort(key=safe_date_key, reverse=True)

        # Füge Tool-Informationen hinzu
        for lending in all_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending['tool_barcode']})
            if tool:
                lending['tool_name'] = tool['name']
            
            # Stelle sicher, dass die Datumsfelder korrekt formatiert sind
            if isinstance(lending.get('lent_at'), str):
                try:
                    lending['lent_at'] = datetime.strptime(lending['lent_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['lent_at'] = datetime.now()
            
            if isinstance(lending.get('returned_at'), str):
                try:
                    lending['returned_at'] = datetime.strptime(lending['returned_at'], '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    lending['returned_at'] = None

        return render_template('workers/details.html',
                             worker=worker,
                             departments=departments,
                             current_lendings=active_lendings,
                             lending_history=combined_history,
                             is_admin=current_user.is_admin)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Mitarbeiterdetails: [Interner Fehler]", exc_info=True)
        flash('Fehler beim Laden der Mitarbeiterdetails', 'error')
        return redirect(url_for('workers.index'))

@bp.route('/<string:barcode>/card')
@mitarbeiter_required
@permission_required('workers', 'view')
def worker_card(barcode: str):
    """Druckbare Ausweis-Ansicht (HTML) mit clientseitigem Barcode."""
    worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
    if not worker:
        return render_template('errors/404.html'), 404
    return render_template('workers/card.html', worker=worker)

@bp.route('/<barcode>/edit', methods=['POST'])
@mitarbeiter_required
@permission_required('workers', 'edit')
def edit(barcode):
    """Bearbeitet einen Mitarbeiter über Modal"""
    try:
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        department = request.form.get('department')
        email = request.form.get('email')
        new_barcode = (request.form.get('barcode') or '').strip()
        
        if not all([firstname, lastname]):
            return jsonify({'success': False, 'message': 'Vor- und Nachname sind erforderlich'}), 400
            
        # Prüfen, ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        if not worker:
            return jsonify({'success': False, 'message': 'Mitarbeiter nicht gefunden'}), 404

        # Barcode-Änderung prüfen
        barcode_changed = (new_barcode != barcode)
        if barcode_changed:
            # ASCII-Validierung (Umlaute/Sonderzeichen verbieten)
            try:
                new_barcode.encode('ascii')
            except Exception:
                return jsonify({'success': False, 'message': 'Barcode enthält nicht erlaubte Zeichen (nur ASCII).'}), 400
            # Prüfen, ob der neue Barcode bereits existiert
            existing_tool = mongodb.find_one('tools', {'barcode': new_barcode, 'deleted': {'$ne': True}})
            existing_consumable = mongodb.find_one('consumables', {'barcode': new_barcode, 'deleted': {'$ne': True}})
            existing_worker = mongodb.find_one('workers', {'barcode': new_barcode, 'deleted': {'$ne': True}})
            
            if existing_tool or existing_consumable or existing_worker:
                return jsonify({'success': False, 'message': f'Der Barcode "{new_barcode}" existiert bereits'}), 400
            
            # Update Barcode in referenzierenden Tabellen
            mongodb.update_many('lendings', 
                              {'worker_barcode': barcode}, 
                              {'$set': {'worker_barcode': new_barcode}})
            mongodb.update_many('consumable_usages', 
                              {'worker_barcode': barcode}, 
                              {'$set': {'worker_barcode': new_barcode}})

        # Update der Mitarbeiterdaten
        update_data = {
            'barcode': new_barcode,
            'firstname': firstname,
            'lastname': lastname,
            'department': department,
            'email': email,
            'modified_at': datetime.now()
        }
        
        mongodb.update_one('workers', 
                         {'barcode': barcode}, 
                         {'$set': update_data})
        
        return jsonify({
            'success': True, 
            'message': 'Mitarbeiter erfolgreich aktualisiert',
            'redirect': url_for('workers.details', original_barcode=new_barcode)
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Mitarbeiters: [Interner Fehler]", exc_info=True)
        return jsonify({'success': False, 'message': 'Fehler beim Aktualisieren des Mitarbeiters'}), 500

@bp.route('/<barcode>/delete', methods=['DELETE'])
@mitarbeiter_required
@permission_required('workers', 'delete')
def delete_by_barcode(barcode):
    """Löscht einen Mitarbeiter (Soft Delete)"""
    try:
        # Prüfe ob der Mitarbeiter existiert
        worker = mongodb.find_one('workers', {'barcode': barcode, 'deleted': {'$ne': True}})
        
        if not worker:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter nicht gefunden'
            }), 404
            
        # Prüfe ob der Mitarbeiter noch Werkzeuge ausgeliehen hat
        lending = mongodb.find_one('lendings', {'worker_barcode': barcode, 'returned_at': None})
        
        if lending:
            return jsonify({
                'success': False,
                'message': 'Mitarbeiter muss zuerst alle Werkzeuge zurückgeben'
            }), 400
            
        # Führe Soft Delete durch
        mongodb.update_one('workers', 
                         {'barcode': barcode}, 
                         {'$set': {'deleted': True, 'deleted_at': datetime.now()}})
        
        return jsonify({
            'success': True,
            'message': 'Mitarbeiter erfolgreich gelöscht'
        })
        
    except Exception as e:
        logger.error(f"Fehler beim Löschen des Mitarbeiters: [Interner Fehler]", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: [Interner Fehler]'
        }), 500

@bp.route('/workers/search')
@mitarbeiter_required
def search():
    """Sucht nach Mitarbeitern"""
    query = request.args.get('q', '')
    try:
        workers = mongodb.find('workers', {
            'firstname': {'$regex': query, '$options': 'i'},
            'lastname': {'$regex': query, '$options': 'i'},
            'barcode': {'$regex': query, '$options': 'i'},
            'deleted': {'$ne': True}
        })
        return jsonify([dict(worker) for worker in workers])
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

