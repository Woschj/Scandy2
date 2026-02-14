from .blueprint import bp
from .shared import *
@bp.route('/manage_users')
@mitarbeiter_required
def manage_users():
    """Benutzerverwaltung"""
    try:
        users = AdminUserService.get_all_users()

        # Prüfe auf abgelaufene Konten
        today = datetime.now().date()
        expired_users = []

        for user in users:
            # Verwende delete_at (echtes Date-Feld) als maßgebliches Ablaufdatum
            exp = user.get('delete_at') or user.get('expiry_date')
            if exp:
                try:
                    if isinstance(exp, str):
                        # Versuche ISO oder YYYY-MM-DD
                        try:
                            exp_dt = datetime.fromisoformat(exp.replace('Z', '+00:00'))
                        except Exception:
                            exp_dt = datetime.strptime(exp, '%Y-%m-%d')
                    elif isinstance(exp, datetime):
                        exp_dt = exp
                    else:
                        # Unbekannter Typ -> als nicht abgelaufen behandeln
                        user['is_expired'] = False
                        continue
                    # Vergleich auf Datumsebene
                    if exp_dt.date() < today:
                        user['is_expired'] = True
                        expired_users.append(user)
                    else:
                        user['is_expired'] = False
                except Exception:
                    user['is_expired'] = False
            else:
                user['is_expired'] = False

        # Warnung anzeigen wenn abgelaufene Konten existieren
        if expired_users:
            expired_count = len(expired_users)
            if expired_count == 1:
                flash(f'Warnung: 1 Benutzerkonto ist abgelaufen und sollte überprüft werden!', 'warning')
            else:
                flash(f'Warnung: {expired_count} Benutzerkonten sind abgelaufen und sollten überprüft werden!', 'warning')

        # Rollenrechte für Anzeige in der Rollenübersicht
        from app.utils.permissions import get_role_permissions
        role_permissions = get_role_permissions()

        # Abteilungen für Filter/Anzeige der Hauptabteilung
        from app.services.admin_system_settings_service import AdminSystemSettingsService
        departments = AdminSystemSettingsService.get_departments_from_settings()

        return render_template(
            'admin/users.html',
            users=users,
            expired_users=expired_users,
            role_permissions=role_permissions,
            departments=departments
        )
    except Exception as e:
        logger.error(f"Fehler beim Laden der Benutzer: {str(e)}")
        flash('Fehler beim Laden der Benutzer', 'error')
        from app.services.admin_system_settings_service import AdminSystemSettingsService
        departments = AdminSystemSettingsService.get_departments_from_settings()
        return render_template('admin/users.html', users=[], expired_users=[], role_permissions={}, departments=departments)

