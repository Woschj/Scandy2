from .blueprint import bp
from .shared import *
@bp.route('/debug/session')
@admin_required
def debug_session():
    """Debug-Route für Session-Informationen"""
    try:
        # Verwende den AdminDebugService
        session_info = AdminDebugService.debug_session_info()
        return jsonify(session_info)

    except Exception as e:
        return jsonify({
            'error': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/debug/clear-session')
@admin_required
def clear_session():
    """Löscht die aktuelle Session"""
    try:
        # Verwende den AdminDebugService
        success, message = AdminDebugService.clear_session()

        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/debug/normalize-all-ids')
@admin_required
def normalize_all_ids():
    """Normalisiert alle IDs in allen Collections zu Strings"""
    try:
        from app.models.mongodb_database import mongodb
        from bson import ObjectId

        collections_to_normalize = [
            'users', 'tickets', 'tools', 'workers', 'consumables',
            'lendings', 'ticket_messages', 'ticket_notes', 'auftrag_details',
            'auftrag_material', 'auftrag_arbeit', 'timesheets'
        ]

        total_updated = 0
        collection_results = {}

        for collection in collections_to_normalize:
            try:
                all_docs = mongodb.find(collection, {})
                updated_count = 0

                for doc in all_docs:
                    doc_id = doc.get('_id')

                    # Falls die ID ein ObjectId ist, konvertiere sie zu String
                    if isinstance(doc_id, ObjectId):
                        string_id = str(doc_id)

                        # Erstelle ein neues Dokument mit String-ID
                        new_doc = doc.copy()
                        new_doc['_id'] = string_id

                        # Lösche das alte Dokument und füge das neue ein
                        mongodb.delete_one(collection, {'_id': doc_id})
                        mongodb.insert_one(collection, new_doc)

                        updated_count += 1

                collection_results[collection] = updated_count
                total_updated += updated_count
                print(f"Collection {collection}: {updated_count} IDs normalisiert")

            except Exception as e:
                collection_results[collection] = f"Fehler: {str(e)}"
                print(f"Fehler bei Collection {collection}: {str(e)}")

        return jsonify({
            'status': 'success',
            'message': f'{total_updated} IDs in allen Collections normalisiert',
            'total_updated': total_updated,
            'collection_results': collection_results
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/email_debug')
@admin_required
def email_debug():
    """E-Mail-Debug wurde entfernt."""
    from flask import abort
    return abort(404)

@bp.route('/admin/email/test-simple', methods=['POST'])
@login_required
@admin_required
def test_email_simple():
    """Einfacher E-Mail-Test"""
    try:
        config_data = AdminEmailService.get_email_config()
        if not config_data:
            return jsonify({'success': False, 'message': 'Keine E-Mail-Konfiguration gefunden'})

        # Verwende die gleiche Logik wie im Debug-Tool
        from app.utils.email_utils import _decrypt_password

        # Erstelle Test-Konfiguration mit entschlüsseltem Passwort
        test_config = config_data.copy()

        # Entschlüssele Passwort falls verschlüsselt
        if test_config.get('mail_password') and test_config['mail_password'].startswith('gAAAAA'):
            try:
                decrypted_password = _decrypt_password(test_config['mail_password'])
                if decrypted_password:
                    test_config['mail_password'] = decrypted_password
                else:
                    logger.warning("Passwort konnte nicht entschlüsselt werden - verwende verschlüsseltes Passwort")
                    # Verwende das verschlüsselte Passwort direkt - test_email_config kann damit umgehen
            except Exception as e:
                logger.warning(f"Fehler beim Entschlüsseln des Passworts: {str(e)} - verwende verschlüsseltes Passwort")
                # Verwende das verschlüsselte Passwort direkt - test_email_config kann damit umgehen

        # Verwende die test_email_config aus email_utils direkt
        from app.utils.email_utils import test_email_config

        success, message = test_email_config(test_config)

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Test-Fehler: {str(e)}'
        })

@bp.route('/debug/fix-lending-inconsistencies', methods=['POST'])
@admin_required
def fix_lending_inconsistencies():
    """Behebt Inkonsistenzen in den Ausleihdaten"""
    try:
        from app.services.lending_service import LendingService

        success, message, statistics = LendingService.fix_lending_inconsistencies()

        if success:
            return jsonify({
                'success': True,
                'message': message,
                'statistics': statistics
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500

    except Exception as e:
        logger.error(f"Fehler beim Beheben der Inkonsistenzen: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Beheben der Inkonsistenzen: {str(e)}'
        }), 500

@bp.route('/debug/validate-lending-consistency', methods=['GET'])
@admin_required
def validate_lending_consistency():
    """Validiert die Konsistenz der Ausleihdaten"""
    try:
        from app.services.lending_service import LendingService

        is_consistent, message, issues = LendingService.validate_lending_consistency()

        return jsonify({
            'success': True,
            'is_consistent': is_consistent,
            'message': message,
            'issues': issues
        })

    except Exception as e:
        logger.error(f"Fehler bei der Konsistenzprüfung: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Konsistenzprüfung: {str(e)}'
        }), 500

@bp.route('/debug/fix-missing-created-at', methods=['POST'])
@admin_required
def fix_missing_created_at():
    """Korrigiert fehlende created_at Felder in der Datenbank"""
    try:
        from app.services.admin_backup_service import AdminBackupService

        fixed_count = AdminBackupService._fix_missing_created_at_fields()

        return jsonify({
            'success': True,
            'message': f'{fixed_count} fehlende created_at Felder wurden ergänzt',
            'fixed_count': fixed_count
        })

    except Exception as e:
        logger.error(f"Fehler beim Korrigieren fehlender created_at Felder: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Korrigieren: {str(e)}'
        }), 500

@bp.route('/debug/test-dashboard-fix', methods=['GET'])
@admin_required
def test_dashboard_fix():
    """Testet und behebt Dashboard-Probleme nach Backup-Restore"""
    try:
        # Teste ob das Dashboard geladen werden kann
        from app.services.admin_dashboard_service import AdminDashboardService

        result = {
            'success': False,
            'message': '',
            'tests': {},
            'errors': []
        }

        # Teste alle Dashboard-Services
        services_to_test = [
            ('recent_activity', AdminDashboardService.get_recent_activity),
            ('material_usage', AdminDashboardService.get_material_usage),
            ('warnings', AdminDashboardService.get_warnings),
            ('consumables_forecast', AdminDashboardService.get_consumables_forecast),
            ('consumable_trend', AdminDashboardService.get_consumable_trend)
        ]

        working_services = 0
        for service_name, service_func in services_to_test:
            try:
                data = service_func()
                if data is not None:
                    if isinstance(data, list):
                        result['tests'][service_name] = len(data)
                    elif isinstance(data, dict):
                        result['tests'][service_name] = len(data.get('usage_data', [])) if 'usage_data' in data else len(data)
                    else:
                        result['tests'][service_name] = 'OK'
                    working_services += 1
                else:
                    result['tests'][service_name] = 'Keine Daten'
            except Exception as e:
                error_msg = f"{str(e)}"
                result['tests'][service_name] = f"Fehler: {error_msg}"
                result['errors'].append(f"{service_name}: {error_msg}")

        # Bewerte das Ergebnis
        if working_services == len(services_to_test) and not result['errors']:
            result['success'] = True
            result['message'] = 'Dashboard funktioniert einwandfrei!'
        elif working_services > 0:
            result['success'] = True
            result['message'] = f'Dashboard teilweise funktional. {working_services}/{len(services_to_test)} Services funktionieren.'
        else:
            result['message'] = 'Dashboard hat Probleme. Keine Services funktionieren.'

        return jsonify(result)

    except Exception as e:
        logger.error(f"Fehler beim Testen des Dashboard-Fixes: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Testen: {str(e)}',
            'errors': [f"Unerwarteter Fehler: {str(e)}"],
            'tests': {}
        }), 500

