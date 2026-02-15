"""
User-Modell für Flask-Login Integration mit MongoDB
"""
from flask_login import UserMixin
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class User(UserMixin):
    """User-Klasse für Flask-Login Integration"""
    
    def __init__(self, user_data=None):
        if user_data:
            # Verwende normale Attribut-Zuweisung
            # WICHTIG: Speichere die ID immer als String für Konsistenz
            self.id = str(user_data.get('_id'))
            self.username = user_data.get('username')
            self.role = user_data.get('role', 'anwender')
            self.is_admin = user_data.get('role', 'anwender') == 'admin'
            self.is_mitarbeiter = user_data.get('role', 'anwender') in ['admin', 'mitarbeiter']
            self.is_teilnehmer = user_data.get('role', 'anwender') == 'teilnehmer'
            # Speichere is_active als normales Attribut
            self._active = user_data.get('is_active', True)
            
            # Löschdatum-Funktionalität
            self.delete_at = user_data.get('delete_at')
            if self.delete_at and isinstance(self.delete_at, str):
                try:
                    self.delete_at = datetime.fromisoformat(self.delete_at.replace('Z', '+00:00'))
                except Exception as e:
                    logger.warning(f"Fehler bei Datumskonvertierung delete_at: [Interner Fehler]")
                    self.delete_at = None
            

            
            # Wochenbericht-Feature: Prüfe ob Feld existiert, sonst setze Standard
            if 'timesheet_enabled' in user_data:
                # Feld existiert - verwende den gespeicherten Wert
                self.timesheet_enabled = user_data.get('timesheet_enabled', False)
            else:
                # Feld existiert nicht - setze Standard basierend auf Rolle
                if user_data.get('role') in ['anwender', 'teilnehmer']:
                    self.timesheet_enabled = True  # Anwender und Teilnehmer standardmäßig aktiviert
                else:
                    self.timesheet_enabled = False  # Andere Rollen standardmäßig deaktiviert
                
                # Speichere das Feld automatisch in der Datenbank
                self._save_timesheet_enabled(user_data['_id'], self.timesheet_enabled)
            
            # Kantinenplan-Feature: Prüfe ob Feld existiert, sonst setze Standard
            if 'canteen_plan_enabled' in user_data:
                # Feld existiert - verwende den gespeicherten Wert
                self.canteen_plan_enabled = user_data.get('canteen_plan_enabled', False)
            else:
                # Feld existiert nicht - setze Standard basierend auf Rolle
                if user_data.get('role') in ['admin', 'mitarbeiter']:
                    self.canteen_plan_enabled = True  # Admins und Mitarbeiter standardmäßig aktiviert
                else:
                    self.canteen_plan_enabled = False  # Andere Rollen standardmäßig deaktiviert
                
                # Speichere das Feld automatisch in der Datenbank
                self._save_canteen_plan_enabled(user_data['_id'], self.canteen_plan_enabled)
            
            # Handlungsfeld-Zuweisungen
            self.handlungsfelder = user_data.get('handlungsfelder', [])
        else:
            self.id = None
            self.username = None
            self.role = 'anwender'
            self.is_admin = False
            self.is_mitarbeiter = False
            self.is_teilnehmer = False
            self._active = True
            self.timesheet_enabled = False
            self.canteen_plan_enabled = False
            self.handlungsfelder = []
    
    def get_id(self):
        return str(self.id)
    
    def is_authenticated(self):
        # Prüfe ob der User aktiv ist und nicht zur Löschung vorgesehen
        return self._active and not self.is_scheduled_for_deletion
    
    def is_anonymous(self):
        return False
    
    @property
    def is_active(self):
        return self._active
    
    @property
    def is_scheduled_for_deletion(self):
        """Prüft ob der Account zur Löschung vorgesehen ist"""
        if not self.delete_at:
            return False
        return datetime.now() > self.delete_at
    
    @property
    def days_until_deletion(self):
        """Gibt die Anzahl der Tage bis zur Löschung zurück"""
        if not self.delete_at:
            return None
        delta = self.delete_at - datetime.now()
        return delta.days
    

    
    def _save_timesheet_enabled(self, user_id, enabled):
        """Speichert das timesheet_enabled Feld in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            mongodb.db.users.update_one(
                {'_id': user_id},
                {'$set': {'timesheet_enabled': enabled}}
            )
        except Exception as e:
            # Logge den Fehler, aber falle nicht aus
            import logging
    
    def _save_canteen_plan_enabled(self, user_id, enabled):
        """Speichert das canteen_plan_enabled Feld in der Datenbank"""
        try:
            from app.models.mongodb_database import mongodb
            mongodb.db.users.update_one(
                {'_id': user_id},
                {'$set': {'canteen_plan_enabled': enabled}}
            )
        except Exception as e:
            # Logge den Fehler, aber falle nicht aus
            import logging
            logging.error(f"Fehler beim Speichern von timesheet_enabled für User {user_id}: [Interner Fehler]")