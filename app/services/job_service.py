from datetime import datetime, timedelta
from app.models.job import Job
from app.utils.logger import loggers
from bson import ObjectId
from typing import Tuple

class JobService:
    """Service für Job-Management"""
    
    @staticmethod
    def get_active_jobs(filters=None, page=1, per_page=12):
        """Aktive Jobs mit Filtern und Pagination abrufen"""
        try:
            from app.models.mongodb_database import get_mongodb
            mongodb = get_mongodb()
            
            # Basis-Filter für aktive Jobs (ohne is_public, da nicht alle Jobs dieses Feld haben)
            query = {'is_active': True}
            

            
            # Zusätzliche Filter anwenden
            if filters:
                if filters.get('search'):
                    search_term = filters['search']
                    # Erweitere $or um Suchbegriffe
                    if '$or' in query:
                        query['$and'] = [
                            {'$or': query['$or']},
                            {'$or': [
                                {'title': {'$regex': search_term, '$options': 'i'}},
                                {'company': {'$regex': search_term, '$options': 'i'}},
                                {'description': {'$regex': search_term, '$options': 'i'}},
                                {'location': {'$regex': search_term, '$options': 'i'}}
                            ]}
                        ]
                        del query['$or']
                    else:
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
            
            # Gesamtanzahl für Pagination
            total_count = mongodb.count_documents('jobs', query)
            
            # Jobs mit Pagination abrufen
            skip = (page - 1) * per_page
            jobs_data = mongodb.find('jobs', query, skip=skip, limit=per_page, sort=[('created_at', -1)])
            
            # Jobs in Job-Objekte konvertieren
            jobs = []
            for job_data in jobs_data:
                job = Job(job_data)
                jobs.append(job)
            
            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                'jobs': jobs,
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Abrufen der aktiven Jobs: {str(e)}")
            return {
                'jobs': [],
                'total_count': 0,
                'total_pages': 0,
                'current_page': page,
                'per_page': per_page
            }
    
    @staticmethod
    def get_job_by_id(job_id):
        """Holt einen Job anhand der ID"""
        try:
            from app.models.mongodb_database import get_mongodb
            mongodb = get_mongodb()
            
            # Versuche ObjectId-Konvertierung
            try:
                obj_id = ObjectId(job_id)
                job_data = mongodb.find_one('jobs', {'_id': obj_id})
            except:
                # Falls ObjectId-Konvertierung fehlschlägt, suche nach job_number
                job_data = mongodb.find_one('jobs', {'job_number': int(job_id) if job_id.isdigit() else job_id})
            
            if job_data:

                return Job(job_data)
            return None
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Abrufen des Jobs {job_id}: {str(e)}")
            return None
    
    @staticmethod
    def create_job(data, user):
        """Neuen Job erstellen"""
        try:
            from datetime import datetime
            from app.models.mongodb_database import get_mongodb
            
            mongodb = get_mongodb()
            
            # Fortlaufende Job-ID generieren - einfachere Methode
            all_jobs = mongodb.find('jobs', {})
            next_job_number = 1
            for job in all_jobs:
                if 'job_number' in job and job['job_number'] >= next_job_number:
                    next_job_number = job['job_number'] + 1
            

            
            # Job-Daten vorbereiten
            job_data = {
                'job_number': next_job_number,  # Fortlaufende Nummer
                'title': data['title'],
                'company': data['company'],
                'location': data.get('location', ''),
                'industry': data.get('industry', ''),
                'job_type': data.get('job_type', 'Vollzeit'),
                'description': data['description'],
                'requirements': data.get('requirements', ''),
                'benefits': data.get('benefits', ''),
                'salary_range': data.get('salary_range', ''),
                'contact_email': data.get('contact_email', ''),
                'contact_phone': data.get('contact_phone', ''),
                'application_url': data.get('application_url', ''),
                'created_by': str(user.id),
                'created_by_name': user.username or user.role or 'Unbekannt',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'is_active': True,
                'is_public': True,
                'views': 0,
                'applications': 0
            }
            
            # Job in DB einfügen
            job_id = mongodb.insert_one('jobs', job_data)
            
            if job_id:
                # Job-Objekt mit ID erstellen
                job_data['_id'] = job_id
                job = Job(job_data)
                loggers['user_actions'].info(f"Job erstellt: {data['title']} bei {data['company']} (ID: {job_id}, Nummer: {next_job_number})")
                return job
            else:
                loggers['errors'].error("Fehler beim Erstellen des Jobs: Keine ID zurückgegeben")
                return None
                
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Erstellen des Jobs: {str(e)}")
            return None
    
    @staticmethod
    def update_job(job_id, data, user):
        """Job aktualisieren"""
        try:
            from app.models.mongodb_database import get_mongodb
            from bson import ObjectId
            from datetime import datetime
            
            mongodb = get_mongodb()
            
            # Job finden
            job = mongodb.find_one('jobs', {'_id': ObjectId(job_id)})
            if not job:
                loggers['errors'].error(f"Job nicht gefunden für Update: {job_id}")
                return None
            
            # Berechtigung prüfen: Admin oder Job-Ersteller
            if user.role != 'admin' and job.get('created_by') != str(user.id):
                loggers['errors'].error(f"Keine Berechtigung zum Bearbeiten des Jobs {job_id} von {user.username}")
                return None
            

            
            # Update-Daten vorbereiten
            update_data = {
                'title': data['title'],
                'company': data['company'],
                'location': data.get('location', ''),
                'industry': data.get('industry', ''),
                'job_type': data.get('job_type', 'Vollzeit'),
                'description': data['description'],
                'requirements': data.get('requirements', ''),
                'benefits': data.get('benefits', ''),
                'salary_range': data.get('salary_range', ''),
                'contact_email': data.get('contact_email', ''),
                'contact_phone': data.get('contact_phone', ''),
                'application_url': data.get('application_url', ''),

                'updated_at': datetime.now()
            }
            
            # Job aktualisieren
            result = mongodb.update_one('jobs', {'_id': ObjectId(job_id)}, update_data)
            
            if result:
                # Aktualisierten Job abrufen
                updated_job = mongodb.find_one('jobs', {'_id': ObjectId(job_id)})
                if updated_job:
                    # Job-Objekt korrekt erstellen
                    job_obj = Job(updated_job)
                    loggers['user_actions'].info(f"Job aktualisiert: {data['title']} von {user.username}")
                    return job_obj
                else:
                    loggers['errors'].error(f"Job nach Update nicht gefunden: {job_id}")
                    return None
            else:
                loggers['errors'].error(f"Fehler beim Aktualisieren des Jobs {job_id}")
                return None
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Aktualisieren des Jobs {job_id}: {str(e)}")
            return None
    
    @staticmethod
    def delete_job(job_id, user):
        """Job löschen (soft delete)"""
        try:
            job = Job.find_by_id(job_id)
            if not job or job.created_by != str(user.id):
                return False
            
            
            
            job.is_active = False
            job.save()
            
            loggers['user_actions'].info(f"Job gelöscht: {job.title} von {user.username}")
            return True
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Löschen des Jobs {job_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_job_statistics():
        """Job-Statistiken abrufen"""
        try:
            from app.models.mongodb_database import get_mongodb
            mongodb = get_mongodb()
            
            # Statistiken abrufen
            total_jobs = mongodb.count_documents('jobs', {'is_active': True})
            active_jobs = mongodb.count_documents('jobs', {'is_active': True, 'is_public': True})
            

            
            # Views und Bewerbungen summieren
            pipeline = [
                {'$match': {'is_active': True}},
                {'$group': {
                    '_id': None,
                    'total_views': {'$sum': '$views'},
                    'total_applications': {'$sum': '$applications'}
                }}
            ]
            stats_result = list(mongodb.aggregate('jobs', pipeline))
            
            total_views = stats_result[0]['total_views'] if stats_result else 0
            total_applications = stats_result[0]['total_applications'] if stats_result else 0
            
            # Top Branchen
            pipeline = [
                {'$match': {'is_active': True, 'is_public': True}},
                {'$group': {'_id': '$industry', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 5}
            ]
            top_industries = list(mongodb.aggregate('jobs', pipeline))
            
            return {
                'total_jobs': total_jobs,
                'active_jobs': active_jobs,

                'total_views': total_views,
                'total_applications': total_applications,
                'top_industries': top_industries
            }
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Abrufen der Job-Statistiken: {str(e)}")
            return {
                'total_jobs': 0,
                'active_jobs': 0,

                'total_views': 0,
                'total_applications': 0,
                'top_industries': []
            }

    @staticmethod
    def get_jobs(filters=None, page=1, per_page=12):
        """Jobs mit Filtern abrufen"""
        try:
            from app.models.mongodb_database import get_mongodb
            
            # Filter vorbereiten
            query = {}  # Zeige alle Jobs an
            
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
            mongodb = get_mongodb()
            skip = (page - 1) * per_page
            
            jobs_data = mongodb.find('jobs', query, skip=skip, limit=per_page, sort=[('created_at', -1)])
            
            # Jobs in Job-Objekte konvertieren
            jobs = []
            for job_data in jobs_data:
                job = Job(job_data)
                jobs.append(job)
            
            # Gesamtanzahl für Pagination
            total_count = mongodb.count_documents('jobs', query)
            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                'jobs': jobs,
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Abrufen der Jobs: {str(e)}")
            return {
                'jobs': [],
                'total_count': 0,
                'total_pages': 0,
                'current_page': page,
                'per_page': per_page
            }

 