@bp.route('/debug/fix-dashboard-complete', methods=['GET', 'POST'])
@admin_required
def fix_dashboard_complete():
    """Behebt alle Dashboard-Probleme umfassend"""
    try:
        from app.services.admin_backup_service import AdminBackupService
        from app.services.admin_dashboard_service import AdminDashboardService

        result = {
            'success': False,
            'message': '',
            'fixes': {
                'backup_fields': 0,
                'data_consistency': 0,
                'missing_relations': 0,
                'date_fixes': 0
            },
            'dashboard_tests': {},
            'errors': []
        }

        # 1. Backup-Felder korrigieren
        try:
            result['fixes']['backup_fields'] = AdminBackupService._fix_missing_created_at_fields()
        except Exception as e:
            result['errors'].append(f"Backup-Felder: {str(e)}")

        # 2. Datenkonsistenz prüfen und korrigieren
        collections_to_check = ['tools', 'workers', 'consumables', 'lendings', 'consumable_usages']

        for collection in collections_to_check:
            try:
                # Prüfe auf ungültige Datumsfelder
                date_fields = ['created_at', 'updated_at', 'lent_at', 'returned_at', 'used_at']
                for field in date_fields:
                    docs_with_invalid_dates = mongodb.find(collection, {
                        field: {'$exists': True, '$type': 'string'}
                    })

                    for doc in docs_with_invalid_dates:
                        date_value = doc.get(field)
                        if isinstance(date_value, str):
                            try:
                                # Versuche verschiedene Datumsformate
                                if '.' in date_value:
                                    parsed_date = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S.%f')
                                elif 'T' in date_value:
                                    parsed_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                                else:
                                    parsed_date = datetime.strptime(date_value, '%Y-%m-%d %H:%M:%S')

                                mongodb.update_one(collection,
                                                 {'_id': doc['_id']},
                                                 {'$set': {field: parsed_date}})
                                result['fixes']['date_fixes'] += 1
                            except ValueError:
                                # Ungültiges Datum - setze auf aktuelles Datum
                                mongodb.update_one(collection,
                                                 {'_id': doc['_id']},
                                                 {'$set': {field: datetime.now()}})
                                result['fixes']['date_fixes'] += 1
            except Exception as e:
                result['errors'].append(f"{collection} Datumsfelder: {str(e)}")

        # 3. Teste Dashboard-Services
        dashboard_services = [
            ('recent_activity', AdminDashboardService.get_recent_activity),
            ('material_usage', AdminDashboardService.get_material_usage),
            ('warnings', AdminDashboardService.get_warnings),
            ('consumables_forecast', AdminDashboardService.get_consumables_forecast),
            ('consumable_trend', AdminDashboardService.get_consumable_trend)
        ]

        working_services = 0
        for service_name, service_func in dashboard_services:
            try:
                data = service_func()
                if data is not None:
                    if isinstance(data, list):
                        result['dashboard_tests'][service_name] = len(data)
                    elif isinstance(data, dict):
                        result['dashboard_tests'][service_name] = len(data.get('usage_data', [])) if 'usage_data' in data else len(data)
                    else:
                        result['dashboard_tests'][service_name] = 'OK'
                    working_services += 1
                else:
                    result['dashboard_tests'][service_name] = 'Keine Daten'
            except Exception as e:
                error_msg = f"{str(e)}"
                result['dashboard_tests'][service_name] = f"Fehler: {error_msg}"
                result['errors'].append(f"{service_name}: {error_msg}")

        # 4. Bewerte das Ergebnis
        total_fixes = sum(result['fixes'].values())

        if working_services == len(dashboard_services) and not result['errors']:
            result['success'] = True
            result['message'] = f'Dashboard-Korrektur abgeschlossen: {total_fixes} Probleme behoben'
        elif working_services > 0:
            result['success'] = True
            result['message'] = f'Dashboard teilweise repariert: {total_fixes} Probleme behoben, {working_services}/{len(dashboard_services)} Services funktionieren'
        else:
            result['message'] = f'Dashboard konnte nicht repariert werden: {total_fixes} Probleme behoben, aber Services funktionieren nicht'

        return jsonify(result)

    except Exception as e:
        logger.error(f"Fehler bei der umfassenden Dashboard-Korrektur: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler bei der Dashboard-Korrektur: {str(e)}',
            'errors': [f"Unerwarteter Fehler: {str(e)}"],
            'fixes': {'backup_fields': 0, 'data_consistency': 0, 'missing_relations': 0, 'date_fixes': 0},
            'dashboard_tests': {}
        }), 500

