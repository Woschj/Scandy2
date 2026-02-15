from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.services.job_service import JobService
from app.models.mongodb_database import get_mongodb, is_feature_enabled
from app.utils.decorators import mitarbeiter_required
from app.utils.logger import loggers

import json
from bson import ObjectId
from datetime import datetime

bp = Blueprint('jobs', __name__)



@bp.route('/')
def job_list():
    """Job-Übersicht"""
    # Jobbörse ist global aktiviert
    
    try:
        # Filter aus Request
        filters = {}
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        if request.args.get('industry'):
            filters['industry'] = request.args.get('industry')
        if request.args.get('job_type'):
            filters['job_type'] = request.args.get('job_type')
        if request.args.get('location'):
            filters['location'] = request.args.get('location')
        
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = 12
        
        loggers['user_actions'].info(f"Job-Liste abgerufen - Filter: {filters}, Seite: {page}")
        
        # Jobs direkt aus MongoDB abrufen
        mongodb = get_mongodb()
        
        # Filter vorbereiten: Öffentlich sichtbare, aktive Jobs
        query = {'is_active': True, 'is_public': True}
        
        if filters:
            if filters.get('search'):
                search_term = filters['search']
                query['$or'] = [
                    {'title': {'$regex': search_term, '$options': 'i'}},
                    {'company': {'$regex': search_term, '$options': 'i'}},
                    {'description': {'$regex': search_term, '$options': 'i'}}
                ]
            
            if filters.get('industry'):
                query['industry'] = filters['industry']
            
            if filters.get('job_type'):
                query['job_type'] = filters['job_type']
            
            if filters.get('location'):
                query['location'] = {'$regex': filters['location'], '$options': 'i'}
        
        # Jobs abrufen
        skip = (page - 1) * per_page
        jobs_data_raw = list(mongodb.find('jobs', query, skip=skip, limit=per_page, sort=[('created_at', -1)]))
        
        # Gesamtanzahl für Pagination
        total_count = mongodb.count_documents('jobs', query)
        total_pages = (total_count + per_page - 1) // per_page
        
        loggers['user_actions'].info(f"Jobs abgerufen: {len(jobs_data_raw)} von {total_count}")
        
        # Statistiken für Sidebar
        stats = JobService.get_job_statistics()
        
        loggers['user_actions'].info(f"Statistiken: {stats}")
        
        # Verfügbare Branchen aus der Datenbank sammeln
        available_industries = mongodb.distinct('jobs', 'industry')
        available_industries = [ind for ind in available_industries if ind and ind.strip()]  # Leere Werte entfernen
        
        # MongoDB-Daten für Template vorbereiten
        jobs_data = []
        for job in jobs_data_raw:
            # Stelle sicher, dass job ein Dictionary ist
            if hasattr(job, 'to_dict'):
                # Falls es ein Job-Objekt ist, konvertiere es zu Dictionary
                job_dict = job.to_dict()
            else:
                # Falls es bereits ein Dictionary ist
                job_dict = {
                    'id': str(job.get('_id', 'unknown')),
                    'title': job.get('title', ''),
                    'company': job.get('company', ''),
                    'location': job.get('location', ''),
                    'industry': job.get('industry', ''),
                    'job_type': job.get('job_type', 'Vollzeit'),
                    'description': job.get('description', ''),
                    'requirements': job.get('requirements', ''),
                    'benefits': job.get('benefits', ''),
                    'salary_range': job.get('salary_range', ''),
                    'contact_email': job.get('contact_email', ''),
                    'contact_phone': job.get('contact_phone', ''),
                    'application_url': job.get('application_url', ''),
                    'created_by': job.get('created_by'),
                    'created_at': job.get('created_at'),
                    'updated_at': job.get('updated_at'),
                    'is_active': job.get('is_active', True),
                    'is_public': job.get('is_public', True),
                    'views': job.get('views', 0),
                    'applications': job.get('applications', 0),
                    'job_number': job.get('job_number'),
                    'images': job.get('images', [])
                }
            jobs_data.append(job_dict)
        
        return render_template('jobs/index.html', 
                             jobs=jobs_data,
                             total_count=total_count,
                             total_pages=total_pages,
                             current_page=page,
                             filters=filters,
                             stats=stats,
                             available_industries=available_industries)
                             
    except Exception as e:
        loggers['errors'].error(f"Fehler in job_list: [Interner Fehler]")
        import traceback
        loggers['errors'].error(f"Traceback: {traceback.format_exc()}")
        flash('Fehler beim Laden der Jobs', 'error')
        return render_template('jobs/index.html', 
                             jobs=[], 
                             stats={}, 
                             filters={}, 
                             total_count=0, 
                             total_pages=0, 
                             current_page=1, 
                             available_industries=[])

