from datetime import datetime
from app.models.mongodb_database import get_mongodb
from bson import ObjectId
import json

class Job:
    """Job-Modell für die Jobbörse"""
    
    def __init__(self, data=None):
        if data is None:
            data = {}
        
        # ID korrekt setzen - verschiedene Möglichkeiten
        self.id = None
        if '_id' in data:
            self.id = str(data['_id'])
        elif 'id' in data:
            self.id = str(data['id'])
        elif 'job_id' in data:
            self.id = str(data['job_id'])
        
        # Falls immer noch keine ID, versuche job_number zu verwenden
        if not self.id and 'job_number' in data:
            self.id = str(data['job_number'])
        
        # Falls immer noch keine ID, verwende einen Fallback
        if not self.id:
            self.id = "unknown"
        
        self.title = data.get('title', '')
        self.company = data.get('company', '')
        self.location = data.get('location', '')
        self.industry = data.get('industry', '')
        self.job_type = data.get('job_type', 'Vollzeit')
        self.description = data.get('description', '')
        self.requirements = data.get('requirements', '')
        self.benefits = data.get('benefits', '')
        self.salary_range = data.get('salary_range', '')
        self.contact_email = data.get('contact_email', '')
        self.contact_phone = data.get('contact_phone', '')
        self.application_url = data.get('application_url', '')
        self.created_by = data.get('created_by')
        self.created_by_name = data.get('created_by_name')
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())
        self.is_active = data.get('is_active', True)
        self.is_public = data.get('is_public', True)
        self.views = data.get('views', 0)
        self.applications = data.get('applications', 0)
        self.job_number = data.get('job_number')
        self.comments = data.get('comments', [])

        

    
    def to_dict(self):
        """Konvertiert Job zu Dictionary"""
        return {
            'id': str(self.id) if self.id else None,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'industry': self.industry,
            'job_type': self.job_type,
            'description': self.description,
            'requirements': self.requirements,
            'benefits': self.benefits,
            'salary_range': self.salary_range,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'application_url': self.application_url,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_by_name': self.created_by_name,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'views': self.views,
            'applications': self.applications,
            'is_active': self.is_active,
            'is_public': self.is_public,
            'comments': self.comments,

        }
    

    
    def save(self):
        """Speichert den Job in der Datenbank"""
        mongodb = get_mongodb()
        
        job_data = {
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'industry': self.industry,
            'job_type': self.job_type,
            'description': self.description,
            'requirements': self.requirements,
            'benefits': self.benefits,
            'salary_range': self.salary_range,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'application_url': self.application_url,
            'created_by': self.created_by,
            'created_by_name': self.created_by_name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active,
            'is_public': self.is_public,
            'views': self.views,
            'applications': self.applications,
            'job_number': self.job_number,
        }
        
        # Kommentare nur hinzufügen, wenn sie existieren
        if hasattr(self, 'comments') and self.comments:
            job_data['comments'] = self.comments
        
        if self.id and self.id != "unknown":
            # Update existing job
            mongodb.update_one('jobs', {'_id': ObjectId(self.id)}, job_data)
        else:
            # Create new job
            self.id = mongodb.insert_one('jobs', job_data)
        
        return self
    
    @staticmethod
    def find_by_id(job_id):
        """Findet Job anhand ID"""
        try:
            from app.utils.logger import loggers
            loggers['user_actions'].info(f"Job.find_by_id aufgerufen mit ID: {job_id}")
            
            if not ObjectId.is_valid(job_id):
                loggers['errors'].error(f"Ungültige ObjectId: {job_id}")
                return None
            
            mongodb = get_mongodb()
            job_data = mongodb.find_one('jobs', {'_id': ObjectId(job_id)})
            
            if job_data:
                loggers['user_actions'].info(f"Job gefunden in DB: {job_data.get('title', 'Unbekannt')}")

                return Job(job_data)
            else:
                loggers['errors'].error(f"Job nicht in DB gefunden für ID: {job_id}")
            return None
            
        except Exception as e:
            from app.utils.logger import loggers
            loggers['errors'].error(f"Fehler in Job.find_by_id: [Interner Fehler]")
            return None
    
    @staticmethod
    def find_active_jobs(filters=None, page=1, per_page=12):
        """Findet aktive Jobs mit Filtern"""
        try:
            mongodb = get_mongodb()
            
            # Basis-Filter für aktive Jobs
            filter_dict = {'is_active': True, 'is_public': True}
            
            # Basis-Filter für aktive Jobs
            filter_dict = {'is_active': True, 'is_public': True}
            
            if filters:
                if filters.get('industry'):
                    filter_dict['industry'] = {'$regex': filters['industry'], '$options': 'i'}
                if filters.get('job_type'):
                    filter_dict['job_type'] = filters['job_type']
                if filters.get('location'):
                    filter_dict['location'] = {'$regex': filters['location'], '$options': 'i'}
                if filters.get('search'):
                    search_term = filters['search']
                    # Erweitere $or um Suchbegriffe
                    if '$or' in filter_dict:
                        filter_dict['$and'] = [
                            {'$or': filter_dict['$or']},
                            {'$or': [
                                {'title': {'$regex': search_term, '$options': 'i'}},
                                {'company': {'$regex': search_term, '$options': 'i'}},
                                {'description': {'$regex': search_term, '$options': 'i'}}
                            ]}
                        ]
                        del filter_dict['$or']
                    else:
                        filter_dict['$or'] = [
                            {'title': {'$regex': search_term, '$options': 'i'}},
                            {'company': {'$regex': search_term, '$options': 'i'}},
                            {'description': {'$regex': search_term, '$options': 'i'}}
                        ]
            
            # Jobs abrufen
            jobs_data = mongodb.find('jobs', filter_dict, sort=[('created_at', -1)], limit=per_page, skip=(page-1)*per_page)
            jobs = [Job(job_data) for job_data in jobs_data]
            
            # Gesamtanzahl
            total_count = mongodb.count_documents('jobs', filter_dict)
            total_pages = (total_count + per_page - 1) // per_page
            
            return {
                'jobs': jobs,
                'total_count': total_count,
                'total_pages': total_pages,
                'current_page': page,
                'per_page': per_page
            }
            
        except Exception as e:
            # Bei MongoDB-Fehlern: Fallback auf leere Liste
            print(f"Fehler beim Abrufen der Jobs: {e}")
            return {
                'jobs': [],
                'total_count': 0,
                'total_pages': 0,
                'current_page': page,
                'per_page': per_page
            }
    
    def __str__(self):
        return f"{self.title} bei {self.company}" 