@bp.route('/debug/dashboard-status', methods=['GET'])
@admin_required
def dashboard_status():
    """Zeigt den aktuellen Dashboard-Status und behebt Probleme automatisch"""
    try:
        from app.services.admin_dashboard_service import AdminDashboardService

        status = {
            'dashboard_working': False,
            'errors': [],
            'fixes_applied': 0,
            'data_counts': {}
        }

        # Teste Dashboard-Services
        try:
            recent_activity = AdminDashboardService.get_recent_activity()
            status['data_counts']['recent_activity'] = len(recent_activity)
        except Exception as e:
            status['errors'].append(f"Recent Activity: {str(e)}")

        try:
            material_usage = AdminDashboardService.get_material_usage()
            status['data_counts']['material_usage'] = len(material_usage.get('usage_data', []))
        except Exception as e:
            status['errors'].append(f"Material Usage: {str(e)}")

        try:
            warnings = AdminDashboardService.get_warnings()
            status['data_counts']['warnings'] = sum(len(w) for w in warnings.values())
        except Exception as e:
            status['errors'].append(f"Warnings: {str(e)}")

        try:
            consumables_forecast = AdminDashboardService.get_consumables_forecast()
            status['data_counts']['consumables_forecast'] = len(consumables_forecast)
        except Exception as e:
            status['errors'].append(f"Consumables Forecast: {str(e)}")

        try:
            consumable_trend = AdminDashboardService.get_consumable_trend()
            status['data_counts']['consumable_trend'] = len(consumable_trend.get('labels', []))
        except Exception as e:
            status['errors'].append(f"Consumable Trend: {str(e)}")

        # Prüfe Datenbank-Zugriff
        try:
            total_tools = mongodb.count_documents('tools', {'deleted': {'$ne': True}})
            total_consumables = mongodb.count_documents('consumables', {'deleted': {'$ne': True}})
            total_workers = mongodb.count_documents('workers', {'deleted': {'$ne': True}})
            total_lendings = mongodb.count_documents('lendings', {})

            status['data_counts'].update({
                'tools': total_tools,
                'consumables': total_consumables,
                'workers': total_workers,
                'lendings': total_lendings
            })
        except Exception as e:
            status['errors'].append(f"Database Access: {str(e)}")

        # Wenn es Fehler gibt, versuche automatische Korrektur
        if status['errors']:
            try:
                from app.services.admin_backup_service import AdminBackupService

                # Führe Backup-Feld-Korrektur aus
                fixed_count = AdminBackupService._fix_missing_created_at_fields()
                status['fixes_applied'] = fixed_count

                # Teste erneut nach der Korrektur
                retry_success = True
                for error in status['errors'][:]:  # Kopie für Iteration
                    if 'Recent Activity' in error:
                        try:
                            recent_activity = AdminDashboardService.get_recent_activity()
                            status['data_counts']['recent_activity'] = len(recent_activity)
                            status['errors'].remove(error)
                        except:
                            retry_success = False

                if retry_success and not status['errors']:
                    status['dashboard_working'] = True
                    status['message'] = f'Dashboard repariert! {fixed_count} Felder korrigiert'
                else:
                    status['message'] = f'Teilweise repariert. {fixed_count} Felder korrigiert, aber {len(status["errors"])} Fehler verbleiben'
            except Exception as fix_error:
                status['errors'].append(f"Auto-Fix failed: {str(fix_error)}")
                status['message'] = 'Automatische Reparatur fehlgeschlagen'
        else:
            status['dashboard_working'] = True
            status['message'] = 'Dashboard funktioniert einwandfrei'

        return jsonify(status)

    except Exception as e:
        logger.error(f"Fehler beim Prüfen des Dashboard-Status: {str(e)}")
        return jsonify({
            'dashboard_working': False,
            'errors': [f"Status check failed: {str(e)}"],
            'fixes_applied': 0,
            'data_counts': {},
            'message': 'Fehler beim Prüfen des Dashboard-Status'
        }), 500

