from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
import logging
from app.models.mongodb_database import mongodb, is_feature_enabled
from app.utils.decorators import login_required, admin_required, teilnehmer_required
from datetime import datetime, timedelta
from flask_login import current_user
import os
import tempfile
from docxtpl import DocxTemplate
from bson import ObjectId

bp = Blueprint('weekly_reports', __name__)
logger = logging.getLogger(__name__)

# Timesheet routes moved from workers plugin
@bp.route('/admin/migrate-timesheets', methods=['POST'])
@admin_required
def admin_migrate_timesheets():
    """Admin-Route zur manuellen Migration von Timesheet-Datumsfeldern"""
    try:
        migrated_count = migrate_timesheet_dates()
        flash(f'Migration abgeschlossen. {migrated_count} Timesheet-Einträge wurden migriert.', 'success')
    except Exception as e:
        flash(f'Fehler bei der Migration: [Interner Fehler]', 'error')

    return redirect(url_for('weekly_reports.timesheet_list'))

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
                results[collection] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        flash(f'Migration abgeschlossen. {total_migrated} Dokumente wurden migriert.', 'success')
        return jsonify({
            'success': True,
            'total_migrated': total_migrated,
            'results': results
        })

    except Exception as e:
        flash(f'Fehler bei der Migration: [Interner Fehler]', 'error')
        return jsonify({'success': False, 'error': 'Ein interner Fehler ist aufgetreten.'}), 500

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
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

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
                    'error': 'Ein interner Fehler ist aufgetreten.'
                }

        return jsonify(status)

    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'}), 500

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
        print(f"Fehler bei Timesheet-Migration: [Interner Fehler]")
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
        print(f"Migration-Fehler (nicht kritisch): [Interner Fehler]")

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

    return render_template('weekly_reports/timesheet_list.html',
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
            return redirect(url_for('weekly_reports.timesheet_create'))
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
        return redirect(url_for('weekly_reports.timesheet_list'))
    return render_template('weekly_reports/timesheet.html', now=datetime.now())

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
            print(f"DEBUG: ObjectId-Konvertierung fehlgeschlagen: [Interner Fehler]")
            found_id = None

    if not ts:
        print(f"DEBUG: Kein Timesheet gefunden für ID: {ts_id}")
        flash('Wochenplan nicht gefunden oder keine Berechtigung.', 'error')
        return redirect(url_for('weekly_reports.timesheet_list'))

    if request.method == 'POST':
        week = request.form.get('week')
        if week and '-W' in week:
            year, week_str = week.split('-W')
            calendar_week = int(week_str)
            year = int(year)
        else:
            flash('Ungültiges Wochenformat.', 'error')
            return redirect(url_for('weekly_reports.timesheet_edit', ts_id=ts_id))

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
        return redirect(url_for('weekly_reports.timesheet_list'))
    return render_template('weekly_reports/timesheet.html', ts=ts, now=datetime.now(), datetime=datetime, timedelta=timedelta)

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
            print(f"DEBUG: ObjectId-Konvertierung fehlgeschlagen: [Interner Fehler]")

    if not ts:
        print(f"DEBUG: Kein Timesheet gefunden für ID: {ts_id}")
        flash('Wochenplan nicht gefunden oder keine Berechtigung.', 'error')
        return redirect(url_for('weekly_reports.timesheet_list'))
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
        print(f"Quick-Update Fehler: [Interner Fehler]")
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
        return redirect(url_for('weekly_reports.timesheet_list'))
    # Nur Besitzer oder Admin darf löschen
    if ts.get('user_id') != current_user.username and not current_user.is_admin:
        flash('Sie dürfen nur Ihre eigenen Wochenberichte löschen.', 'error')
        return redirect(url_for('weekly_reports.timesheet_list'))

    # Verwende die ID für alle Abfragen
    mongodb.delete_one('timesheets', {'_id': ts_id_for_update})
    flash('Wochenbericht wurde gelöscht.', 'success')
    return redirect(url_for('weekly_reports.timesheet_list'))