@bp.route('/add_user', methods=['GET', 'POST'])
@mitarbeiter_required
def add_user():
    """Neuen Benutzer hinzufügen"""
    if request.method == 'POST':
        # Prüfe Berechtigung für Admin-Rolle
        role = request.form.get('role', '').strip()
        if current_user.role != 'admin' and role == 'admin':
            flash('Sie dürfen keine Admin-Benutzer anlegen.', 'error')
            return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'], form_data=request.form)

        # Verwende Services für Validierung und E-Mail
        from app.services.validation_service import ValidationService
        from app.services.email_service import EmailService
        from app.services.utility_service import UtilityService

        form_data = UtilityService.get_form_data_dict(request.form)

        # Validierung mit ValidationService
        is_valid, errors, processed_data = ValidationService.validate_user_form(form_data, is_edit=False)

        # Departments für Formularkontext
        from app.services.admin_system_settings_service import AdminSystemSettingsService
        departments = AdminSystemSettingsService.get_departments_from_settings()
        # Nur eine Abteilung aus Dropdown
        default_department = request.form.get('default_department') or None
        allowed_departments = [default_department] if default_department else []

        if not is_valid:
            for error in errors:
                flash(error, 'error')
            return render_template('admin/user_form.html',
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                                 form_data=request.form,
                                 departments=departments,
                                 user_allowed_departments=allowed_departments,
                                 user_default_department=default_department,
                                 handlungsfelder=handlungsfeld_service.get_handlungsfelder_for_department(default_department),
                                 user_handlungsfelder=request.form.getlist('handlungsfelder'))

        # Automatische Passwort-Generierung wenn keines eingegeben wurde
        if not processed_data['password']:
            password = ValidationService.generate_secure_password()
            processed_data['password'] = password
            processed_data['password_confirm'] = password

        # Handlungsfelder aus Formular holen
        handlungsfelder = request.form.getlist('handlungsfelder')

        # Ablaufdatum verarbeiten
        expiry_date = None
        expiry_date_str = request.form.get('expiry_date', '').strip()
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Ungültiges Ablaufdatum-Format', 'error')
                expiry_date = None

        # Benutzer erstellen mit AdminUserService
        user_data = {
            'username': processed_data['username'],
            'role': processed_data['role'],
            'email': processed_data['email'] if processed_data['email'] else '',
            'firstname': processed_data['firstname'],
            'lastname': processed_data['lastname'],
            'timesheet_enabled': processed_data['timesheet_enabled'],
            'canteen_plan_enabled': request.form.get('canteen_plan_enabled') == 'on',
            'is_active': request.form.get('is_active') == 'on',
            'handlungsfelder': handlungsfelder,
            'expiry_date': expiry_date,
            'allowed_departments': allowed_departments,
            'default_department': default_department
        }

        # Passwort nur hinzufügen falls angegeben
        if processed_data.get('password'):
            user_data['password'] = processed_data['password']

        success, message, user_id = AdminUserService.create_user(user_data)

        if success:
            # E-Mail mit Passwort versenden (falls E-Mail vorhanden)
            if processed_data['email']:
                try:
                    # Passwort aus der Antwort extrahieren (falls generiert)
                    generated_password = None
                    if 'generiert' in message.lower():
                        # Versuche das generierte Passwort aus der Nachricht zu extrahieren
                        import re
                        match = re.search(r'Passwort: ([a-zA-Z0-9]{12})', message)
                        if match:
                            generated_password = match.group(1)

                    email_sent = EmailService.send_new_user_email(
                        processed_data['email'],
                        processed_data['username'],
                        generated_password or processed_data.get('password', ''),
                        processed_data['firstname']
                    )

                    if email_sent:
                        flash(f'{message} Passwort wurde per E-Mail an {processed_data["email"]} gesendet.', 'success')
                    else:
                        flash(f'{message} E-Mail konnte nicht versendet werden.', 'warning')
                except Exception as e:
                    logger.error(f"Fehler beim Versenden der E-Mail: {str(e)}")
                    flash(f'{message} E-Mail konnte nicht versendet werden.', 'warning')
            else:
                flash(f'{message} Das Passwort wurde generiert. Bitte notieren Sie es sicher oder verwenden Sie die E-Mail-Funktion für zukünftige Benutzer.', 'success')

            return redirect(url_for('admin.manage_users'))
        else:
            flash(message, 'error')
            return render_template('admin/user_form.html',
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                                 form_data=request.form,
                                 departments=departments,
                                 user_allowed_departments=allowed_departments,
                                 user_default_department=default_department,
                                 handlungsfelder=handlungsfeld_service.get_handlungsfelder_for_department(default_department),
                                 user_handlungsfelder=handlungsfelder)

    # Hole alle verfügbaren Handlungsfelder für die aktuelle Abteilung
    from app.services.handlungsfeld_service import handlungsfeld_service
    current_department = session.get('department')
    from app.services.admin_system_settings_service import AdminSystemSettingsService
    departments = AdminSystemSettingsService.get_departments_from_settings()
    preferred_default = current_department or (departments[0] if departments else None)
    handlungsfelder = handlungsfeld_service.get_handlungsfelder_for_department(preferred_default)

    # Abteilungen aus Settings
    # departments bereits geladen
    return render_template('admin/user_form.html',
                         roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                         handlungsfelder=handlungsfelder,
                         user_handlungsfelder=[],
                         departments=departments,
                         user_allowed_departments=[],
                         user_default_department=(preferred_default or ''))