@bp.route('/debug/dashboard-details', methods=['GET'])
@admin_required
def dashboard_details():
    """Zeigt detaillierte Informationen über Dashboard-Probleme"""
    try:
        from app.services.admin_dashboard_service import AdminDashboardService

        details = {
            'database_counts': {},
            'service_tests': {},
            'template_variables': {},
            'errors': []
        }

        # Datenbank-Zählungen
        try:
            details['database_counts'] = {
                'tools': mongodb.count_documents('tools', {'deleted': {'$ne': True}}),
                'consumables': mongodb.count_documents('consumables', {'deleted': {'$ne': True}}),
                'workers': mongodb.count_documents('workers', {'deleted': {'$ne': True}}),
                'lendings': mongodb.count_documents('lendings', {}),
                'consumable_usages': mongodb.count_documents('consumable_usages', {}),
                'tickets': mongodb.count_documents('tickets', {})
            }
        except Exception as e:
            details['errors'].append(f"Database counts: {str(e)}")

        # Service-Tests
        try:
            recent_activity = AdminDashboardService.get_recent_activity()
            details['service_tests']['recent_activity'] = {
                'count': len(recent_activity),
                'sample': recent_activity[:2] if recent_activity else []
            }
        except Exception as e:
            details['service_tests']['recent_activity'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        try:
            material_usage = AdminDashboardService.get_material_usage()
            details['service_tests']['material_usage'] = {
                'count': len(material_usage.get('usage_data', [])),
                'period_days': material_usage.get('period_days', 0)
            }
        except Exception as e:
            details['service_tests']['material_usage'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        try:
            warnings = AdminDashboardService.get_warnings()
            details['service_tests']['warnings'] = {
                'defect_tools': len(warnings.get('defect_tools', [])),
                'overdue_lendings': len(warnings.get('overdue_lendings', [])),
                'low_stock_consumables': len(warnings.get('low_stock_consumables', []))
            }
        except Exception as e:
            details['service_tests']['warnings'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        try:
            consumables_forecast = AdminDashboardService.get_consumables_forecast()
            details['service_tests']['consumables_forecast'] = {
                'count': len(consumables_forecast)
            }
        except Exception as e:
            details['service_tests']['consumables_forecast'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        try:
            consumable_trend = AdminDashboardService.get_consumable_trend()
            details['service_tests']['consumable_trend'] = {
                'labels_count': len(consumable_trend.get('labels', [])),
                'datasets_count': len(consumable_trend.get('datasets', []))
            }
        except Exception as e:
            details['service_tests']['consumable_trend'] = {'error': 'Ein interner Fehler ist aufgetreten.'}

        # Template-Variablen simulieren
        try:
            # Simuliere Dashboard-Route Logik
            total_tools = mongodb.count_documents('tools', {'deleted': {'$ne': True}})
            total_consumables = mongodb.count_documents('consumables', {'deleted': {'$ne': True}})
            total_workers = mongodb.count_documents('workers', {'deleted': {'$ne': True}})
            total_tickets = mongodb.count_documents('tickets', {})

            # Tool-Statistiken
            tool_stats = {
                'total': total_tools,
                'available': mongodb.count_documents('tools', {'status': 'verfügbar', 'deleted': {'$ne': True}}),
                'lent': mongodb.count_documents('tools', {'status': 'ausgeliehen', 'deleted': {'$ne': True}}),
                'defect': mongodb.count_documents('tools', {'status': 'defekt', 'deleted': {'$ne': True}})
            }

            # Consumable-Statistiken
            consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
            sufficient = 0
            warning = 0
            critical = 0

            for consumable in consumables:
                if consumable['quantity'] >= consumable.get('warning_threshold', 10):
                    sufficient += 1
                elif consumable['quantity'] >= consumable.get('critical_threshold', 5):
                    warning += 1
                else:
                    critical += 1

            consumable_stats = {
                'total': total_consumables,
                'sufficient': sufficient,
                'warning': warning,
                'critical': critical
            }

            # Worker-Statistiken
            workers = list(mongodb.find('workers', {'deleted': {'$ne': True}}))
            worker_stats = {
                'total': total_workers,
                'by_department': []
            }

            # Gruppiere nach Abteilung
            dept_counts = {}
            for worker in workers:
                dept = worker.get('department', 'Ohne Abteilung')
                dept_counts[dept] = dept_counts.get(dept, 0) + 1

            for dept, count in dept_counts.items():
                worker_stats['by_department'].append({
                    'name': dept,
                    'count': count
                })

            details['template_variables'] = {
                'total_tools': total_tools,
                'total_consumables': total_consumables,
                'total_workers': total_workers,
                'total_tickets': total_tickets,
                'tool_stats': tool_stats,
                'consumable_stats': consumable_stats,
                'worker_stats': worker_stats
            }

        except Exception as e:
            details['errors'].append(f"Template variables: {str(e)}")

        return jsonify({
            'success': True,
            'details': details,
            'message': 'Dashboard-Details erfolgreich geladen'
        })

    except Exception as e:
        logger.error(f"Fehler beim Laden der Dashboard-Details: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Fehler beim Laden der Dashboard-Details: {str(e)}'
        }), 500

@bp.route('/debug/dashboard-page')
@admin_required
def dashboard_debug_page():
    """Dashboard Debug-Seite"""
    return render_template('admin/dashboard_debug.html')

@bp.route('/debug/email-debug-page')
@admin_required
def email_debug_page():
    """E-Mail Debug-Seite"""
    return render_template('admin/email_debug.html')

@bp.route('/debug/test-email-config', methods=['GET'])
@admin_required
def test_email_config_debug():
    """Testet die E-Mail-Konfiguration mit detaillierten Informationen"""
    try:
        from app.utils.email_utils import get_email_config, test_email_config, _decrypt_password

        result = {
            'success': False,
            'message': '',
            'config_loaded': False,
            'config_details': {},
            'test_result': {},
            'errors': []
        }

        # 1. Lade E-Mail-Konfiguration
        try:
            config = get_email_config()
            if config:
                result['config_loaded'] = True
                result['config_details'] = {
                    'mail_server': config.get('mail_server'),
                    'mail_port': config.get('mail_port'),
                    'mail_use_tls': config.get('mail_use_tls'),
                    'mail_username': config.get('mail_username'),
                    'mail_password_length': len(config.get('mail_password', '')),
                    'mail_password_encrypted': config.get('mail_password', '').startswith('gAAAAA'),
                    'test_email': config.get('test_email'),
                    'use_auth': config.get('use_auth')
                }
            else:
                result['errors'].append("E-Mail-Konfiguration konnte nicht geladen werden")
        except Exception as e:
            result['errors'].append(f"Fehler beim Laden der Konfiguration: {str(e)}")

        # 2. Teste E-Mail-Konfiguration
        if config:
            try:
                # Erstelle Test-Konfiguration mit entschlüsseltem Passwort
                test_config = config.copy()

                # Entschlüssele Passwort falls verschlüsselt
                if test_config.get('mail_password') and test_config['mail_password'].startswith('gAAAAA'):
                    try:
                        decrypted_password = _decrypt_password(test_config['mail_password'])
                        if decrypted_password:
                            test_config['mail_password'] = decrypted_password
                            result['config_details']['password_decrypted'] = True
                        else:
                            result['errors'].append("Passwort konnte nicht entschlüsselt werden")
                    except Exception as e:
                        result['errors'].append(f"Fehler beim Entschlüsseln des Passworts: {str(e)}")

                # Teste E-Mail-Konfiguration
                success, message = test_email_config(test_config)

                result['test_result'] = {
                    'success': success,
                    'message': message,
                    'config_used': {
                        'mail_server': test_config.get('mail_server'),
                        'mail_port': test_config.get('mail_port'),
                        'mail_use_tls': test_config.get('mail_use_tls'),
                        'mail_username': test_config.get('mail_username'),
                        'mail_password_length': len(test_config.get('mail_password', '')),
                        'test_email': test_config.get('test_email')
                    }
                }

                if success:
                    result['success'] = True
                    result['message'] = "E-Mail-Konfiguration funktioniert korrekt!"
                else:
                    result['message'] = f"E-Mail-Test fehlgeschlagen: {message}"

            except Exception as e:
                result['errors'].append(f"Fehler beim E-Mail-Test: {str(e)}")
                result['message'] = f"Fehler beim E-Mail-Test: {str(e)}"
        else:
            result['message'] = "Keine E-Mail-Konfiguration verfügbar"

        return jsonify(result)

    except Exception as e:
        logger.error(f"Fehler beim E-Mail-Konfigurations-Test: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Kritischer Fehler: {str(e)}',
            'config_loaded': False,
            'config_details': {},
            'test_result': {},
            'errors': [f"Unerwarteter Fehler: {str(e)}"]
        }), 500

@bp.route('/debug/fix-email-config', methods=['GET'])
@admin_required
def fix_email_config():
    """Korrigiert E-Mail-Konfigurationsprobleme nach Backup-Restore"""
    try:
        result = {
            'success': False,
            'message': '',
            'fixes_applied': 0,
            'old_settings': {},
            'new_config': {},
            'errors': []
        }

        # 1. Prüfe alte E-Mail-Einstellungen in settings Collection
        try:
            old_settings = {}
            settings_docs = mongodb.find('settings', {'key': {'$regex': '^email_'}})

            for doc in settings_docs:
                old_settings[doc['key']] = doc.get('value', '')

            result['old_settings'] = old_settings

            # 2. Prüfe neue E-Mail-Konfiguration in email_config Collection
            try:
                new_config_doc = mongodb.find_one('email_config', {'_id': 'email_config'})
                if new_config_doc:
                    result['new_config'] = {k: v for k, v in new_config_doc.items() if k != '_id'}
            except Exception as e:
                result['errors'].append(f"Neue E-Mail-Konfiguration prüfen: {str(e)}")

            # 3. Migriere alte Einstellungen zu neuem Format
            if old_settings and not result['new_config']:
                try:
                    # Konvertiere alte Einstellungen zu neuem Format
                    new_config = {
                        'mail_server': old_settings.get('email_smtp_server', 'smtp.gmail.com'),
                        'mail_port': int(old_settings.get('email_smtp_port', 587)),
                        'mail_use_tls': old_settings.get('email_use_tls', 'true').lower() == 'true',
                        'mail_username': old_settings.get('email_username', ''),
                        'mail_password': old_settings.get('email_password', ''),
                        'test_email': old_settings.get('email_test_email', ''),
                        'use_auth': old_settings.get('email_use_auth', 'true').lower() == 'true'
                    }

                    # Speichere neue Konfiguration
                    mongodb.update_one('email_config',
                                     {'_id': 'email_config'},
                                     {'$set': new_config},
                                     upsert=True)

                    result['new_config'] = new_config
                    result['fixes_applied'] += 1
                    result['message'] += "E-Mail-Konfiguration von altem Format migriert. "

                except Exception as e:
                    result['errors'].append(f"Migration fehlgeschlagen: {str(e)}")

            # 4. Prüfe ob Admin-Benutzer E-Mail-Adresse hat
            try:
                admin_users = list(mongodb.find('users', {'role': 'admin'}))
                admin_without_email = 0

                for admin in admin_users:
                    if not admin.get('email'):
                        admin_without_email += 1
                        # Setze Standard-E-Mail für Admin ohne E-Mail
                        mongodb.update_one('users',
                                         {'_id': admin['_id']},
                                         {'$set': {'email': 'admin@scandy.local'}})

                if admin_without_email > 0:
                    result['fixes_applied'] += admin_without_email
                    result['message'] += f"{admin_without_email} Admin-Benutzer ohne E-Mail-Adresse korrigiert. "

            except Exception as e:
                result['errors'].append(f"Admin-E-Mail prüfen: {str(e)}")

            # 5. Bewerte das Ergebnis
            if result['fixes_applied'] > 0 and not result['errors']:
                result['success'] = True
                result['message'] += "E-Mail-Konfiguration erfolgreich repariert!"
            elif result['fixes_applied'] > 0:
                result['success'] = True
                result['message'] += "E-Mail-Konfiguration teilweise repariert."
            else:
                result['message'] = "Keine E-Mail-Konfigurationsprobleme gefunden."

        except Exception as e:
            result['errors'].append(f"Allgemeiner Fehler: {str(e)}")
            result['message'] = "Fehler beim Prüfen der E-Mail-Konfiguration."

        return jsonify(result)

    except Exception as e:
        logger.error(f"Fehler bei E-Mail-Konfigurations-Fix: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Kritischer Fehler: {str(e)}',
            'fixes_applied': 0,
            'errors': [f"Unerwarteter Fehler: {str(e)}"],
            'old_settings': {},
            'new_config': {}
        }), 500

@bp.route('/debug/analyze-lendings', methods=['GET'])
@admin_required
def analyze_lendings():
    """Analysiert die Ausleihen in der Datenbank"""
    try:
        from app.models.mongodb_database import mongodb

        # Hole alle Ausleihen
        all_lendings = list(mongodb.find('lendings', {}))
        current_lendings = list(mongodb.find('lendings', {'returned_at': {'$exists': False}}))

        # Analysiere Duplikate
        lending_counts = {}
        for lending in current_lendings:
            tool_barcode = lending.get('tool_barcode')
            if tool_barcode:
                lending_counts[tool_barcode] = lending_counts.get(tool_barcode, 0) + 1

        duplicate_lendings = {barcode: count for barcode, count in lending_counts.items() if count > 1}

        # Erstelle detaillierte Analyse
        analysis = {
            'total_lendings': len(all_lendings),
            'current_lendings': len(current_lendings),
            'unique_tools_lent': len(lending_counts),
            'duplicate_lendings': duplicate_lendings,
            'lending_details': []
        }

        # Detaillierte Ausleihen
        for lending in current_lendings:
            tool = mongodb.find_one('tools', {'barcode': lending.get('tool_barcode')})
            worker = mongodb.find_one('workers', {'barcode': lending.get('worker_barcode')})

            analysis['lending_details'].append({
                'id': str(lending.get('_id')),
                'tool_barcode': lending.get('tool_barcode'),
                'tool_name': tool.get('name', 'Unbekannt') if tool else 'Unbekannt',
                'worker_barcode': lending.get('worker_barcode'),
                'worker_name': worker.get('name', 'Unbekannt') if worker else 'Unbekannt',
                'lent_at': lending.get('lent_at'),
                'returned_at': lending.get('returned_at')
            })

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        logger.error(f"Fehler bei Ausleihen-Analyse: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/debug/fix-dashboard-simple', methods=['GET'])
@admin_required
def fix_dashboard_simple():
    """Einfache Dashboard-Korrektur mit detaillierten Informationen"""
    try:
        import traceback
        from app.services.admin_backup_service import AdminBackupService
        from app.services.admin_dashboard_service import AdminDashboardService

        result = {
            'success': False,
            'message': '',
            'fixes_applied': 0,
            'errors': [],
            'tests': {},
            'database_info': {}
        }

        # 1. Sammle Datenbank-Informationen
        try:
            result['database_info'] = {
                'tools_count': mongodb.count_documents('tools', {'deleted': {'$ne': True}}),
                'consumables_count': mongodb.count_documents('consumables', {'deleted': {'$ne': True}}),
                'workers_count': mongodb.count_documents('workers', {'deleted': {'$ne': True}}),
                'lendings_count': mongodb.count_documents('lendings', {}),
                'tickets_count': mongodb.count_documents('tickets', {})
            }
        except Exception as e:
            result['errors'].append(f"Datenbank-Zugriff: {str(e)}")

        # 2. Führe Backup-Feld-Korrektur aus
        try:
            fixed_count = AdminBackupService._fix_missing_created_at_fields()
            result['fixes_applied'] = fixed_count
            result['message'] += f"{fixed_count} fehlende Felder korrigiert. "
        except Exception as e:
            result['errors'].append(f"Backup-Feld-Korrektur: {str(e)}")

        # 3. Teste Dashboard-Services
        dashboard_services = [
            ('recent_activity', AdminDashboardService.get_recent_activity),
            ('material_usage', AdminDashboardService.get_material_usage),
            ('warnings', AdminDashboardService.get_warnings),
            ('consumables_forecast', AdminDashboardService.get_consumables_forecast),
            ('consumable_trend', AdminDashboardService.get_consumable_trend)
        ]

        working_services = 0
        for service_name, service_func in dashboard_services:
            try:
                data = service_func()
                if data is not None:
                    if isinstance(data, list):
                        result['tests'][service_name] = len(data)
                    elif isinstance(data, dict):
                        result['tests'][service_name] = len(data.get('usage_data', [])) if 'usage_data' in data else len(data)
                    else:
                        result['tests'][service_name] = 'OK'
                    working_services += 1
                else:
                    result['tests'][service_name] = 'Keine Daten'
            except Exception as e:
                error_msg = f"{str(e)}"
                result['tests'][service_name] = f"Fehler: {error_msg}"
                result['errors'].append(f"{service_name}: {error_msg}")

        # 4. Bewerte das Ergebnis
        if working_services == len(dashboard_services) and not result['errors']:
            result['success'] = True
            result['message'] += "Dashboard funktioniert einwandfrei!"
        elif working_services > 0:
            result['success'] = True
            result['message'] += f"Dashboard teilweise repariert. {working_services}/{len(dashboard_services)} Services funktionieren."
        else:
            result['message'] += "Dashboard konnte nicht repariert werden."

        return jsonify(result)

    except Exception as e:
        logger.error(f"Fehler bei der einfachen Dashboard-Korrektur: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Kritischer Fehler: {str(e)}',
            'fixes_applied': 0,
            'errors': [f"Unerwarteter Fehler: {str(e)}"],
            'tests': {},
            'database_info': {}
        }), 500
