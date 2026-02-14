from datetime import datetime
from app.models.experience import Experience
from app.models.job import Job
from app.models.user import User
from app.utils.logger import loggers
from bson import ObjectId

class ExperienceService:
    """Service für Erfahrungsberichte"""
    
    @staticmethod
    def get_experiences_for_job(job_id, limit=10):
        """Erfahrungsberichte für einen Job abrufen"""
        try:
            if not ObjectId.is_valid(job_id):
                return []
            
            experiences = Experience.objects(job=job_id).order_by('-created_at').limit(limit)
            return list(experiences)
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Abrufen der Erfahrungsberichte für Job {job_id}: [Interner Fehler]")
            return []
    
    @staticmethod
    def create_experience(data, user, job_id):
        """Neuen Erfahrungsbericht erstellen"""
        try:
            if not ObjectId.is_valid(job_id):
                return None
            
            job = Job.objects(id=job_id, is_active=True).first()
            if not job:
                return None
            
            experience = Experience(
                job=job,
                author=user,
                rating=data['rating'],
                overall_experience=data.get('overall_experience', 'Neutral'),
                work_environment=data.get('work_environment', 3),
                salary_benefits=data.get('salary_benefits', 3),
                career_growth=data.get('career_growth', 3),
                work_life_balance=data.get('work_life_balance', 3),
                review_title=data.get('review_title', ''),
                review_text=data['review_text'],
                pros=data.get('pros', ''),
                cons=data.get('cons', ''),
                recommendations=data.get('recommendations', ''),
                is_anonymous=data.get('is_anonymous', False)
            )
            
            experience.save()
            loggers['user_actions'].info(f"Erfahrungsbericht erstellt für {job.title} von {user.username}")
            return experience
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Erstellen des Erfahrungsberichts: [Interner Fehler]")
            return None
    
    @staticmethod
    def update_experience(experience_id, data, user):
        """Erfahrungsbericht aktualisieren"""
        try:
            experience = Experience.objects(id=experience_id, author=user).first()
            if not experience:
                return None
            
            # Felder aktualisieren
            for field, value in data.items():
                if hasattr(experience, field):
                    setattr(experience, field, value)
            
            experience.updated_at = datetime.utcnow()
            experience.save()
            
            loggers['user_actions'].info(f"Erfahrungsbericht aktualisiert von {user.username}")
            return experience
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Aktualisieren des Erfahrungsberichts {experience_id}: [Interner Fehler]")
            return None
    
    @staticmethod
    def delete_experience(experience_id, user):
        """Erfahrungsbericht löschen"""
        try:
            experience = Experience.objects(id=experience_id, author=user).first()
            if not experience:
                return False
            
            experience.delete()
            loggers['user_actions'].info(f"Erfahrungsbericht gelöscht von {user.username}")
            return True
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Löschen des Erfahrungsberichts {experience_id}: [Interner Fehler]")
            return False
    
    @staticmethod
    def vote_experience(experience_id, user, is_helpful):
        """Erfahrungsbericht bewerten (hilfreich/nicht hilfreich)"""
        try:
            experience = Experience.objects(id=experience_id).first()
            if not experience:
                return False
            
            if is_helpful:
                experience.helpful_votes += 1
            else:
                experience.not_helpful_votes += 1
            
            experience.save()
            return True
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Bewerten des Erfahrungsberichts {experience_id}: [Interner Fehler]")
            return False
    
    @staticmethod
    def get_experience_statistics(job_id):
        """Statistiken für Erfahrungsberichte eines Jobs"""
        try:
            if not ObjectId.is_valid(job_id):
                return {}
            
            experiences = Experience.objects(job=job_id)
            
            if not experiences:
                return {
                    'total_reviews': 0,
                    'average_rating': 0,
                    'rating_distribution': {},
                    'overall_experience_distribution': {}
                }
            
            # Durchschnittliche Bewertung
            total_rating = sum(exp.rating for exp in experiences)
            average_rating = total_rating / experiences.count()
            
            # Bewertungsverteilung
            rating_distribution = {}
            for i in range(1, 6):
                rating_distribution[i] = experiences.filter(rating=i).count()
            
            # Erfahrungsverteilung
            experience_distribution = {}
            for exp in experiences:
                exp_type = exp.overall_experience or 'Neutral'
                experience_distribution[exp_type] = experience_distribution.get(exp_type, 0) + 1
            
            return {
                'total_reviews': experiences.count(),
                'average_rating': round(average_rating, 1),
                'rating_distribution': rating_distribution,
                'overall_experience_distribution': experience_distribution
            }
            
        except Exception as e:
            loggers['errors'].error(f"Fehler beim Abrufen der Erfahrungsbericht-Statistiken für Job {job_id}: [Interner Fehler]")
            return {
                'total_reviews': 0,
                'average_rating': 0,
                'rating_distribution': {},
                'overall_experience_distribution': {}
            } 