@bp.route('/create', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def create_job():
    """Job erstellen"""
    # Jobbörse ist global aktiviert
    
    if request.method == 'POST':
        try:
            data = {
                'title': request.form.get('title', '').strip(),
                'company': request.form.get('company', '').strip(),
                'location': request.form.get('location', '').strip(),
                'industry': request.form.get('industry', '').strip(),
                'job_type': request.form.get('job_type', 'Vollzeit'),
                'description': request.form.get('description', '').strip(),
                'requirements': request.form.get('requirements', '').strip(),
                'benefits': request.form.get('benefits', '').strip(),
                'salary_range': request.form.get('salary_range', '').strip(),
                'contact_email': request.form.get('contact_email', '').strip(),
                'contact_phone': request.form.get('contact_phone', '').strip(),
                'application_url': request.form.get('application_url', '').strip(),

            }
            
            # Validierung
            if not data['title'] or not data['company'] or not data['description']:
                flash('Bitte füllen Sie alle Pflichtfelder aus', 'error')
                return render_template('jobs/create.html', data=data)
            
            # Job erstellen
            job = JobService.create_job(data, current_user)
            if job:
                flash(f'Job "{job.title}" erfolgreich erstellt!', 'success')
                return redirect(url_for('jobs.job_detail', job_id=str(job.id)))
            else:
                flash('Fehler beim Erstellen des Jobs', 'error')
                
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Erstellen des Jobs: [Interner Fehler]")
            flash('Fehler beim Erstellen des Jobs', 'error')
    
    # Leere data für GET-Request oder bei Fehlern
    data = {
        'title': '',
        'company': '',
        'location': '',
        'industry': '',
        'job_type': 'Vollzeit',
        'description': '',
        'requirements': '',
        'benefits': '',
        'salary_range': '',
        'contact_email': '',
        'contact_phone': '',
        'application_url': ''
    }
    
    return render_template('jobs/create.html', data=data)

@bp.route('/<job_id>')
def job_detail(job_id):
    """Job-Details"""
    # Jobbörse ist global aktiviert
    
    try:
        loggers['user_actions'].info(f"Job-Detail abgerufen für ID: {job_id}")
        job = JobService.get_job_by_id(job_id)
        if not job:
            loggers['errors'].error(f"Job nicht gefunden für ID: {job_id}")
            flash('Job nicht gefunden', 'error')
            return redirect(url_for('jobs.job_list'))
        
        # Zugriff: Gäste dürfen nur aktive, öffentliche Jobs sehen
        is_owner_or_admin = False
        try:
            is_owner_or_admin = current_user.is_authenticated and (
                getattr(current_user, 'role', None) == 'admin' or (job.created_by and str(job.created_by) == str(getattr(current_user, 'id', '')))
            )
        except Exception:
            is_owner_or_admin = False
        if not (job.is_active and job.is_public) and not is_owner_or_admin:
            flash('Dieser Job ist nicht öffentlich sichtbar.', 'error')
            return redirect(url_for('jobs.job_list'))

        loggers['user_actions'].info(f"Job gefunden: {job.title}")
        return render_template('jobs/detail.html', 
                             job=job, entity_type='jobs', entity_id=job_id)
                             
    except Exception as e:
        loggers['errors'].error(f"Fehler in job_detail: [Interner Fehler]")
        flash('Fehler beim Laden der Job-Details', 'error')
        return redirect(url_for('jobs.job_list'))

@bp.route('/<job_id>/edit', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def edit_job(job_id):
    """Job bearbeiten"""
    # Prüfe ob Jobbörse aktiviert ist
    if not is_feature_enabled('job_board'):
        flash('Jobbörse ist deaktiviert', 'error')
        return redirect(url_for('main.index'))
    try:
        job = JobService.get_job_by_id(job_id)
        if not job:
            flash('Job nicht gefunden', 'error')
            return redirect(url_for('jobs.job_list'))
        
        # Berechtigung prüfen: Admin oder Job-Ersteller
        if current_user.role != 'admin' and job.created_by != str(current_user.id):
            flash('Keine Berechtigung zum Bearbeiten dieses Jobs', 'error')
            return redirect(url_for('jobs.job_list'))
        
        if request.method == 'POST':
            data = {
                'title': request.form.get('title', '').strip(),
                'company': request.form.get('company', '').strip(),
                'location': request.form.get('location', '').strip(),
                'industry': request.form.get('industry', '').strip(),
                'job_type': request.form.get('job_type', 'Vollzeit'),
                'description': request.form.get('description', '').strip(),
                'requirements': request.form.get('requirements', '').strip(),
                'benefits': request.form.get('benefits', '').strip(),
                'salary_range': request.form.get('salary_range', '').strip(),
                'contact_email': request.form.get('contact_email', '').strip(),
                'contact_phone': request.form.get('contact_phone', '').strip(),
                'application_url': request.form.get('application_url', '').strip()
            }
            
            # Validierung
            if not data['title'] or not data['company'] or not data['description']:
                flash('Bitte füllen Sie alle Pflichtfelder aus', 'error')
                return render_template('jobs/edit.html', job=job, data=data)
            
            # Job aktualisieren
            updated_job = JobService.update_job(job_id, data, current_user)
            if updated_job:
                flash(f'Job "{updated_job.title}" erfolgreich aktualisiert!', 'success')
                return redirect(url_for('jobs.job_detail', job_id=job_id))
            else:
                flash('Fehler beim Aktualisieren des Jobs', 'error')
                
        return render_template('jobs/edit.html', job=job, entity_type='jobs', entity_id=job_id)
        
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Bearbeiten des Jobs {job_id}: [Interner Fehler]")
        flash('Fehler beim Bearbeiten des Jobs', 'error')
        return redirect(url_for('jobs.job_list'))

@bp.route('/<job_id>/delete', methods=['POST'])
@login_required
@mitarbeiter_required
def delete_job(job_id):
    """Job löschen"""
    # Prüfe ob Jobbörse aktiviert ist
    if not is_feature_enabled('job_board'):
        flash('Jobbörse ist deaktiviert', 'error')
        return redirect(url_for('main.index'))
    
    try:
        success = JobService.delete_job(job_id, current_user)
        if success:
            flash('Job erfolgreich gelöscht', 'success')
        else:
            flash('Fehler beim Löschen des Jobs', 'error')
            
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Löschen des Jobs {job_id}: [Interner Fehler]")
        flash('Fehler beim Löschen des Jobs', 'error')
    
    return redirect(url_for('jobs.job_list'))

@bp.route('/api/jobs')
def api_jobs():
    """Jobs als JSON API"""
    try:
        filters = {}
        if request.args.get('search'):
            filters['search'] = request.args.get('search')
        if request.args.get('industry'):
            filters['industry'] = request.args.get('industry')
        if request.args.get('job_type'):
            filters['job_type'] = request.args.get('job_type')
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 12))
        
        result = JobService.get_active_jobs(filters, page, per_page)
        
        # Jobs zu JSON konvertieren
        jobs_json = [job.to_dict() for job in result['jobs']]
        
        return jsonify({
            'jobs': jobs_json,
            'total_count': result['total_count'],
            'total_pages': result['total_pages'],
            'current_page': result['current_page']
        })
        
    except Exception as e:
        loggers['errors'].error(f"Fehler in API jobs: [Interner Fehler]")
        return jsonify({'error': 'Fehler beim Abrufen der Jobs'}), 500

