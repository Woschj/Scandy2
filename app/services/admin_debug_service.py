"""
Admin Debug Service

Dieser Service enthält alle Debug- und Wartungsfunktionen,
die aus der großen admin.py Datei ausgelagert wurden.
"""

import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from flask import current_app, session
from app.models.mongodb_database import mongodb
from app.models.mongodb_models import MongoDBUser
from app.utils.id_helpers import find_document_by_id, convert_id_for_query

logger = logging.getLogger(__name__)

class AdminDebugService:
    """Service für Admin-Debug-Funktionen"""
    
    @staticmethod
    def debug_session_info() -> Dict[str, Any]:
        """
        Gibt Debug-Informationen über die aktuelle Session zurück
        
        Returns:
            Dictionary mit Session-Informationen
        """
        try:
            session_info = {
                'session_id': session.get('_id'),
                'user_id': session.get('user_id'),
                'username': session.get('username'),
                'role': session.get('role'),
                'is_authenticated': session.get('is_authenticated', False),
                'session_data': dict(session),
                'session_keys': list(session.keys()),
                'session_size': len(str(session))
            }
            
            logger.info(f"Session-Debug-Info: {session_info}")
            return session_info
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Session-Info: {str(e)}")
            return {'error': 'Ein interner Fehler ist aufgetreten.'}

    @staticmethod
    def debug_backup_info() -> Dict[str, Any]:
        """
        Gibt Debug-Informationen über Backups zurück
        
        Returns:
            Dictionary mit Backup-Informationen
        """
        try:
            from app.utils.backup_manager import backup_manager
            
            backup_info = {
                'backup_dir': str(backup_manager.backup_dir),
                'backup_dir_exists': backup_manager.backup_dir.exists(),
                'backup_dir_writable': os.access(backup_manager.backup_dir, os.W_OK),
                'backup_files': [],
                'total_backups': 0,
                'total_size_mb': 0
            }
            
            if backup_manager.backup_dir.exists():
                backup_files = list(backup_manager.backup_dir.glob('*.zip'))
                backup_info['backup_files'] = [f.name for f in backup_files]
                backup_info['total_backups'] = len(backup_files)
                backup_info['total_size_mb'] = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)
            
            logger.info(f"Backup-Debug-Info: {backup_info}")
            return backup_info
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Backup-Info: {str(e)}")
            return {'error': 'Ein interner Fehler ist aufgetreten.'}

    @staticmethod
    def clear_session() -> Tuple[bool, str]:
        """
        Löscht die aktuelle Session
        
        Returns:
            (success, message)
        """
        try:
            session.clear()
            logger.info("Session erfolgreich gelöscht")
            return True, "Session erfolgreich gelöscht"
            
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Session: {str(e)}")
            return False, f"Fehler beim Löschen der Session: {str(e)}"

    @staticmethod
    def fix_session_for_user(username: str) -> Tuple[bool, str]:
        """
        Repariert die Session für einen bestimmten Benutzer
        
        Args:
            username: Benutzername
            
        Returns:
            (success, message)
        """
        try:
            # Finde den Benutzer
            user = MongoDBUser.get_by_username(username)
            if not user:
                return False, f"Benutzer '{username}' nicht gefunden"
            
            # Erstelle eine neue Session für den Benutzer
            session.clear()
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            session['is_authenticated'] = True
            session['_id'] = str(user['_id'])
            
            logger.info(f"Session für Benutzer '{username}' repariert")
            return True, f"Session für Benutzer '{username}' erfolgreich repariert"
            
        except Exception as e:
            logger.error(f"Fehler beim Reparieren der Session für '{username}': {str(e)}")
            return False, f"Fehler beim Reparieren der Session: {str(e)}"

    @staticmethod
    def normalize_user_ids() -> Tuple[bool, str, Dict[str, Any]]:
        """
        Normalisiert alle User-IDs in der Datenbank
        
        Returns:
            (success, message, statistics)
        """
        try:
            stats = {
                'total_users': 0,
                'normalized_users': 0,
                'errors': 0,
                'details': []
            }
            
            # Hole alle Benutzer
            users = list(mongodb.find('users', {}))
            stats['total_users'] = len(users)
            
            for user in users:
                try:
                    user_id = user.get('_id')
                    if user_id:
                        # Konvertiere zu String falls nötig
                        if not isinstance(user_id, str):
                            user_id_str = str(user_id)
                            
                            # Update alle Referenzen auf diese User-ID
                            collections_to_update = [
                                'lendings', 'tickets', 'ticket_assignments',
                                'ticket_messages', 'ticket_notes'
                            ]
                            
                            for collection in collections_to_update:
                                # Update alle Dokumente die diese User-ID referenzieren
                                mongodb.update_many(
                                    collection,
                                    {'user_id': user_id},
                                    {'$set': {'user_id': user_id_str}}
                                )
                                
                                mongodb.update_many(
                                    collection,
                                    {'assigned_to': user_id},
                                    {'$set': {'assigned_to': user_id_str}}
                                )
                            
                            stats['normalized_users'] += 1
                            stats['details'].append(f"User {user.get('username', 'unknown')}: {user_id} -> {user_id_str}")
                            
                except Exception as e:
                    stats['errors'] += 1
                    stats['details'].append(f"Fehler bei User {user.get('username', 'unknown')}: {str(e)}")
            
            message = f"Normalisierung abgeschlossen: {stats['normalized_users']} Benutzer normalisiert, {stats['errors']} Fehler"
            logger.info(message)
            return True, message, stats
            
        except Exception as e:
            logger.error(f"Fehler bei der User-ID-Normalisierung: {str(e)}")
            return False, f"Fehler bei der Normalisierung: {str(e)}", {}

    @staticmethod
    def normalize_all_ids() -> Tuple[bool, str, Dict[str, Any]]:
        """
        Normalisiert alle IDs in der gesamten Datenbank
        
        Returns:
            (success, message, statistics)
        """
        try:
            stats = {
                'collections_processed': 0,
                'documents_updated': 0,
                'errors': 0,
                'details': []
            }
            
            # Liste aller Collections
            collections = [
                'users', 'tools', 'workers', 'consumables', 'lendings',
                'tickets', 'ticket_messages', 'ticket_notes', 'ticket_assignments',
                'auftrag_details', 'auftrag_material', 'auftrag_arbeit',
                'notifications', 'settings'
            ]
            
            for collection_name in collections:
                try:
                    # Hole alle Dokumente aus der Collection
                    documents = list(mongodb.find(collection_name, {}))
                    
                    for doc in documents:
                        try:
                            doc_id = doc.get('_id')
                            if doc_id and not isinstance(doc_id, str):
                                # Konvertiere ID zu String
                                doc_id_str = str(doc_id)
                                
                                # Update das Dokument mit der neuen ID
                                mongodb.update_one(
                                    collection_name,
                                    {'_id': doc_id},
                                    {'$set': {'_id': doc_id_str}}
                                )
                                
                                stats['documents_updated'] += 1
                                
                        except Exception as e:
                            stats['errors'] += 1
                            stats['details'].append(f"Fehler bei Dokument in {collection_name}: {str(e)}")
                    
                    stats['collections_processed'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    stats['details'].append(f"Fehler bei Collection {collection_name}: {str(e)}")
            
            message = f"ID-Normalisierung abgeschlossen: {stats['collections_processed']} Collections, {stats['documents_updated']} Dokumente aktualisiert, {stats['errors']} Fehler"
            logger.info(message)
            return True, message, stats
            
        except Exception as e:
            logger.error(f"Fehler bei der ID-Normalisierung: {str(e)}")
            return False, f"Fehler bei der Normalisierung: {str(e)}", {}

    @staticmethod
    def debug_user_management() -> Dict[str, Any]:
        """
        Gibt Debug-Informationen über die Benutzerverwaltung zurück
        
        Returns:
            Dictionary mit Benutzer-Management-Informationen
        """
        try:
            # Hole alle Benutzer
            users = list(mongodb.find('users', {}))
            
            # Analysiere Benutzer-Daten
            user_stats = {
                'total_users': len(users),
                'active_users': len([u for u in users if u.get('is_active', True)]),
                'inactive_users': len([u for u in users if not u.get('is_active', True)]),
                'users_by_role': {},
                'users_with_invalid_ids': [],
                'users_without_username': [],
                'users_without_role': []
            }
            
            # Gruppiere nach Rollen
            for user in users:
                role = user.get('role', 'unknown')
                if role not in user_stats['users_by_role']:
                    user_stats['users_by_role'][role] = 0
                user_stats['users_by_role'][role] += 1
                
                # Prüfe auf Probleme
                user_id = user.get('_id')
                if user_id and not isinstance(user_id, str):
                    user_stats['users_with_invalid_ids'].append({
                        'username': user.get('username', 'unknown'),
                        'id': user_id,
                        'id_type': type(user_id).__name__
                    })
                
                if not user.get('username'):
                    user_stats['users_without_username'].append(str(user.get('_id', 'unknown')))
                
                if not user.get('role'):
                    user_stats['users_without_role'].append(user.get('username', 'unknown'))
            
            logger.info(f"User-Management-Debug-Info: {user_stats}")
            return user_stats
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der User-Management-Info: {str(e)}")
            return {'error': 'Ein interner Fehler ist aufgetreten.'}

    @staticmethod
    def test_user_id(user_id: str) -> Dict[str, Any]:
        """
        Testet eine spezifische User-ID
        
        Args:
            user_id: ID des Benutzers
            
        Returns:
            Dictionary mit Test-Ergebnissen
        """
        try:
            test_results = {
                'user_id': user_id,
                'user_found': False,
                'user_data': None,
                'id_type': type(user_id).__name__,
                'references': {},
                'errors': []
            }
            
            # Versuche den Benutzer zu finden
            try:
                user = find_document_by_id('users', user_id)
                if user:
                    test_results['user_found'] = True
                    test_results['user_data'] = {
                        'username': user.get('username'),
                        'role': user.get('role'),
                        'is_active': user.get('is_active', True)
                    }
            except Exception as e:
                test_results['errors'].append(f"Fehler beim Laden des Benutzers: {str(e)}")
            
            # Prüfe Referenzen auf diese User-ID
            collections_to_check = [
                'lendings', 'tickets', 'ticket_assignments',
                'ticket_messages', 'ticket_notes'
            ]
            
            for collection in collections_to_check:
                try:
                    # Zähle Referenzen
                    count = mongodb.count_documents(collection, {'user_id': user_id})
                    if count > 0:
                        test_results['references'][collection] = count
                except Exception as e:
                    test_results['errors'].append(f"Fehler beim Prüfen von {collection}: {str(e)}")
            
            logger.info(f"User-ID-Test für {user_id}: {test_results}")
            return test_results
            
        except Exception as e:
            logger.error(f"Fehler beim Testen der User-ID {user_id}: {str(e)}")
            return {'error': 'Ein interner Fehler ist aufgetreten.', 'user_id': user_id}

    @staticmethod
    def get_available_logos() -> List[Dict[str, Any]]:
        """
        Gibt eine Liste aller verfügbaren Logos zurück
        
        Returns:
            Liste der verfügbaren Logos
        """
        try:
            logos_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'logos')
            
            if not os.path.exists(logos_dir):
                return []
            
            logos = []
            for filename in os.listdir(logos_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                    file_path = os.path.join(logos_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    logos.append({
                        'filename': filename,
                        'size_bytes': file_stat.st_size,
                        'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                        'modified': datetime.fromtimestamp(file_stat.st_mtime),
                        'url': f'/static/uploads/logos/{filename}'
                    })
            
            # Sortiere nach Dateiname
            logos.sort(key=lambda x: x['filename'])
            
            logger.info(f"Verfügbare Logos gefunden: {len(logos)}")
            return logos
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der verfügbaren Logos: {str(e)}")
            return []

    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """
        Gibt eine Übersicht über die Systemgesundheit zurück
        
        Returns:
            Dictionary mit System-Health-Informationen
        """
        try:
            health_info = {
                'database': {},
                'filesystem': {},
                'sessions': {},
                'overall_status': 'healthy'
            }
            
            # Datenbank-Status
            try:
                # Teste Datenbankverbindung
                db_stats = mongodb.command('dbStats')
                health_info['database'] = {
                    'status': 'connected',
                    'collections': db_stats.get('collections', 0),
                    'data_size_mb': round(db_stats.get('dataSize', 0) / (1024 * 1024), 2),
                    'storage_size_mb': round(db_stats.get('storageSize', 0) / (1024 * 1024), 2)
                }
            except Exception as e:
                health_info['database'] = {'status': 'error', 'error': 'Ein interner Fehler ist aufgetreten.'}
                health_info['overall_status'] = 'unhealthy'
            
            # Dateisystem-Status
            try:
                uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
                logos_dir = os.path.join(uploads_dir, 'logos')
                
                health_info['filesystem'] = {
                    'uploads_dir_exists': os.path.exists(uploads_dir),
                    'uploads_dir_writable': os.access(uploads_dir, os.W_OK) if os.path.exists(uploads_dir) else False,
                    'logos_dir_exists': os.path.exists(logos_dir),
                    'logos_dir_writable': os.access(logos_dir, os.W_OK) if os.path.exists(logos_dir) else False
                }
            except Exception as e:
                health_info['filesystem'] = {'status': 'error', 'error': 'Ein interner Fehler ist aufgetreten.'}
                health_info['overall_status'] = 'unhealthy'
            
            # Session-Status
            try:
                health_info['sessions'] = {
                    'session_id': session.get('_id'),
                    'user_authenticated': session.get('is_authenticated', False),
                    'session_size': len(str(session))
                }
            except Exception as e:
                health_info['sessions'] = {'status': 'error', 'error': 'Ein interner Fehler ist aufgetreten.'}
            
            logger.info(f"System-Health-Check: {health_info['overall_status']}")
            return health_info
            
        except Exception as e:
            logger.error(f"Fehler beim System-Health-Check: {str(e)}")
            return {'overall_status': 'error', 'error': 'Ein interner Fehler ist aufgetreten.'}

    @staticmethod
    def fix_email_configuration() -> Tuple[bool, str]:
        """
        Repariert die E-Mail-Konfiguration automatisch
        
        Returns:
            (success, message)
        """
        try:
            from app.services.admin_email_service import AdminEmailService
            from app.utils.email_utils import _decrypt_password
            
            # Prüfe ob alte E-Mail-Einstellungen vorhanden sind
            old_settings = mongodb.find_one('settings', {'key': 'email_smtp_server'})
            
            if old_settings:
                logger.info("Alte E-Mail-Einstellungen gefunden, migriere zu neuem System")
                
                # Sammle alle alten E-Mail-Einstellungen
                old_email_settings = {}
                old_keys = [
                    'email_smtp_server', 'email_smtp_port', 'email_username', 
                    'email_password', 'email_use_tls', 'email_sender_email'
                ]
                
                for key in old_keys:
                    setting = mongodb.find_one('settings', {'key': key})
                    if setting:
                        old_email_settings[key] = setting.get('value', '')
                
                # Konvertiere zu neuem Format
                if old_email_settings.get('email_smtp_server'):
                    new_config = {
                        'mail_server': old_email_settings.get('email_smtp_server', ''),
                        'mail_port': int(old_email_settings.get('email_smtp_port', 587)),
                        'mail_use_tls': old_email_settings.get('email_use_tls', 'true').lower() == 'true',
                        'mail_username': old_email_settings.get('email_username', ''),
                        'mail_password': old_email_settings.get('email_password', ''),
                        'test_email': old_email_settings.get('email_sender_email', ''),
                        'use_auth': True
                    }
                    
                    # Speichere neue Konfiguration
                    AdminEmailService.save_email_config(new_config)
                    
                    # Lösche alte Einstellungen
                    for key in old_keys:
                        mongodb.delete_one('settings', {'key': key})
                    
                    logger.info("E-Mail-Konfiguration erfolgreich migriert")
                    return True, "E-Mail-Konfiguration erfolgreich migriert"
            
            # Prüfe ob Admin-Benutzer ohne E-Mail-Adresse existieren
            admin_users = list(mongodb.find('users', {'role': 'admin'}))
            fixed_users = 0
            
            for user in admin_users:
                if not user.get('email'):
                    # Setze Standard-E-Mail-Adresse
                    mongodb.update_one(
                        'users',
                        {'_id': user['_id']},
                        {'$set': {'email': 'admin@example.com'}}
                    )
                    fixed_users += 1
            
            if fixed_users > 0:
                logger.info(f"{fixed_users} Admin-Benutzer ohne E-Mail-Adresse korrigiert")
                return True, f"E-Mail-Konfiguration repariert: {fixed_users} Admin-Benutzer korrigiert"
            
            return True, "E-Mail-Konfiguration ist bereits korrekt"
            
        except Exception as e:
            logger.error(f"Fehler bei der E-Mail-Konfigurations-Reparatur: {str(e)}")
            return False, f"Fehler bei der E-Mail-Reparatur: {str(e)}"

    @staticmethod
    def fix_dashboard_comprehensive():
        """
        Umfassende Dashboard-Reparatur die alle bekannten Probleme behebt
        Wird automatisch beim App-Start und nach Backup-Import ausgeführt
        """
        try:
            from datetime import datetime
            from app.services.admin_backup_service import AdminBackupService
            
            fixes_applied = {
                'missing_fields': 0,
                'datetime_conversions': 0,
                'objectid_conversions': 0,
                'data_consistency': 0,
                'total': 0
            }
            
            # 1. Standard Backup-Feld-Reparatur
            try:
                fixes_applied['missing_fields'] = AdminDebugService.fix_missing_created_at_fields()
            except Exception as e:
                logger.warning(f"Backup-Feld-Reparatur fehlgeschlagen: {str(e)}")
            
            # 2. Umfassende Datentyp-Reparatur
            try:
                dashboard_fixes = AdminBackupService.fix_dashboard_after_backup()
                fixes_applied['datetime_conversions'] = dashboard_fixes.get('datetime_conversions', 0)
                fixes_applied['objectid_conversions'] = dashboard_fixes.get('objectid_conversions', 0)
                fixes_applied['data_consistency'] = dashboard_fixes.get('data_consistency', 0)
            except Exception as e:
                logger.warning(f"Datentyp-Reparatur fehlgeschlagen: {str(e)}")
            
            # 3. Zusätzliche Konsistenzprüfungen
            try:
                # Stelle sicher, dass alle Tools ein gültiges created_at Feld haben
                all_tools = mongodb.find('tools', {})
                for tool in all_tools:
                    created_at = tool.get('created_at')
                    if created_at is None:
                        fallback_date = tool.get('updated_at') or datetime.now()
                        if isinstance(fallback_date, str):
                            try:
                                fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                try:
                                    fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    fallback_date = datetime.now()
                        
                        mongodb.update_one('tools', 
                                         {'_id': tool['_id']}, 
                                         {'$set': {'created_at': fallback_date}})
                        fixes_applied['data_consistency'] += 1
                
                # Stelle sicher, dass alle Workers ein gültiges created_at Feld haben
                all_workers = mongodb.find('workers', {})
                for worker in all_workers:
                    created_at = worker.get('created_at')
                    if created_at is None:
                        fallback_date = worker.get('updated_at') or datetime.now()
                        if isinstance(fallback_date, str):
                            try:
                                fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                            except ValueError:
                                try:
                                    fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    fallback_date = datetime.now()
                        
                        mongodb.update_one('workers', 
                                         {'_id': worker['_id']}, 
                                         {'$set': {'created_at': fallback_date}})
                        fixes_applied['data_consistency'] += 1
                        
            except Exception as e:
                logger.warning(f"Datenkonsistenz-Reparatur fehlgeschlagen: {str(e)}")
            
            # Gesamtzahl berechnen
            fixes_applied['total'] = sum([
                fixes_applied['missing_fields'],
                fixes_applied['datetime_conversions'],
                fixes_applied['objectid_conversions'],
                fixes_applied['data_consistency']
            ])
            
            if fixes_applied['total'] > 0:
                logger.info(f"Umfassende Dashboard-Reparatur abgeschlossen: {fixes_applied}")
            
            return fixes_applied
            
        except Exception as e:
            logger.error(f"Fehler bei umfassender Dashboard-Reparatur: {str(e)}")
            return {'total': 0, 'error': 'Ein interner Fehler ist aufgetreten.'}

    @staticmethod
    def fix_missing_created_at_fields() -> int:
        """
        Ergänzt fehlende created_at Felder in der Datenbank
        Wird automatisch beim App-Start und nach Backup-Import ausgeführt
        
        Returns:
            Anzahl der korrigierten Felder
        """
        try:
            from datetime import datetime
            
            fixed_count = 0
            
            # Tools ohne created_at Feld
            tools_without_created = mongodb.find('tools', {'created_at': {'$exists': False}})
            for tool in tools_without_created:
                fallback_date = tool.get('updated_at') or datetime.now()
                if isinstance(fallback_date, str):
                    try:
                        fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            fallback_date = datetime.now()
                
                mongodb.update_one('tools', 
                                 {'_id': tool['_id']}, 
                                 {'$set': {'created_at': fallback_date}})
                fixed_count += 1
            
            # Workers ohne created_at Feld
            workers_without_created = mongodb.find('workers', {'created_at': {'$exists': False}})
            for worker in workers_without_created:
                fallback_date = worker.get('updated_at') or datetime.now()
                if isinstance(fallback_date, str):
                    try:
                        fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            fallback_date = datetime.now()
                
                mongodb.update_one('workers', 
                                 {'_id': worker['_id']}, 
                                 {'$set': {'created_at': fallback_date}})
                fixed_count += 1
            
            # Consumables ohne created_at Feld
            consumables_without_created = mongodb.find('consumables', {'created_at': {'$exists': False}})
            for consumable in consumables_without_created:
                fallback_date = consumable.get('updated_at') or datetime.now()
                if isinstance(fallback_date, str):
                    try:
                        fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S.%f')
                    except ValueError:
                        try:
                            fallback_date = datetime.strptime(fallback_date, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            fallback_date = datetime.now()
                
                mongodb.update_one('consumables', 
                                 {'_id': consumable['_id']}, 
                                 {'$set': {'created_at': fallback_date}})
                fixed_count += 1
            
            if fixed_count > 0:
                logger.info(f"{fixed_count} fehlende created_at Felder ergänzt")
            
            return fixed_count
            
        except Exception as e:
            logger.error(f"Fehler beim Ergänzen fehlender Felder: {str(e)}")
            return 0 