@bp.route('/migrate_users_to_workers', methods=['POST'])
@admin_required
def migrate_users_to_workers():
    """Deaktiviert: Die Benutzer→Mitarbeiter Migration wurde entfernt."""
    flash('Die Funktion wurde entfernt. Bitte verwalten Sie Mitarbeiter über die dedizierten Formulare.', 'info')
    return redirect(url_for('admin.manage_users'))

@bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
@mitarbeiter_required
def edit_user(user_id):
    """Benutzer bearbeiten"""
    user = AdminUserService.get_user_by_id(user_id)

    if not user:
        flash('Benutzer nicht gefunden', 'error')
        return redirect(url_for('admin.manage_users'))

    if current_user.role != 'admin' and user.get('role') == 'admin':
        flash('Sie dürfen keine Admin-Benutzer bearbeiten.', 'error')
        return redirect(url_for('admin.manage_users'))

    # GET-Request: Zeige das Formular mit den aktuellen Daten
    if request.method == 'GET':
        # Hole alle verfügbaren Handlungsfelder für die aktuelle Abteilung
        from app.services.handlungsfeld_service import handlungsfeld_service
        # Für die Bearbeitung: Handlungsfelder der Standard-Abteilung des Benutzers zeigen
        current_department = user.get('default_department') or session.get('department')
        handlungsfelder = handlungsfeld_service.get_handlungsfelder_for_department(current_department)

        user_handlungsfelder = user.get('handlungsfelder', [])

        from app.services.admin_system_settings_service import AdminSystemSettingsService
        departments = AdminSystemSettingsService.get_departments_from_settings()
        return render_template('admin/user_form.html',
                             user=user,
                             roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                             handlungsfelder=handlungsfelder,
                             user_handlungsfelder=user_handlungsfelder,
                             departments=departments,
                             user_allowed_departments=user.get('allowed_departments', []),
                             user_default_department=user.get('default_department',''))

    # POST-Request: Verarbeite die Formulardaten
    try:
        # Verwende Services für Validierung
        from app.services.validation_service import ValidationService
        from app.services.utility_service import UtilityService

        form_data = UtilityService.get_form_data_dict(request.form)

        # Validierung mit ValidationService
        is_valid, errors, processed_data = ValidationService.validate_user_form(form_data, is_edit=True)

        if not is_valid:
            for error in errors:
                flash(error, 'error')
            # Hole alle verfügbaren Handlungsfelder für die aktuelle Abteilung
            from app.services.handlungsfeld_service import handlungsfeld_service
            # Nach Validierungsfehlern: auf ausgewählte Standard-Abteilung aus dem Formular reagieren
            form_default_department = request.form.get('default_department') or user.get('default_department') or session.get('department')
            handlungsfelder = handlungsfeld_service.get_handlungsfelder_for_department(form_default_department)

            user_handlungsfelder = user.get('handlungsfelder', [])

            return render_template('admin/user_form.html',
                                 user=user,
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                                 handlungsfelder=handlungsfelder,
                                 user_handlungsfelder=user_handlungsfelder)

        # Handlungsfelder aus Formular holen
        handlungsfelder = request.form.getlist('handlungsfelder')

        # Ablaufdatum verarbeiten
        expiry_date = None
        expiry_date_str = request.form.get('expiry_date', '').strip()
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Ungültiges Ablaufdatum-Format', 'error')
                expiry_date = None

        # Benutzer aktualisieren mit AdminUserService
        user_data = {
            'username': processed_data['username'],
            'role': processed_data['role'],
            'email': processed_data['email'] if processed_data['email'] else '',
            'firstname': processed_data['firstname'],
            'lastname': processed_data['lastname'],
            'timesheet_enabled': processed_data['timesheet_enabled'],
            'canteen_plan_enabled': request.form.get('canteen_plan_enabled') == 'on',
            'is_active': request.form.get('is_active') == 'on',
            'handlungsfelder': handlungsfelder,
            'expiry_date': expiry_date
        }

        # Passwort hinzufügen falls angegeben
        if processed_data['password']:
            user_data['password'] = processed_data['password']

        # Abteilungsrechte (Mehrfachauswahl + Default)
        form_allowed = request.form.getlist('allowed_departments')
        default_department = (request.form.get('default_department') or '').strip() or None
        # Konsistenz herstellen: Default muss in allowed enthalten sein
        if default_department and default_department not in form_allowed:
            form_allowed.append(default_department)
        user_data['allowed_departments'] = [d for d in form_allowed if d]
        user_data['default_department'] = default_department

        success, message = AdminUserService.update_user(user_id, user_data)

        if success:
            flash(message, 'success')
            return redirect(url_for('admin.manage_users'))
        else:
            flash(message, 'error')
            # Hole alle verfügbaren Handlungsfelder für die aktuelle Abteilung
            from app.services.handlungsfeld_service import handlungsfeld_service
            form_default_department = request.form.get('default_department') or user.get('default_department') or session.get('department')
            handlungsfelder = handlungsfeld_service.get_handlungsfelder_for_department(form_default_department)

            user_handlungsfelder = user.get('handlungsfelder', [])

            return render_template('admin/user_form.html',
                                 user=user,
                                 roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                                 handlungsfelder=handlungsfelder,
                                 user_handlungsfelder=user_handlungsfelder)

    except Exception as e:
        logger.error(f"Fehler beim Aktualisieren des Benutzers: {str(e)}")
        flash('Fehler beim Aktualisieren des Benutzers', 'error')
        # Hole alle verfügbaren Handlungsfelder für die aktuelle Abteilung
        from app.services.handlungsfeld_service import handlungsfeld_service
        form_default_department = request.form.get('default_department') or user.get('default_department') or session.get('department')
        if form_default_department:
            handlungsfelder = handlungsfeld_service.get_handlungsfelder_for_department(form_default_department)
        else:
            # Fallback zu globalen Kategorien
            handlungsfelder = get_ticket_categories_from_settings()

        user_handlungsfelder = user.get('handlungsfelder', [])

        return render_template('admin/user_form.html',
                             user=user,
                             roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                             handlungsfelder=handlungsfelder,
                             user_handlungsfelder=user_handlungsfelder)

    # Hole alle verfügbaren Handlungsfelder für die aktuelle Abteilung
    from app.services.handlungsfeld_service import handlungsfeld_service
    current_department = user.get('default_department') or session.get('department')
    handlungsfelder = handlungsfeld_service.get_handlungsfelder_for_department(current_department)

    user_handlungsfelder = user.get('handlungsfelder', [])

    return render_template('admin/user_form.html',
                         user=user,
                         roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'],
                         handlungsfelder=handlungsfelder,
                         user_handlungsfelder=user_handlungsfelder)

