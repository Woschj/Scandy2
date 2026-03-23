"""
Admin User Service

Dieser Service enthält alle Funktionen für die Benutzerverwaltung,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.mongodb_database import mongodb
from app.utils.id_helpers import find_user_by_id
import random
import string

logger = logging.getLogger(__name__)

class AdminUserService:
    """Service für Admin-Benutzerverwaltungs-Funktionen"""
    
    @staticmethod
    def get_all_users() -> List[Dict[str, Any]]:
        """Hole alle Benutzer"""
        try:
            # OPTIMIERT: mongodb.find konvertiert _id bereits zu string (Bolt ⚡)
            return list(mongodb.find('users', {}))
            
        except Exception as e:
            logger.error(f"Fehler beim Laden aller Benutzer: [Interner Fehler]")
            return []

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Hole einen Benutzer anhand der ID"""
        try:
            user = find_user_by_id(user_id)
            if user and '_id' in user:
                user['_id'] = str(user['_id'])
                        
            return user
            
        except Exception as e:
            logger.error(f"Fehler beim Laden des Benutzers {user_id}: [Interner Fehler]")
            return None

    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Erstellt einen neuen Benutzer
        
        Args:
            user_data: Benutzerdaten
            
        Returns:
            (success, message, user_id)
        """
        try:
            # Validierung
            required_fields = ['username', 'role']
            for field in required_fields:
                if field not in user_data or not user_data[field]:
                    return False, f"Feld '{field}' ist erforderlich", None
            
            # Prüfe ob Benutzername bereits existiert (case-insensitive)
            existing_user = mongodb.find_one('users', {'username': {'$regex': f'^{user_data["username"]}$', '$options': 'i'}})
            if existing_user:
                return False, "Benutzername existiert bereits", None
            
            # Department-Zuweisung: Admins dürfen mehrere, Nicht‑Admins genau eine
            allowed_departments = user_data.get('allowed_departments') or []
            default_department = user_data.get('default_department')
            if not allowed_departments and default_department:
                allowed_departments = [default_department]
            if user_data.get('role') != 'admin':
                chosen_department = default_department or (allowed_departments[0] if allowed_departments else None)
                if not chosen_department:
                    return False, "Genau eine Abteilung muss zugewiesen werden", None
                allowed_departments = [chosen_department]
                default_department = chosen_department
            else:
                # Admin: Mindestens eine Abteilung notwendig für Default-Auswahl
                if not allowed_departments:
                    return False, "Mindestens eine Abteilung muss zugewiesen werden", None
                if default_department and default_department not in allowed_departments:
                    allowed_departments.append(default_department)

            # Passwort generieren falls nicht angegeben
            password = user_data.get('password', '')
            if not password:
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                logger.info(f"Automatisches Passwort generiert für {user_data['username']}")
            
            # Passwort hashen
            password_hash = generate_password_hash(password)
            

            
            # Benutzer erstellen
            expiry_date = user_data.get('expiry_date')  # Erwartet datetime oder None
            new_user = {
                'username': user_data['username'],
                'password_hash': password_hash,
                'role': user_data['role'],
                'is_active': user_data.get('is_active', True),
                'timesheet_enabled': user_data.get('timesheet_enabled', False),
                'canteen_plan_enabled': user_data.get('canteen_plan_enabled', False),
                'email': user_data.get('email', ''),
                'firstname': user_data.get('firstname', ''),
                'lastname': user_data.get('lastname', ''),
                # Multi-Department Felder
                'allowed_departments': allowed_departments,
                'default_department': default_department or allowed_departments[0],
                'handlungsfelder': user_data.get('handlungsfelder', []),
                # Ablaufdatum (delete_at) aus Formular übernehmen
                'delete_at': user_data.get('delete_at', expiry_date),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            # Standard: Für Teilnehmer ohne explizites Datum -> 1 Jahr
            if new_user.get('role') == 'teilnehmer' and not new_user.get('delete_at'):
                new_user['delete_at'] = datetime.now() + timedelta(days=365)
            
            # Benutzer in Datenbank speichern
            user_id = mongodb.insert_one('users', new_user)
            
            logger.info(f"Neuer Benutzer erstellt: {user_data['username']} (ID: {user_id})")
            
            # Automatisch Mitarbeiter-Eintrag erstellen
            worker_created = AdminUserService._create_worker_from_user(new_user, user_id)
            if worker_created:
                logger.info(f"Automatischer Mitarbeiter-Eintrag erstellt für: {user_data['username']}")
            
            # Passwort in der Nachricht zurückgeben falls generiert
            if not user_data.get('password'):
                return True, f"Benutzer '{user_data['username']}' erfolgreich erstellt. Generiertes Passwort: {password}", user_id
            else:
                return True, f"Benutzer '{user_data['username']}' erfolgreich erstellt", user_id
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Benutzers: [Interner Fehler]")
            return False, f"Fehler beim Erstellen des Benutzers: [Interner Fehler]", None

    @staticmethod
    def update_user(user_id: str, user_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Aktualisiert einen bestehenden Benutzer
        
        Args:
            user_id: ID des zu aktualisierenden Benutzers
            user_data: Neue Benutzerdaten
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benutzer existiert
            user = find_user_by_id(user_id)
            if not user:
                return False, "Benutzer nicht gefunden"
            
            # Update-Daten vorbereiten
            update_data = {
                'updated_at': datetime.now()
            }
            
            # Aktualisierbare Felder inkl. Multi-Department
            updatable_fields = ['username', 'role', 'is_active', 'timesheet_enabled', 'canteen_plan_enabled',
                              'email', 'firstname', 'lastname', 'handlungsfelder', 'delete_at',
                              'allowed_departments', 'default_department']
            
            for field in updatable_fields:
                if field in user_data:
                    update_data[field] = user_data[field]

            # Mapping: expiry_date aus Formular (Admin-Seite) auf delete_at übernehmen
            if 'expiry_date' in user_data and user_data['expiry_date']:
                update_data['delete_at'] = user_data['expiry_date']
            

            
            # Passwort aktualisieren falls angegeben
            if 'password' in user_data and user_data['password']:
                update_data['password_hash'] = generate_password_hash(user_data['password'])
            
            # Prüfe ob neuer Benutzername bereits existiert (außer bei diesem Benutzer) - case-insensitive
            if 'username' in update_data:
                # Konvertiere user_id zu ObjectId für korrekte Datenbankabfrage
                from bson import ObjectId
                try:
                    object_id = ObjectId(user_id)
                except:
                    # Falls user_id bereits ein ObjectId ist oder ungültig
                    object_id = user_id
                
                existing_user = mongodb.find_one('users', {
                    'username': {'$regex': f'^{update_data["username"]}$', '$options': 'i'},
                    '_id': {'$ne': object_id}
                })
                if existing_user:
                    return False, "Benutzername existiert bereits"
            
            # Department-Zuweisung konsolidieren: Admins dürfen mehrere, Nicht‑Admins genau eine
            new_allowed = update_data.get('allowed_departments', user.get('allowed_departments', []))
            new_default = update_data.get('default_department', user.get('default_department'))
            role_effective = update_data.get('role', user.get('role'))
            if role_effective != 'admin':
                chosen_department = new_default or (new_allowed[0] if new_allowed else None)
                if not chosen_department:
                    return False, "Genau eine Abteilung muss zugewiesen werden"
                new_allowed = [chosen_department]
                new_default = chosen_department
                update_data['allowed_departments'] = new_allowed
                update_data['default_department'] = new_default
            else:
                if not new_allowed and new_default:
                    new_allowed = [new_default]
                    update_data['allowed_departments'] = new_allowed
                if not new_allowed:
                    return False, "Mindestens eine Abteilung muss zugewiesen werden"
                if not new_default:
                    new_default = new_allowed[0]
                    update_data['default_department'] = new_default
                if new_default not in new_allowed:
                    new_allowed.append(new_default)
                    update_data['allowed_departments'] = new_allowed

            # Benutzer aktualisieren
            mongodb.update_one('users', {'_id': user_id}, {'$set': update_data})
            
            # Synchronisiere Mitarbeiter-Eintrag falls vorhanden (inkl. delete_at)
            AdminUserService._sync_worker_from_user(user_id, update_data)
            
            logger.info(f"Benutzer aktualisiert: {user.get('username', 'Unknown')} (ID: {user_id})")
            return True, f"Benutzer erfolgreich aktualisiert"
            
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Benutzers {user_id}: [Interner Fehler]")
            return False, f"Fehler beim Aktualisieren des Benutzers: [Interner Fehler]"

    @staticmethod
    def delete_user(user_id: str, permanent: bool = False) -> Tuple[bool, str]:
        """
        Löscht einen Benutzer. Standard: Soft-Delete (deaktivieren). Optional: permanent löschen.
        
        Args:
            user_id: ID des zu löschenden Benutzers
            permanent: True für permanentes Löschen
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benutzer existiert
            user = find_user_by_id(user_id)
            if not user:
                return False, "Benutzer nicht gefunden"
            
            # Admin-Benutzer dürfen ebenfalls gelöscht werden (über Papierkorb)
            
            if permanent:
                # Permanente Löschung
                from bson import ObjectId
                oid = ObjectId(user_id) if len(str(user_id)) == 24 else user_id
                mongodb.delete_one('users', {'_id': oid})
                # Referenzen bereinigen
                try:
                    # Timesheets löschen
                    mongodb.delete_many('timesheets', {'user_id': user.get('username')})
                    # Tickets/History/Messages: User-Bezüge leeren
                    from datetime import datetime as _dt
                    for coll in ['tickets', 'ticket_history', 'messages', 'ticket_messages']:
                        mongodb.update_many(coll, {'$or': [
                            {'created_by': user.get('username')},
                            {'assigned_to': user.get('username')},
                            {'author': user.get('username')},
                            {'user': user.get('username')}
                        ]}, {'$set': {
                            'created_by': None,
                            'assigned_to': None,
                            'author': None,
                            'user': None,
                            'updated_at': _dt.now()
                        }})
                except Exception:
                    pass
                # Zugehörigen Worker ggf. löschen/deaktivieren
                try:
                    AdminUserService._deactivate_worker_from_user(user_id)
                except Exception:
                    pass
                logger.info(f"Benutzer permanent gelöscht: {user.get('username', 'Unknown')} (ID: {user_id})")
                return True, f"Benutzer '{user.get('username', 'Unknown')}' dauerhaft gelöscht"
            else:
                # Soft-Delete (Papierkorb)
                mongodb.update_one('users', {'_id': user_id}, {
                    '$set': {
                        'is_active': False,
                        'deleted': True,
                        'deleted_at': datetime.now(),
                        'updated_at': datetime.now()
                    }
                })
                # Deaktiviere auch den zugehörigen Mitarbeiter-Eintrag
                AdminUserService._deactivate_worker_from_user(user_id)
                logger.info(f"Benutzer deaktiviert: {user.get('username', 'Unknown')} (ID: {user_id})")
                return True, f"Benutzer '{user.get('username', 'Unknown')}' erfolgreich deaktiviert"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Benutzers {user_id}: [Interner Fehler]")
            return False, f"Fehler beim Löschen des Benutzers: [Interner Fehler]"

    @staticmethod
    def reset_user_password(user_id: str, new_password: str) -> Tuple[bool, str]:
        """
        Setzt das Passwort eines Benutzers zurück
        
        Args:
            user_id: ID des Benutzers
            new_password: Neues Passwort
            
        Returns:
            (success, message)
        """
        try:
            # Prüfe ob Benutzer existiert
            user = find_user_by_id(user_id)
            if not user:
                return False, "Benutzer nicht gefunden"
            
            # Passwort hashen
            password_hash = generate_password_hash(new_password)
            
            # Passwort aktualisieren
            mongodb.update_one('users', {'_id': user_id}, {
                '$set': {
                    'password_hash': password_hash,
                    'updated_at': datetime.now()
                }
            })
            
            logger.info(f"Passwort zurückgesetzt für: {user.get('username', 'Unknown')} (ID: {user_id})")
            return True, f"Passwort für '{user.get('username', 'Unknown')}' erfolgreich zurückgesetzt"
            
        except Exception as e:
            logger.error(f"Fehler beim Zurücksetzen des Passworts für {user_id}: [Interner Fehler]")
            return False, f"Fehler beim Zurücksetzen des Passworts: [Interner Fehler]"

    @staticmethod
    def get_user_statistics() -> Dict[str, Any]:
        """Hole Benutzer-Statistiken"""
        try:
            # Gesamtanzahl Benutzer
            total_users = mongodb.count_documents('users', {})
            
            # Aktive Benutzer
            active_users = mongodb.count_documents('users', {'is_active': True})
            
            # Benutzer nach Rollen
            role_stats = list(mongodb.aggregate('users', [
                {'$group': {'_id': '$role', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]))
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'role_stats': role_stats
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Benutzer-Statistiken: [Interner Fehler]")
            return {
                'total_users': 0,
                'active_users': 0,
                'role_stats': [],
                'scheduled_for_deletion': 0,
                'scheduled_users': []
            }
    
    @staticmethod
    def _create_worker_from_user(user_data: Dict[str, Any], user_id: str) -> bool:
        """
        Erstellt automatisch einen Mitarbeiter-Eintrag aus Benutzerdaten
        
        Args:
            user_data: Benutzerdaten
            user_id: ID des erstellten Benutzers
            
        Returns:
            True wenn erfolgreich erstellt, False sonst
        """
        try:
            # Prüfe ob bereits ein Mitarbeiter mit diesem Benutzernamen oder dieser User-ID existiert (auch gelöschte)
            existing_worker = mongodb.find_one('workers', {
                '$or': [
                    {'username': user_data['username']},
                    {'user_id': user_id}
                ]
            })
            
            if existing_worker:
                logger.info(f"Mitarbeiter-Eintrag existiert bereits für: {user_data['username']}")
                return True
            
            # Neues, sprechendes Barcode-Schema: 1. Buchst. Vorname + 3 Buchst. Nachname + laufende 3-stellige Nummer bei Kollision
            import unicodedata

            def _to_ascii_upper(text: str) -> str:
                if not text:
                    return ''
                mapping = {
                    'ä': 'AE', 'ö': 'OE', 'ü': 'UE', 'ß': 'SS',
                    'Ä': 'AE', 'Ö': 'OE', 'Ü': 'UE'
                }
                replaced = ''.join(mapping.get(ch, ch) for ch in text)
                normalized = unicodedata.normalize('NFKD', replaced)
                ascii_only = normalized.encode('ascii', 'ignore').decode('ascii')
                return ascii_only.upper()

            def _propose_worker_barcode(firstname: str, lastname: str) -> str:
                fn = _to_ascii_upper((firstname or '').strip())
                ln = _to_ascii_upper((lastname or '').strip())
                base = f"{fn[:1]}{ln[:3]}" or 'W'
                base = ''.join(ch for ch in base if ch.isalnum())[:8]
                # Falls Basis schon eindeutig ist
                if not mongodb.find_one('workers', {'barcode': base}):
                    return base
                # Sonst laufend nummerieren
                number = 1
                while number < 1000:
                    cand = f"{base}{number:03d}"
                    if not mongodb.find_one('workers', {'barcode': cand}):
                        return cand
                    number += 1
                # Fallback auf zufälliges, kompaktes Format
                alphabet = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
                return 'W' + ''.join(random.choice(alphabet) for _ in range(6))

            # Eindeutigen Barcode bestimmen
            barcode = _propose_worker_barcode(user_data.get('firstname',''), user_data.get('lastname',''))
            
            # Erstelle Mitarbeiter-Daten (mit Legacy-Kompatibilität)
            worker_data = {
                'barcode': barcode,
                'username': user_data['username'],  # Verknüpfung zum Benutzer
                'user_id': user_id,  # Verknüpfung zur Benutzer-ID
                'firstname': user_data.get('firstname', ''),
                'lastname': user_data.get('lastname', ''),
                'department': user_data.get('default_department') or (user_data.get('allowed_departments', [])[:1] or [''])[0],
                'email': user_data.get('email', ''),
                'role': user_data.get('role', 'anwender'),
                'legacy_barcodes': [f"USER_{user_data['username'].upper()}"] ,
                'created_at': datetime.now(),
                'modified_at': datetime.now(),
                'deleted': False
            }
            
            # Mitarbeiter in Datenbank speichern
            mongodb.insert_one('workers', worker_data)
            
            logger.info(f"Automatischer Mitarbeiter-Eintrag erstellt: {barcode} für Benutzer {user_data['username']}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des automatischen Mitarbeiter-Eintrags: [Interner Fehler]")
            return False
    
    @staticmethod
    def _sync_worker_from_user(user_id: str, user_update_data: Dict[str, Any]) -> bool:
        """
        Synchronisiert einen bestehenden Mitarbeiter-Eintrag mit Benutzerdaten
        
        Args:
            user_id: ID des Benutzers
            user_update_data: Aktualisierte Benutzerdaten
            
        Returns:
            True wenn erfolgreich synchronisiert, False sonst
        """
        try:
            # Finde den zugehörigen Mitarbeiter-Eintrag (auch gelöschte)
            worker = mongodb.find_one('workers', {
                'user_id': user_id
            })
            
            if not worker:
                logger.info(f"Kein Mitarbeiter-Eintrag gefunden für Benutzer-ID: {user_id}")
                return False
            
            # Bereite Update-Daten vor
            worker_update_data = {
                'modified_at': datetime.now()
            }
            
            # Synchronisiere relevante Felder
            if 'firstname' in user_update_data:
                worker_update_data['firstname'] = user_update_data['firstname']
            if 'lastname' in user_update_data:
                worker_update_data['lastname'] = user_update_data['lastname']
            if 'email' in user_update_data:
                worker_update_data['email'] = user_update_data['email']
            if 'default_department' in user_update_data:
                worker_update_data['department'] = user_update_data['default_department']
            if 'delete_at' in user_update_data:
                worker_update_data['delete_at'] = user_update_data['delete_at']
            
            # Aktualisiere Mitarbeiter-Eintrag
            mongodb.update_one('workers', 
                             {'user_id': user_id}, 
                             {'$set': worker_update_data})
            
            logger.info(f"Mitarbeiter-Eintrag synchronisiert für Benutzer-ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Synchronisieren des Mitarbeiter-Eintrags: [Interner Fehler]")
            return False
    
    @staticmethod
    def _deactivate_worker_from_user(user_id: str) -> bool:
        """
        Deaktiviert den zugehörigen Mitarbeiter-Eintrag
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            True wenn erfolgreich deaktiviert, False sonst
        """
        try:
            # Finde den zugehörigen Mitarbeiter-Eintrag (auch gelöschte)
            worker = mongodb.find_one('workers', {
                'user_id': user_id
            })
            
            if not worker:
                logger.info(f"Kein Mitarbeiter-Eintrag gefunden für Benutzer-ID: {user_id}")
                return False
            
            # Deaktiviere den Mitarbeiter-Eintrag (Soft Delete)
            mongodb.update_one('workers', 
                             {'user_id': user_id}, 
                             {'$set': {
                                 'deleted': True,
                                 'deleted_at': datetime.now(),
                                 'modified_at': datetime.now()
                             }})
            
            logger.info(f"Mitarbeiter-Eintrag deaktiviert für Benutzer-ID: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Deaktivieren des Mitarbeiter-Eintrags: [Interner Fehler]")
            return False
    

    
