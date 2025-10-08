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

bp = Blueprint('workers', __name__, url_prefix='/workers')

logger = logging.getLogger(__name__)

def convert_id_for_query(id_value: str) -> Union[str, ObjectId]:
    """
    Konvertiert eine ID für Datenbankabfragen.
    Versucht zuerst mit String-ID, dann mit ObjectId.
    """
    try:
        # Versuche zuerst mit String-ID (für importierte Daten)
        return id_value
    except Exception as e:
        logger.warning(f"Fehler bei String-ID-Behandlung: {e}")
        # Falls das fehlschlägt, versuche ObjectId
        try:
            return ObjectId(id_value)
        except Exception as e2:
            logger.warning(f"Fehler bei ObjectId-Konvertierung: {e2}")
            # Falls auch das fehlschlägt, gib die ursprüngliche ID zurück
            return id_value

def find_document_by_id(collection: str, id_value: str):
    """
    Findet ein Dokument in einer Collection mit robuster ID-Behandlung.
    Unterstützt sowohl String-IDs als auch ObjectIds.
    """
    try:
        # Versuche zuerst mit String-ID
        doc = mongodb.find_one(collection, {'_id': id_value})
        if doc:
            return doc
        
        # Falls nicht gefunden, versuche mit ObjectId
        try:
            obj_id = ObjectId(id_value)
            doc = mongodb.find_one(collection, {'_id': obj_id})
            if doc:
                return doc
        except Exception as e:
            logger.warning(f"Fehler bei ObjectId-Konvertierung: {e}")
            pass
        
        # Falls auch das fehlschlägt, versuche mit convert_id_for_query
        converted_id = convert_id_for_query(id_value)
        doc = mongodb.find_one(collection, {'_id': converted_id})
        return doc
        
    except Exception as e:
        print(f"Fehler beim Suchen von Dokument {id_value} in {collection}: {e}")
        return None

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
        logger.error(f"Fehler beim Laden der Mitarbeiter: {str(e)}", exc_info=True)
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
            flash(f'Fehler beim Hinzufügen: {str(e)}', 'error')
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
        logger.error(f"Fehler beim Laden der Mitarbeiterdetails: {str(e)}", exc_info=True)
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
        logger.error(f"Fehler beim Aktualisieren des Mitarbeiters: {str(e)}", exc_info=True)
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
        logger.error(f"Fehler beim Löschen des Mitarbeiters: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Fehler beim Löschen: {str(e)}'
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
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/migrate-timesheets', methods=['POST'])
@admin_required
def admin_migrate_timesheets():
    """Admin-Route zur manuellen Migration von Timesheet-Datumsfeldern"""
    try:
        migrated_count = migrate_timesheet_dates()
        flash(f'Migration abgeschlossen. {migrated_count} Timesheet-Einträge wurden migriert.', 'success')
    except Exception as e:
        flash(f'Fehler bei der Migration: {str(e)}', 'error')
    
    return redirect(url_for('workers.timesheet_list'))

@bp.route('/admin/migrate-all-dates', methods=['POST'])
@admin_required
def admin_migrate_all_dates():
    """Admin-Route zur Migration aller Datumsfelder in allen Collections"""
    try:
        collections = ['tickets', 'users', 'tools', 'consumables', 'workers', 'timesheets']
        total_migrated = 0
        results = {}
        
        for collection in collections:
            try:
                # Finde alle Dokumente mit String-Datumsfeldern
                documents = list(mongodb.db[collection].find({
                    '$or': [
                        {'created_at': {'$type': 'string'}},
                        {'updated_at': {'$type': 'string'}},
                        {'due_date': {'$type': 'string'}},
                        {'resolved_at': {'$type': 'string'}}
                    ]
                }))
                
                migrated_count = 0
                for doc in documents:
                    update_data = {}
                    
                    # Konvertiere alle Datumsfelder
                    for field in ['created_at', 'updated_at', 'due_date', 'resolved_at']:
                        if isinstance(doc.get(field), str):
                            try:
                                for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                    try:
                                        update_data[field] = datetime.strptime(doc[field], fmt)
                                        break
                                    except ValueError:
                                        continue
                                # Wenn kein Format passt, verwende aktuelles Datum
                                if field not in update_data:
                                    update_data[field] = datetime.now()
                            except:
                                update_data[field] = datetime.now()
                    
                    # Update nur wenn Änderungen vorhanden
                    if update_data:
                        result = mongodb.db[collection].update_one(
                            {'_id': doc['_id']},
                            {'$set': update_data}
                        )
                        if result.modified_count > 0:
                            migrated_count += 1
                
                results[collection] = migrated_count
                total_migrated += migrated_count
                
            except Exception as e:
                results[collection] = {'error': str(e)}
        
        flash(f'Migration abgeschlossen. {total_migrated} Dokumente wurden migriert.', 'success')
        return jsonify({
            'success': True,
            'total_migrated': total_migrated,
            'results': results
        })
        
    except Exception as e:
        flash(f'Fehler bei der Migration: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/admin/check-timesheet-dates')
@admin_required
def check_timesheet_dates():
    """Admin-Route zur Überprüfung der Timesheet-Datumsfelder"""
    try:
        # Zähle Timesheets mit String-Datumsfeldern
        string_dates = mongodb.db.timesheets.count_documents({
            '$or': [
                {'created_at': {'$type': 'string'}},
                {'updated_at': {'$type': 'string'}}
            ]
        })
        
        # Zähle Timesheets mit Date-Datumsfeldern
        date_dates = mongodb.db.timesheets.count_documents({
            '$and': [
                {'created_at': {'$type': 'date'}},
                {'updated_at': {'$type': 'date'}}
            ]
        })
        
        total = mongodb.db.timesheets.count_documents({})
        
        return jsonify({
            'total_timesheets': total,
            'string_dates': string_dates,
            'date_dates': date_dates,
            'needs_migration': string_dates > 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/check-database-status')
@admin_required
def check_database_status():
    """Admin-Route zur Überprüfung des Datenbankstatus nach Backup-Restore"""
    try:
        collections = ['tickets', 'users', 'tools', 'consumables', 'workers', 'timesheets']
        status = {}
        
        for collection in collections:
            try:
                # Zähle Dokumente
                total = mongodb.db[collection].count_documents({})
                
                # Prüfe ID-Typen
                sample_docs = list(mongodb.db[collection].find().limit(5))
                id_types = {}
                for doc in sample_docs:
                    doc_id = doc.get('_id')
                    if doc_id:
                        id_type = type(doc_id).__name__
                        id_types[id_type] = id_types.get(id_type, 0) + 1
                
                # Prüfe Datumsfelder (falls vorhanden)
                date_fields = {}
                if sample_docs:
                    sample_doc = sample_docs[0]
                    for field in ['created_at', 'updated_at', 'due_date', 'resolved_at']:
                        if field in sample_doc:
                            field_value = sample_doc[field]
                            if field_value:
                                date_fields[field] = type(field_value).__name__
                
                status[collection] = {
                    'total_documents': total,
                    'id_types': id_types,
                    'date_fields': date_fields,
                    'sample_ids': [str(doc.get('_id')) for doc in sample_docs[:3]]
                }
                
            except Exception as e:
                status[collection] = {
                    'error': str(e)
                }
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def migrate_timesheet_dates():
    """Migriert Timesheet-Datumsfelder von String zu Date-Objekten"""
    try:
        # Finde alle Timesheets mit String-Datumsfeldern
        timesheets = list(mongodb.db.timesheets.find({
            '$or': [
                {'created_at': {'$type': 'string'}},
                {'updated_at': {'$type': 'string'}}
            ]
        }))
        
        migrated_count = 0
        for ts in timesheets:
            update_data = {}
            
            # Konvertiere created_at
            if isinstance(ts.get('created_at'), str):
                try:
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            update_data['created_at'] = datetime.strptime(ts['created_at'], fmt)
                            break
                        except ValueError:
                            continue
                    # Wenn kein Format passt, verwende aktuelles Datum
                    if 'created_at' not in update_data:
                        update_data['created_at'] = datetime.now()
                except:
                    update_data['created_at'] = datetime.now()
            
            # Konvertiere updated_at
            if isinstance(ts.get('updated_at'), str):
                try:
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            update_data['updated_at'] = datetime.strptime(ts['updated_at'], fmt)
                            break
                        except ValueError:
                            continue
                    # Wenn kein Format passt, verwende aktuelles Datum
                    if 'updated_at' not in update_data:
                        update_data['updated_at'] = datetime.now()
                except:
                    update_data['updated_at'] = datetime.now()
            
            # Update nur wenn Änderungen vorhanden
            if update_data:
                result = mongodb.db.timesheets.update_one(
                    {'_id': ts['_id']},
                    {'$set': update_data}
                )
                if result.modified_count > 0:
                    migrated_count += 1
        
        return migrated_count
    except Exception as e:
        print(f"Fehler bei Timesheet-Migration: {e}")
        return 0

@bp.route('/timesheets')
@login_required
def timesheet_list():
    """Zeigt die Wochenberichte für den aktuellen Benutzer an (für alle Rollen mit timesheet_enabled)"""
    # Prüfe ob Wochenberichte global aktiviert sind
    if not is_feature_enabled('weekly_reports'):
        flash('Das Wochenberichte-System ist deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    
    # Führe Migration aus, falls noch nicht geschehen
    try:
        migrate_timesheet_dates()
    except Exception as e:
        # Migration-Fehler nicht blockieren, nur loggen
        print(f"Migration-Fehler (nicht kritisch): {e}")
    
    # Wochenberichte sind nutzerspezifisch und nicht abteilungsgebunden
    user_id = current_user.username
    sort = request.args.get('sort', 'kw_desc')
    
    # Aktuelle Kalenderwoche ermitteln
    today = datetime.now()
    current_year = today.isocalendar()[0]
    current_week = today.isocalendar()[1]
    
    # Prüfen ob ein Eintrag für die aktuelle Woche existiert
    existing_entry = mongodb.find_one('timesheets', {
        'user_id': user_id,
        'year': current_year,
        'kw': current_week
    })
    
    # Wenn kein Eintrag existiert, erstelle einen neuen
    if not existing_entry:
        mongodb.insert_one('timesheets', {
            'user_id': user_id,
            'year': current_year,
            'kw': current_week,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
    
    # MongoDB Aggregation Pipeline für Timesheets
    pipeline = [
        {'$match': {'user_id': user_id}},
        {
            '$addFields': {
                'filled_days': {
                    '$add': [
                        {'$cond': [{'$and': [{'$ne': ['$montag_start', '']}, {'$ne': ['$montag_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$dienstag_start', '']}, {'$ne': ['$dienstag_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$mittwoch_start', '']}, {'$ne': ['$mittwoch_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$donnerstag_start', '']}, {'$ne': ['$donnerstag_tasks', '']}]}, 1, 0]},
                        {'$cond': [{'$and': [{'$ne': ['$freitag_start', '']}, {'$ne': ['$freitag_tasks', '']}]}, 1, 0]}
                    ]
                },
                'created_at_de': '$created_at',
                'updated_at_de': '$updated_at'
            }
        }
    ]
    
    # Sortierung hinzufügen
    sort_stage = {}
    if sort == 'year_desc':
        sort_stage = {'year': -1, 'kw': -1}
    elif sort == 'year_asc':
        sort_stage = {'year': 1, 'kw': 1}
    elif sort == 'kw_desc':
        sort_stage = {'year': -1, 'kw': -1}
    elif sort == 'kw_asc':
        sort_stage = {'year': 1, 'kw': 1}
    elif sort == 'filled_desc':
        sort_stage = {'filled_days': -1, 'year': -1, 'kw': -1}
    elif sort == 'filled_asc':
        sort_stage = {'filled_days': 1, 'year': -1, 'kw': -1}
    # Für Date-Sortierung verwenden wir Python-Sortierung statt MongoDB-Sortierung
    # da die Felder möglicherweise als Strings gespeichert sind
    elif sort in ['created_desc', 'created_asc', 'updated_desc', 'updated_asc']:
        # Keine MongoDB-Sortierung für Date-Felder, wird später in Python gemacht
        pass
    
    if sort_stage:
        pipeline.append({'$sort': sort_stage})
    
    # MongoDB Aggregation ausführen
    timesheets = list(mongodb.db.timesheets.aggregate(pipeline))
    
    # Verarbeite datetime-Objekte nach der Abfrage
    for ts in timesheets:
        # Verarbeite created_at
        if isinstance(ts.get('created_at'), dict) and ts['created_at'].get('__type__') == 'datetime':
            try:
                ts['created_at_de'] = datetime.fromisoformat(ts['created_at']['value']).strftime('%d.%m.%Y')
            except:
                ts['created_at_de'] = 'Unbekannt'
        elif isinstance(ts.get('created_at'), datetime):
            ts['created_at_de'] = ts['created_at'].strftime('%d.%m.%Y')
        elif isinstance(ts.get('created_at'), str):
            try:
                parsed_date = datetime.strptime(ts['created_at'], '%Y-%m-%d %H:%M:%S')
                ts['created_at_de'] = parsed_date.strftime('%d.%m.%Y')
            except:
                ts['created_at_de'] = ts['created_at']
        else:
            ts['created_at_de'] = 'Unbekannt'
        
        # Verarbeite updated_at
        if isinstance(ts.get('updated_at'), dict) and ts['updated_at'].get('__type__') == 'datetime':
            try:
                ts['updated_at_de'] = datetime.fromisoformat(ts['updated_at']['value']).strftime('%d.%m.%Y')
            except:
                ts['updated_at_de'] = 'Unbekannt'
        elif isinstance(ts.get('updated_at'), datetime):
            ts['updated_at_de'] = ts['updated_at'].strftime('%d.%m.%Y')
        elif isinstance(ts.get('updated_at'), str):
            try:
                parsed_date = datetime.strptime(ts['updated_at'], '%Y-%m-%d %H:%M:%S')
                ts['updated_at_de'] = parsed_date.strftime('%d.%m.%Y')
            except:
                ts['updated_at_de'] = ts['updated_at']
        else:
            ts['updated_at_de'] = 'Unbekannt'
    
    # Python-Sortierung für Date-Felder (falls MongoDB-Sortierung nicht möglich war)
    if sort in ['created_desc', 'created_asc', 'updated_desc', 'updated_asc']:
        def parse_date(date_value):
            """Sichere Datum-Parsing-Funktion"""
            if isinstance(date_value, datetime):
                return date_value
            elif isinstance(date_value, str):
                try:
                    # Versuche verschiedene Datum-Formate
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                        try:
                            return datetime.strptime(date_value, fmt)
                        except ValueError:
                            continue
                    # Fallback: aktuelles Datum
                    return datetime.now()
                except:
                    return datetime.now()
            else:
                return datetime.now()
        
        reverse = sort.endswith('_desc')
        if sort.startswith('created'):
            timesheets.sort(key=lambda x: parse_date(x.get('created_at', datetime.now())), reverse=reverse)
        elif sort.startswith('updated'):
            timesheets.sort(key=lambda x: parse_date(x.get('updated_at', datetime.now())), reverse=reverse)
    
    # Berechne unausgefüllte Tage für alle Wochen
    unfilled_days = 0
    for ts in timesheets:
        # Berechne den Wochenstart
        week_start = datetime.fromisocalendar(ts['year'], ts['kw'], 1)  # 1 = Montag
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
        
        for i, day in enumerate(days):
            # Berechne das Datum für den aktuellen Tag
            current_day = week_start + timedelta(days=i)
            
            # Prüfe nur vergangene Tage
            if current_day.date() < today.date():
                has_times = ts.get(f'{day}_start') or ts.get(f'{day}_end')
                has_tasks = ts.get(f'{day}_tasks')
                if not (has_times and has_tasks):
                    unfilled_days += 1
    
    return render_template('workers/timesheet_list.html', 
                         timesheets=timesheets,
                         unfilled_days=unfilled_days,
                         unfilled_timesheet_days=unfilled_days,
                         today=today,
                         datetime=datetime,
                         timedelta=timedelta
    )

@bp.route('/teilnehmer/timesheets')
@teilnehmer_required
def teilnehmer_timesheet_list():
    """Spezielle Route für Teilnehmer zu den Wochenberichten"""
    return timesheet_list()

@bp.route('/timesheet/new', methods=['GET', 'POST'])
@login_required
def timesheet_create():
    # Prüfe ob Wochenberichte global aktiviert sind
    if not is_feature_enabled('weekly_reports'):
        flash('Das Wochenberichte-System ist deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        user_id = current_user.username
        week = request.form.get('week')  # z.B. '2024-W20'
        if week and '-W' in week:
            year, week_str = week.split('-W')
            calendar_week = int(week_str)
            year = int(year)
        else:
            flash('Ungültiges Wochenformat.', 'error')
            return redirect(url_for('workers.timesheet_create'))
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
        data = {
            'user_id': user_id,
            'year': year,
            'kw': calendar_week,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        for day in days:
            data[f'{day}_tasks'] = request.form.get(f'tasks_{day}', '')
            data[f'{day}_start'] = request.form.get(f'start_{day}', '')
            data[f'{day}_end'] = request.form.get(f'end_{day}', '')
        mongodb.insert_one('timesheets', data)
        flash('Wochenplan erfolgreich gespeichert.', 'success')
        return redirect(url_for('workers.timesheet_list'))
    return render_template('workers/timesheet.html', now=datetime.now())

@bp.route('/timesheet/<string:ts_id>/edit', methods=['GET', 'POST'])
@login_required
def timesheet_edit(ts_id):
    # Prüfe ob Wochenberichte global aktiviert sind
    if not is_feature_enabled('weekly_reports'):
        flash('Das Wochenberichte-System ist deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    user_id = current_user.username
    
    # Robuste ID-Behandlung für verschiedene ID-Typen
    print(f"DEBUG: Timesheet-Edit aufgerufen für ID: {ts_id}")
    
    # Versuche zuerst mit String-ID
    ts = mongodb.find_one('timesheets', {'_id': ts_id, 'user_id': user_id})
    if ts:
        print(f"DEBUG: Timesheet mit String-ID gefunden: KW {ts.get('kw', 'Unknown')}")
        found_id = ts_id  # Verwende die ursprüngliche String-ID
    else:
        # Falls nicht gefunden, versuche mit ObjectId
        try:
            from bson import ObjectId
            obj_id = ObjectId(ts_id)
            ts = mongodb.find_one('timesheets', {'_id': obj_id, 'user_id': user_id})
            if ts:
                print(f"DEBUG: Timesheet mit ObjectId gefunden: KW {ts.get('kw', 'Unknown')}")
                found_id = obj_id  # Verwende die ObjectId
        except Exception as e:
            print(f"DEBUG: ObjectId-Konvertierung fehlgeschlagen: {e}")
            found_id = None
    
    if not ts:
        print(f"DEBUG: Kein Timesheet gefunden für ID: {ts_id}")
        flash('Wochenplan nicht gefunden oder keine Berechtigung.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    
    if request.method == 'POST':
        week = request.form.get('week')
        if week and '-W' in week:
            year, week_str = week.split('-W')
            calendar_week = int(week_str)
            year = int(year)
        else:
            flash('Ungültiges Wochenformat.', 'error')
            return redirect(url_for('workers.timesheet_edit', ts_id=ts_id))
        
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
        update_data = {
            'year': year,
            'kw': calendar_week,
            'updated_at': datetime.now()
        }
        
        for day in days:
            update_data[f'{day}_tasks'] = request.form.get(f'tasks_{day}', '')
            update_data[f'{day}_start'] = request.form.get(f'start_{day}', '')
            update_data[f'{day}_end'] = request.form.get(f'end_{day}', '')
        
        mongodb.update_one('timesheets', 
                         {'_id': found_id}, 
                         {'$set': update_data})
        flash('Wochenplan aktualisiert.', 'success')
        return redirect(url_for('workers.timesheet_list'))
    return render_template('workers/timesheet.html', ts=ts, now=datetime.now())

@bp.route('/timesheet/<string:ts_id>/download')
@login_required
def timesheet_download(ts_id):
    # Prüfe ob Wochenberichte global aktiviert sind
    if not is_feature_enabled('weekly_reports'):
        flash('Das Wochenberichte-System ist deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    
    # Prüfe ob Wochenbericht-Feature für den Benutzer aktiviert ist
    if not current_user.timesheet_enabled:
        flash('Das Wochenbericht-Feature ist für Ihren Account deaktiviert.', 'error')
        return redirect(url_for('main.index'))
    user_id = current_user.username
    
    # Robuste ID-Behandlung für verschiedene ID-Typen
    print(f"DEBUG: Timesheet-Download aufgerufen für ID: {ts_id}")
    
    # Versuche zuerst mit String-ID
    ts = mongodb.find_one('timesheets', {'_id': ts_id, 'user_id': user_id})
    if ts:
        print(f"DEBUG: Timesheet mit String-ID gefunden: KW {ts.get('kw', 'Unknown')}")
    else:
        # Falls nicht gefunden, versuche mit ObjectId
        try:
            from bson import ObjectId
            obj_id = ObjectId(ts_id)
            ts = mongodb.find_one('timesheets', {'_id': obj_id, 'user_id': user_id})
            if ts:
                print(f"DEBUG: Timesheet mit ObjectId gefunden: KW {ts.get('kw', 'Unknown')}")
        except Exception as e:
            print(f"DEBUG: ObjectId-Konvertierung fehlgeschlagen: {e}")
    
    if not ts:
        print(f"DEBUG: Kein Timesheet gefunden für ID: {ts_id}")
        flash('Wochenplan nicht gefunden oder keine Berechtigung.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    # Kontext für docxtpl bauen
    name = current_user.username
    context = {
        'kw': ts['kw'],
        'name': name,
    }
    # Korrekte Berechnung des Wochenstarts nach ISO-Kalenderwoche
    week_start = datetime.fromisocalendar(ts['year'], ts['kw'], 1)  # 1 = Montag
    days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
    for i, day in enumerate(days):
        context[f'{day}_tasks'] = ts.get(f'{day}_tasks', '')
        context[f'{day}_datum'] = (week_start + timedelta(days=i)).strftime('%d.%m.')
        start_time = ts.get(f'{day}_start')
        end_time = ts.get(f'{day}_end')
        if start_time and end_time:
            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
            if end < start:
                end += timedelta(days=1)
            hours = (end - start).total_seconds() / 3600
            if hours > 6:
                hours -= 0.5  # Automatisch 30 Minuten Pause abziehen
            if hours < 0:
                hours = 0
            context[f'{day}_hours'] = f'{hours:.2f}'
        else:
            context[f'{day}_hours'] = ''
    template_path = os.path.join('app', 'static', 'word', 'woplan.docx')
    doc = DocxTemplate(template_path)
    doc.render(context)
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, f'woplan_{datetime.now().strftime("%Y%m%d_%H%M%S")}.docx')
    doc.save(output_path)
    return send_file(output_path, as_attachment=True, download_name=f'woplan_kw{ts["kw"]}.docx')

@bp.route('/timesheet/quick-update', methods=['POST'])
@login_required
def timesheet_quick_update():
    """Aktualisiert den heutigen Tag des aktuellen Wochenplans (teilweise Eingaben erlaubt)."""
    # Feature-Checks
    if not is_feature_enabled('weekly_reports') or not getattr(current_user, 'timesheet_enabled', False):
        flash('Das Wochenberichte-System ist nicht verfügbar.', 'error')
        return redirect(url_for('main.index'))

    try:
        user_id = current_user.username
        now_dt = datetime.now()
        year = now_dt.isocalendar()[0]
        kw = now_dt.isocalendar()[1]
        weekday = now_dt.weekday()  # 0=Montag
        days = ['montag', 'dienstag', 'mittwoch', 'donnerstag', 'freitag']
        if weekday > 4:
            weekday = 4  # Wochenende -> Freitag befüllen
        day_key = days[weekday]

        start_time = (request.form.get('start_time') or '').strip()
        end_time = (request.form.get('end_time') or '').strip()
        tasks = (request.form.get('tasks') or '').strip()

        if not start_time and not end_time and not tasks:
            flash('Keine Änderungen. Bitte Start, Ende oder Tätigkeiten angeben.', 'warning')
            return redirect(url_for('main.index'))

        # Upsert aktuellen Wochenplan
        ts = mongodb.find_one('timesheets', {'user_id': user_id, 'year': year, 'kw': kw})
        if not ts:
            mongodb.insert_one('timesheets', {
                'user_id': user_id,
                'year': year,
                'kw': kw,
                'created_at': now_dt,
                'updated_at': now_dt
            })
            ts = mongodb.find_one('timesheets', {'user_id': user_id, 'year': year, 'kw': kw})

        update_data = {'updated_at': now_dt}
        if start_time:
            update_data[f'{day_key}_start'] = start_time
        if end_time:
            update_data[f'{day_key}_end'] = end_time
        if tasks:
            update_data[f'{day_key}_tasks'] = tasks

        mongodb.update_one('timesheets', {'_id': ts['_id']}, {'$set': update_data})
        flash('Eintrag gespeichert.', 'success')
    except Exception as e:
        print(f"Quick-Update Fehler: {e}")
        flash('Konnte den Eintrag nicht speichern.', 'error')
    return redirect(url_for('main.index'))

@bp.route('/timesheet/<ts_id>/delete', methods=['POST'])
@login_required
def timesheet_delete(ts_id):
    # Verwende die ursprüngliche ID direkt für das Update
    from bson import ObjectId
    try:
        # Versuche zuerst mit ObjectId
        ts_id_for_update = ObjectId(ts_id)
    except:
        # Falls das fehlschlägt, verwende die ursprüngliche ID als String
        ts_id_for_update = ts_id
    
    # Prüfe ob das Timesheet existiert
    ts = mongodb.find_one('timesheets', {'_id': ts_id_for_update})
    if not ts:
        flash('Wochenbericht nicht gefunden.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    # Nur Besitzer oder Admin darf löschen
    if ts.get('user_id') != current_user.username and not current_user.is_admin:
        flash('Sie dürfen nur Ihre eigenen Wochenberichte löschen.', 'error')
        return redirect(url_for('workers.timesheet_list'))
    
    # Verwende die ID für alle Abfragen
    mongodb.delete_one('timesheets', {'_id': ts_id_for_update})
    flash('Wochenbericht wurde gelöscht.', 'success')
    return redirect(url_for('workers.timesheet_list'))