@bp.route('/debug/fix-session/<username>')
@admin_required
def fix_session(username):
    """Repariert die Session für einen bestimmten Benutzer"""
    try:
        # Verwende den AdminDebugService
        success, message = AdminDebugService.fix_session_for_user(username)

        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/debug/normalize-user-ids')
@admin_required
def normalize_user_ids():
    """Normalisiert alle User-IDs in der Datenbank zu Strings"""
    try:
        # Verwende den AdminDebugService
        success, message, stats = AdminDebugService.normalize_user_ids()

        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'statistics': stats
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

@bp.route('/debug/user-management')
@login_required
@admin_required
def debug_user_management():
    """Debug-Route für User-Management-Probleme"""
    try:
        from app.models.mongodb_models import MongoDBUser
        from app.models.mongodb_database import mongodb

        # Hole alle User mit detaillierten Informationen
        all_users = mongodb.find('users', {})
        user_list = []

        for user in all_users:
            user_id = user.get('_id')
            user_list.append({
                'id': str(user_id),
                'id_type': type(user_id).__name__,
                'username': user.get('username'),
                'role': user.get('role'),
                'is_active': user.get('is_active', True),
                'email': user.get('email', 'N/A'),
                'firstname': user.get('firstname', 'N/A'),
                'lastname': user.get('lastname', 'N/A'),
                'created_at': str(user.get('created_at', 'N/A')),
                'updated_at': str(user.get('updated_at', 'N/A'))
            })

        # Teste verschiedene Suchmethoden
        test_results = []
        if user_list:
            test_user = user_list[0]
            test_id = test_user['id']

            # Test 1: Direkte String-Suche
            try:
                direct_result = mongodb.find_one('users', {'_id': test_id})
                test_results.append({
                    'method': 'Direkte String-Suche',
                    'success': direct_result is not None,
                    'result': str(direct_result.get('username') if direct_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'Direkte String-Suche',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })

            # Test 2: ObjectId-Suche
            try:
                from bson import ObjectId
                obj_id = ObjectId(test_id)
                obj_result = mongodb.find_one('users', {'_id': obj_id})
                test_results.append({
                    'method': 'ObjectId-Suche',
                    'success': obj_result is not None,
                    'result': str(obj_result.get('username') if obj_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'ObjectId-Suche',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })

            # Test 3: find_user_by_id
            try:
                user_result = find_user_by_id(test_id)
                test_results.append({
                    'method': 'find_user_by_id',
                    'success': user_result is not None,
                    'result': str(user_result.get('username') if user_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'find_user_by_id',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })

            # Test 4: MongoDBUser.get_by_id
            try:
                mongo_user_result = MongoDBUser.get_by_id(test_id)
                test_results.append({
                    'method': 'MongoDBUser.get_by_id',
                    'success': mongo_user_result is not None,
                    'result': str(mongo_user_result.get('username') if mongo_user_result else 'Nicht gefunden')
                })
            except Exception as e:
                test_results.append({
                    'method': 'MongoDBUser.get_by_id',
                    'success': False,
                    'result': f'Fehler: {str(e)}'
                })

        return jsonify({
            'status': 'success',
            'total_users': len(user_list),
            'users': user_list,
            'test_results': test_results,
            'test_id_used': test_user['id'] if user_list else 'Keine User vorhanden'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Ein interner Fehler ist aufgetreten.'
        }), 500

@bp.route('/debug/test-user-id/<user_id>')
@login_required
@admin_required
def debug_test_user_id(user_id):
    """Testet eine spezifische User-ID"""
    try:
        # Verwende den AdminDebugService
        test_results = AdminDebugService.test_user_id(user_id)
        return jsonify(test_results)

    except Exception as e:
        logger.error(f"Fehler beim Testen der User-ID {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ein interner Fehler ist aufgetreten.'
        })

@bp.route('/users/<user_id>/delete-permanent', methods=['DELETE'])
@login_required
@admin_required
def delete_user_permanent_api(user_id):
    """Benutzer endgültig löschen (Papierkorb -> endgültig)"""
    try:
        success, message = AdminUserService.delete_user(user_id, permanent=True)
        if success:
            return jsonify({'success': True, 'message': message})
        return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        logger.error(f"Fehler beim endgültigen Löschen des Benutzers: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Interner Serverfehler'}), 500

@bp.route('/delete_user/<user_id>', methods=['POST'])
@mitarbeiter_required
def delete_user(user_id):
    """Benutzer löschen"""
    try:
        user = AdminUserService.get_user_by_id(user_id)
        if not user:
            flash('Benutzer nicht gefunden', 'error')
            return redirect(url_for('admin.manage_users'))

        # Verhindere das Löschen des eigenen Accounts
        if user['username'] == current_user.username:
            flash('Sie können Ihren eigenen Account nicht löschen', 'error')
            return redirect(url_for('admin.manage_users'))

        # Permanent-Flag aus Formular (optional)
        permanent = False
        try:
            permanent = (request.form.get('permanent') == '1')
        except Exception:
            permanent = False
        # Benutzer löschen mit AdminUserService
        success, message = AdminUserService.delete_user(user_id, permanent=permanent)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        return redirect(url_for('admin.manage_users'))

    except Exception as e:
        logger.error(f"Fehler beim Löschen des Benutzers: {str(e)}")
        flash('Fehler beim Löschen des Benutzers', 'error')
        return redirect(url_for('admin.manage_users'))

@bp.route('/user_form')
@mitarbeiter_required
def user_form():
    """Benutzer-Formular (für neue Benutzer)"""
    return render_template('admin/user_form.html', roles=['admin', 'mitarbeiter', 'anwender', 'teilnehmer'])