@bp.route('/api/jobs/<job_id>')
def api_job_detail(job_id):
    """Job-Details als JSON API"""
    try:
        job = JobService.get_job_by_id(job_id)
        if not job:
            return jsonify({'error': 'Job nicht gefunden'}), 404
        
        return jsonify(job.to_dict())
        
    except Exception as e:
        loggers['errors'].error(f"Fehler in API job detail: [Interner Fehler]")
        return jsonify({'error': 'Fehler beim Abrufen der Job-Details'}), 500 

@bp.route('/debug-jobs')
@login_required
@mitarbeiter_required
def debug_jobs():
    """Debug: Jobs anzeigen"""
    try:
        from app.models.mongodb_database import get_mongodb
        
        mongodb = get_mongodb()
        
        # Alle Jobs finden
        jobs = mongodb.find('jobs', {})
        
        job_list = []
        for job in jobs:
            job_list.append({
                'id': str(job.get('_id', 'KEINE_ID')),
                'title': job.get('title', 'KEIN_TITEL'),
                'company': job.get('company', 'KEINE_FIRMA'),
                'has_id': '_id' in job
            })
        
        return jsonify({
            'jobs': job_list,
            'total': len(job_list)
        })
        
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'})

@bp.route('/debug-test')
def test_jobs():
    """Test-Route für Job-Abfrage"""
    try:
        loggers['user_actions'].info("TEST: Job-Abfrage gestartet")
        
        # Direkte MongoDB-Abfrage
        from app.models.mongodb_database import get_mongodb
        mongodb = get_mongodb()
        
        # Alle Jobs abrufen
        all_jobs = list(mongodb.find('jobs', {}))
        loggers['user_actions'].info(f"TEST: Alle Jobs in DB: {len(all_jobs)}")
        
        # Aktive Jobs abrufen
        active_jobs = list(mongodb.find('jobs', {'is_active': True}))
        loggers['user_actions'].info(f"TEST: Aktive Jobs: {len(active_jobs)}")
        
        # Öffentliche Jobs abrufen
        public_jobs = list(mongodb.find('jobs', {'is_public': True}))
        loggers['user_actions'].info(f"TEST: Öffentliche Jobs: {len(public_jobs)}")
        
        # Beide Filter
        both_jobs = list(mongodb.find('jobs', {'is_active': True, 'is_public': True}))
        loggers['user_actions'].info(f"TEST: Aktive + Öffentliche Jobs: {len(both_jobs)}")
        
        # JobService testen
        result = JobService.get_active_jobs({}, 1, 12)
        loggers['user_actions'].info(f"TEST: JobService Ergebnis: {len(result['jobs'])} Jobs")
        
        return jsonify({
            'all_jobs_count': len(all_jobs),
            'active_jobs_count': len(active_jobs),
            'public_jobs_count': len(public_jobs),
            'both_jobs_count': len(both_jobs),
            'jobservice_result': len(result['jobs']),
            'all_jobs': [{'id': str(job.get('_id')), 'title': job.get('title'), 'is_active': job.get('is_active'), 'is_public': job.get('is_public')} for job in all_jobs[:5]],
            'active_jobs': [{'id': str(job.get('_id')), 'title': job.get('title'), 'is_active': job.get('is_active'), 'is_public': job.get('is_public')} for job in active_jobs[:5]],
            'public_jobs': [{'id': str(job.get('_id')), 'title': job.get('title'), 'is_active': job.get('is_active'), 'is_public': job.get('is_public')} for job in public_jobs[:5]],
            'both_jobs': [{'id': str(job.get('_id')), 'title': job.get('title'), 'is_active': job.get('is_active'), 'is_public': job.get('is_public')} for job in both_jobs[:5]]
        })
        
    except Exception as e:
        loggers['errors'].error(f"TEST Fehler: [Interner Fehler]")
        import traceback
        loggers['errors'].error(f"TEST Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'})



@bp.route('/fix-test-job')
def fix_test_job():
    """Test-Job reparieren"""
    try:
        from app.models.mongodb_database import get_mongodb
        mongodb = get_mongodb()
        
        # Test-Job finden und reparieren
        job_id = "68807bdb67355795efee2295"
        result = mongodb.update_one('jobs', 
                                  {'_id': ObjectId(job_id)}, 
                                  {'$set': {'is_public': True}})
        
        # Job nach Update abrufen
        job = mongodb.find_one('jobs', {'_id': ObjectId(job_id)})
        
        return jsonify({
            'updated': result if isinstance(result, bool) else result.modified_count > 0,
            'job': {
                'id': str(job.get('_id')),
                'title': job.get('title'),
                'is_active': job.get('is_active'),
                'is_public': job.get('is_public')
            } if job else None
        })
        
    except Exception as e:
                return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'})





@bp.route('/create-test-job')
def create_test_job():
    """Test-Job erstellen"""
    try:
        from app.models.mongodb_database import get_mongodb
        from bson import ObjectId
        from datetime import datetime
        
        mongodb = get_mongodb()
        
        # Test-Job Daten
        test_job = {
            'title': 'Softwareentwickler (m/w/d)',
            'company': 'TechCorp GmbH',
            'location': 'Berlin',
            'industry': 'IT',
            'job_type': 'Vollzeit',
            'description': 'Wir suchen einen erfahrenen Softwareentwickler für unser innovatives Team. Sie werden an spannenden Projekten arbeiten und moderne Technologien einsetzen.',
            'requirements': 'Bachelor in Informatik oder ähnlichem, 3+ Jahre Erfahrung mit Python/JavaScript, Teamplayer',
            'benefits': 'Flexible Arbeitszeiten, Homeoffice, Weiterbildung, attraktives Gehalt',
            'salary_range': '60.000 - 80.000 €',
            'contact_email': 'jobs@techcorp.de',
            'contact_phone': '+49 30 12345678',
            'application_url': 'https://techcorp.de/karriere',
            'created_by': '688094e58d50ce480a2cf9e7',  # Admin User ID
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'is_active': True,
            'is_public': True,
            'views': 0,
            'applications': 0
        }
        
        # Job in DB einfügen
        job_id = mongodb.insert_one('jobs', test_job)
        
        # Job nach Insert abrufen
        job = mongodb.find_one('jobs', {'_id': job_id})
        
        return jsonify({
            'created': True,
            'job_id': str(job_id),
            'job': {
                'id': str(job.get('_id')),
                'title': job.get('title'),
                'company': job.get('company'),
                'is_active': job.get('is_active'),
                'is_public': job.get('is_public')
            }
        })
        
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'})

@bp.route('/fix-job-numbers')
@login_required
@mitarbeiter_required
def fix_job_numbers():
    """Bestehenden Jobs fortlaufende Nummern geben"""
    try:
        from app.models.mongodb_database import get_mongodb
        
        mongodb = get_mongodb()
        
        # Alle Jobs ohne job_number finden
        jobs_without_number = mongodb.find('jobs', {'job_number': {'$exists': False}})
        
        if not jobs_without_number:
            flash('Alle Jobs haben bereits Nummern!', 'info')
            return redirect(url_for('jobs.job_list'))
        
        # Höchste bestehende Nummer finden - einfachere Methode
        all_jobs = mongodb.find('jobs', {'job_number': {'$exists': True}})
        next_number = 1
        for job in all_jobs:
            if 'job_number' in job and job['job_number'] >= next_number:
                next_number = job['job_number'] + 1
        
        # Jobs nummerieren
        updated_count = 0
        for job in jobs_without_number:
            mongodb.update_one('jobs', {'_id': job['_id']}, {'$set': {'job_number': next_number}})
            next_number += 1
            updated_count += 1
        
        flash(f'{updated_count} Jobs wurden mit Nummern versehen!', 'success')
        return redirect(url_for('jobs.job_list'))
        
    except Exception as e:
        flash(f'Fehler beim Nummerieren der Jobs: [Interner Fehler]', 'error')
        return redirect(url_for('jobs.job_list')) 

@bp.route('/debug-fix-ids')
@login_required
@mitarbeiter_required
def debug_fix_ids():
    """Debug: Job-IDs reparieren"""
    try:
        from app.models.mongodb_database import get_mongodb
        
        mongodb = get_mongodb()
        
        # Alle Jobs finden
        jobs = mongodb.find('jobs', {})
        
        fixed_count = 0
        for job in jobs:
            job_id = str(job.get('_id', ''))
            job_number = job.get('job_number', 0)
            
            # Stelle sicher, dass die ID als String gespeichert ist
            if job_id and job_id != 'None':
                # Job hat bereits ID, aber möglicherweise nicht als String
                mongodb.update_one('jobs', {'_id': job['_id']}, {'$set': {'_id_str': job_id}})
                fixed_count += 1
            elif job_number:
                # Job hat job_number aber keine _id, verwende job_number als ID
                mongodb.update_one('jobs', {'job_number': job_number}, {'$set': {'_id_str': str(job_number)}})
                fixed_count += 1
        
        return jsonify({
            'message': f'{fixed_count} Jobs wurden repariert',
            'jobs_found': len(list(jobs))
        })
        
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'})

 

@bp.route('/fix-all-job-ids')
@login_required
@mitarbeiter_required
def fix_all_job_ids():
    """Alle Jobs mit IDs versehen"""
    try:
        from app.models.mongodb_database import get_mongodb
        
        mongodb = get_mongodb()
        
        # Alle Jobs finden
        jobs = mongodb.find('jobs', {})
        
        fixed_count = 0
        for job in jobs:
            job_id = str(job.get('_id', ''))
            job_number = job.get('job_number', 0)
            
            # Falls Job keine _id hat, aber job_number, verwende job_number als ID
            if not job_id or job_id == 'None' or job_id == '':
                if job_number:
                    # Verwende job_number als ID
                    mongodb.update_one('jobs', {'job_number': job_number}, {'$set': {'_id_str': str(job_number)}})
                    fixed_count += 1
                else:
                    # Erstelle eine neue job_number
                    all_jobs = mongodb.find('jobs', {'job_number': {'$exists': True}})
                    next_number = 1
                    for existing_job in all_jobs:
                        if 'job_number' in existing_job and existing_job['job_number'] >= next_number:
                            next_number = existing_job['job_number'] + 1
                    
                    mongodb.update_one('jobs', {'_id': job['_id']}, {'$set': {'job_number': next_number, '_id_str': str(next_number)}})
                    fixed_count += 1
            else:
                # Job hat _id, stelle sicher, dass _id_str auch gesetzt ist
                mongodb.update_one('jobs', {'_id': job['_id']}, {'$set': {'_id_str': job_id}})
                fixed_count += 1
        
        return jsonify({
            'message': f'{fixed_count} Jobs wurden mit IDs versehen',
            'jobs_processed': len(list(jobs))
        })
        
    except Exception as e:
        return jsonify({'error': 'Ein interner Fehler ist aufgetreten.'})

# Neue Routen für Kommentare und Löschfunktionen

@bp.route('/<job_id>/comment', methods=['POST'])
@login_required
def add_comment(job_id):
    """Kommentar zu einem Job hinzufügen"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'success': False, 'error': 'Kommentar darf nicht leer sein'})
        
        mongodb = get_mongodb()
        
        # Job existiert?
        job = mongodb.find_one('jobs', {'_id': ObjectId(job_id)})
        if not job:
            return jsonify({'success': False, 'error': 'Job nicht gefunden'})
        
        # Kommentar erstellen
        comment = {
            'id': str(ObjectId()),  # Eindeutige ID für den Kommentar
            'content': content,
            'author_id': str(current_user.id),
            'author_name': current_user.username,
            'created_at': datetime.now(),
            'job_id': job_id
        }
        
        # Kommentar zur Job-Collection hinzufügen
        mongodb.update_one('jobs', 
                          {'_id': ObjectId(job_id)}, 
                          {'$push': {'comments': comment}})
        
        loggers['user_actions'].info(f"Kommentar zu Job {job_id} hinzugefügt von {current_user.username}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Hinzufügen des Kommentars: [Interner Fehler]")
        return jsonify({'success': False, 'error': 'Ein interner Fehler ist aufgetreten.'})

@bp.route('/comment/<comment_id>/delete', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """Kommentar löschen"""
    try:
        mongodb = get_mongodb()
        
        # Kommentar finden
        job = mongodb.find_one('jobs', {'comments.id': comment_id})
        if not job:
            return jsonify({'success': False, 'error': 'Kommentar nicht gefunden'})
        
        # Kommentar in der Job-Collection finden
        comment = None
        for c in job.get('comments', []):
            if c.get('id') == comment_id:
                comment = c
                break
        
        if not comment:
            return jsonify({'success': False, 'error': 'Kommentar nicht gefunden'})
        
        # Berechtigung prüfen: Admin oder Kommentar-Autor
        if current_user.role != 'admin' and comment.get('author_id') != str(current_user.id):
            return jsonify({'success': False, 'error': 'Keine Berechtigung zum Löschen dieses Kommentars'})
        
        # Kommentar entfernen
        mongodb.update_one('jobs', 
                          {'_id': job['_id']}, 
                          {'$pull': {'comments': {'id': comment_id}}})
        
        loggers['user_actions'].info(f"Kommentar {comment_id} gelöscht von {current_user.username}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Löschen des Kommentars: [Interner Fehler]")
        return jsonify({'success': False, 'error': 'Ein interner Fehler ist aufgetreten.'})

@bp.route('/<job_id>/delete', methods=['DELETE'])
@login_required
def delete_job_api(job_id):
    """Job über API löschen"""
    try:
        mongodb = get_mongodb()
        
        # Job finden
        job = mongodb.find_one('jobs', {'_id': ObjectId(job_id)})
        if not job:
            return jsonify({'success': False, 'error': 'Job nicht gefunden'})
        
        # Berechtigung prüfen: Admin oder Job-Ersteller
        if current_user.role != 'admin' and job.get('created_by') != str(current_user.id):
            return jsonify({'success': False, 'error': 'Keine Berechtigung zum Löschen dieses Jobs'})
        
        # Job löschen
        mongodb.delete_one('jobs', {'_id': ObjectId(job_id)})
        
        loggers['user_actions'].info(f"Job {job_id} gelöscht von {current_user.username}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Löschen des Jobs: [Interner Fehler]")
        return jsonify({'success': False, 'error': 'Ein interner Fehler ist aufgetreten.'})

@bp.route('/fix-job-creator/<job_id>')
def fix_job_creator(job_id):
    """Temporäre Route zum Reparieren des Job-Erstellers"""
    try:
        mongodb = get_mongodb()
        
        # Job finden
        job_data = mongodb.find_one('jobs', {'_id': ObjectId(job_id)})
        if not job_data:
            return jsonify({'success': False, 'error': 'Job nicht gefunden'})
        
        # created_by_name hinzufügen falls nicht vorhanden
        if 'created_by_name' not in job_data or not job_data['created_by_name']:
            # Versuche den Benutzer zu finden
            if job_data.get('created_by'):
                user_data = mongodb.find_one('users', {'_id': ObjectId(job_data['created_by'])})
                if user_data:
                    created_by_name = user_data.get('username') or user_data.get('role') or 'Admin'
                else:
                    created_by_name = 'Admin'
            else:
                created_by_name = 'Admin'
            
            # Job aktualisieren
            mongodb.update_one('jobs', 
                              {'_id': ObjectId(job_id)}, 
                              {'$set': {'created_by_name': created_by_name}})
            
            return jsonify({'success': True, 'created_by_name': created_by_name})
        else:
            return jsonify({'success': True, 'created_by_name': job_data['created_by_name']})
            
    except Exception as e:
        return jsonify({'success': False, 'error': 'Ein interner Fehler ist aufgetreten.'})

@bp.route('/delete-all', methods=['DELETE'])
@login_required
def delete_all_jobs():
    """Alle Jobs löschen (nur für Admins)"""
    try:
        if current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Nur Admins können alle Jobs löschen'})
        
        mongodb = get_mongodb()
        
        # Alle aktiven Jobs löschen
        result = mongodb.delete_many('jobs', {'is_active': True})
        
        loggers['user_actions'].info(f"Alle Jobs gelöscht von {current_user.username} ({result.deleted_count} Jobs)")
        
        return jsonify({'success': True, 'deleted_count': result.deleted_count})
        
    except Exception as e:
        loggers['errors'].error(f"Fehler beim Löschen aller Jobs: [Interner Fehler]")
        return jsonify({'success': False, 'error': 'Ein interner Fehler ist aufgetreten.'})