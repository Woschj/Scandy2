from .blueprint import bp
from .shared import *
@bp.route('/manual-lending', methods=['GET', 'POST'])
@mitarbeiter_required
def manual_lending():
    """Manuelle Ausleihe/Rückgabe"""
    if request.method == 'POST':
        logger.info("POST-Anfrage für manuelle Ausleihe empfangen")

        try:
            # JSON-Daten für manuelle Ausleihe
            data = request.get_json()

            if not data:
                return jsonify({'success': False, 'message': 'Keine Daten empfangen'}), 400

            # Validiere erforderliche Felder
            required_fields = ['item_barcode', 'worker_barcode', 'action', 'item_type']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'message': f'Feld {field} ist erforderlich'}), 400

            # Hole Daten aus JSON
            item_barcode = data.get('item_barcode', '').strip()
            worker_barcode = data.get('worker_barcode', '').strip()
            action = data.get('action', '').strip()
            item_type = data.get('item_type', '').strip()
            quantity = data.get('quantity', 1)

            if not item_barcode or not worker_barcode or not action or not item_type:
                return jsonify({'success': False, 'message': 'Alle Felder sind erforderlich'}), 400

            if action == 'lend' and not worker_barcode:
                return jsonify({
                    'success': False,
                    'message': 'Mitarbeiter muss ausgewählt sein'
                }), 400

            try:
                # Prüfe ob der Mitarbeiter existiert
                if worker_barcode:
                    worker = mongodb.find_one('workers', {'barcode': worker_barcode, 'deleted': {'$ne': True}})
                    if not worker:
                        return jsonify({
                            'success': False,
                            'message': 'Mitarbeiter nicht gefunden'
                        }), 404

                # Verwende den zentralen LendingService für konsistente Verarbeitung
                from app.services.lending_service import LendingService

                # Erstelle Request-Daten für den Service
                service_data = {
                    'item_barcode': item_barcode,
                    'worker_barcode': worker_barcode,
                    'action': action,
                    'item_type': item_type,
                    'quantity': quantity
                }

                # Verarbeite über den Service
                success, message, result_data = LendingService.process_lending_request(service_data)

                if success:
                    return jsonify({
                        'success': True,
                        'message': message,
                        'data': result_data
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': message
                    }), 400
            except Exception as e:
                logger.error(f"Fehler bei der Ausleihe: [Interner Fehler]")
                return jsonify({
                    'success': False,
                    'message': f'Fehler: [Interner Fehler]'
                }), 500

        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der Anfrage: [Interner Fehler]")
            return jsonify({
                'success': False,
                'message': 'Fehler beim Verarbeiten der Anfrage'
            }), 500

    # GET request - zeige das Formular
    try:
        # Hole alle verfügbaren Werkzeuge
        tools_pipeline = [
            {'$match': {'deleted': {'$ne': True}}},
            {
                '$lookup': {
                    'from': 'lendings',
                    'localField': 'barcode',
                    'foreignField': 'tool_barcode',
                    'as': 'active_lendings'
                }
            },
            {
                '$addFields': {
                    'current_status': {
                        '$cond': [
                            {'$gt': [{'$size': {'$filter': {'input': '$active_lendings', 'cond': {'$eq': ['$$this.returned_at', None]}}}}, 0]},
                            'ausgeliehen',
                            '$status'
                        ]
                    }
                }
            },
            {'$sort': {'name': 1}}
        ]

        tools = list(mongodb.aggregate('tools', tools_pipeline))

        # Hole alle Mitarbeiter
        workers = mongodb.find('workers', {'deleted': {'$ne': True}}, sort=[('firstname', 1)])

        # Verbrauchsmaterialien laden
        consumables = mongodb.find('consumables', {'deleted': {'$ne': True}}, sort=[('name', 1)])

        # Hole aktuelle Ausleihen
        current_lendings = []

        # Aktuelle Werkzeug-Ausleihen (Optimiert mit Aggregation zur Vermeidung von N+1 Problemen)
        active_tool_lendings_pipeline = [
            {'$match': {'returned_at': None}},
            {
                '$lookup': {
                    'from': 'tools',
                    'localField': 'tool_barcode',
                    'foreignField': 'barcode',
                    'as': 'tool_info'
                }
            },
            {'$unwind': '$tool_info'},
            {
                '$lookup': {
                    'from': 'workers',
                    'localField': 'worker_barcode',
                    'foreignField': 'barcode',
                    'as': 'worker_info'
                }
            },
            {'$unwind': '$worker_info'},
            {
                '$project': {
                    'item_name': '$tool_info.name',
                    'item_barcode': '$tool_info.barcode',
                    'worker_name': {'$concat': ['$worker_info.firstname', ' ', '$worker_info.lastname']},
                    'worker_barcode': '$worker_info.barcode',
                    'action_date': '$lent_at',
                    'category': {'$literal': 'Werkzeug'},
                    'amount': {'$literal': None}
                }
            }
        ]

        current_lendings.extend(list(mongodb.aggregate('lendings', active_tool_lendings_pipeline)))

        # Aktuelle Verbrauchsmaterial-Ausgaben der letzten 30 Tage (Optimiert mit Aggregation)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_consumable_usages_pipeline = [
            {
                '$match': {
                    'used_at': {'$gte': thirty_days_ago},
                    'quantity': {'$lt': 0}  # Nur Ausgaben (negative Werte)
                }
            },
            {
                '$lookup': {
                    'from': 'consumables',
                    'localField': 'consumable_barcode',
                    'foreignField': 'barcode',
                    'as': 'consumable_info'
                }
            },
            {'$unwind': '$consumable_info'},
            {
                '$lookup': {
                    'from': 'workers',
                    'localField': 'worker_barcode',
                    'foreignField': 'barcode',
                    'as': 'worker_info'
                }
            },
            {'$unwind': '$worker_info'},
            {
                '$project': {
                    'item_name': '$consumable_info.name',
                    'item_barcode': '$consumable_info.barcode',
                    'worker_name': {'$concat': ['$worker_info.firstname', ' ', '$worker_info.lastname']},
                    'worker_barcode': '$worker_info.barcode',
                    'action_date': '$used_at',
                    'category': {'$literal': 'Verbrauchsmaterial'},
                    'amount': '$quantity'
                }
            }
        ]

        current_lendings.extend(list(mongodb.aggregate('consumable_usages', recent_consumable_usages_pipeline)))

        # Sortiere nach Datum (neueste zuerst)
        def safe_date_key(lending):
            action_date = lending.get('action_date')
            if isinstance(action_date, str):
                try:
                    return datetime.strptime(action_date, '%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    return datetime.min
            elif isinstance(action_date, datetime):
                return action_date
            else:
                return datetime.min

        current_lendings.sort(key=safe_date_key, reverse=True)

        return render_template('admin/manual_lending.html',
                              tools=tools,
                              workers=workers,
                              consumables=consumables,
                              current_lendings=current_lendings)
    except Exception as e:
        print(f"Fehler beim Laden der Daten: [Interner Fehler]")
        flash('Fehler beim Laden der Daten', 'error')
        return render_template('admin/manual_lending.html',
                              tools=[],
                              workers=[],
                              consumables=[],
                              current_lendings=[])

@bp.route('/upload_logo', methods=['POST'])
@admin_required
def upload_logo():
    """Logo hochladen"""
    flash('Logo-Upload-Funktion noch nicht implementiert', 'warning')
    return redirect(url_for('admin.system'))

@bp.route('/system', methods=['GET', 'POST'])
@admin_required
def system():
    """System-Einstellungen"""
    try:
        if request.method == 'POST':
            # Begriffe & Icons verarbeiten
            app_labels = {
                'tools': {
                    'name': request.form.get('label_tools_name', 'Werkzeuge'),
                    'icon': request.form.get('label_tools_icon', 'fas fa-tools')
                },
                'consumables': {
                    'name': request.form.get('label_consumables_name', 'Verbrauchsmaterial'),
                    'icon': request.form.get('label_consumables_icon', 'fas fa-box')
                },
                'tickets': {
                    'name': request.form.get('label_tickets_name', 'Tickets'),
                    'icon': request.form.get('label_tickets_icon', 'fas fa-ticket-alt')
                }
            }

            success, message = AdminSystemService.save_app_labels(app_labels)

            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')

            # Software-Presets verarbeiten
            software_presets_text = request.form.get('software_presets', '')
            if software_presets_text:
                software_presets = [line.strip() for line in software_presets_text.split('\n') if line.strip()]
                mongodb.update_one('settings',
                                 {'key': 'software_presets'},
                                 {'$set': {'value': software_presets}},
                                 upsert=True)

            # Nutzergruppen verarbeiten
            user_groups_text = request.form.get('user_groups', '')
            if user_groups_text:
                user_groups = [line.strip() for line in user_groups_text.split('\n') if line.strip()]
                mongodb.update_one('settings',
                                 {'key': 'user_groups'},
                                 {'$set': {'value': user_groups}},
                                 upsert=True)

            return redirect(url_for('admin.system'))

        # Hole alle verfügbaren Logos
        logos = AdminSystemService.get_available_logos()

        # Hole aktuelle Einstellungen und App-Labels
        settings, app_labels = AdminSystemService.get_system_data()

        # Hole Software-Presets und Nutzergruppen
        software_presets_setting = mongodb.find_one('settings', {'key': 'software_presets'})
        software_presets = '\n'.join(software_presets_setting.get('value', [])) if software_presets_setting else ''

        user_groups_setting = mongodb.find_one('settings', {'key': 'user_groups'})
        user_groups = '\n'.join(user_groups_setting.get('value', [])) if user_groups_setting else ''

        return render_template('admin/server-settings.html',
                             logos=logos,
                             settings=settings,
                             app_labels=app_labels,
                             software_presets=software_presets,
                             user_groups=user_groups)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Systemeinstellungen: [Interner Fehler]")
        flash('Fehler beim Laden der Systemeinstellungen', 'error')
        return redirect(url_for('admin.index'))

@bp.route('/feature_settings', methods=['GET', 'POST'])
@admin_required
def feature_settings():
    """Feature-Einstellungen verwalten (department-scoped)"""
    try:
        # Aktuelle Abteilung aus der Session
        current_department = session.get('department')
        if not current_department:
            flash('Keine Abteilung ausgewählt', 'error')
            return redirect(url_for('admin.dashboard'))

        if request.method == 'POST':
            # Nur Features aktualisieren, die auf der Seite tatsächlich vorhanden sind
            # (kein implizites Deaktivieren nicht angezeigter Features)
            form_to_feature_keys = {
                # 'feature_job_board': 'job_board',  # global immer aktiv, nicht konfigurierbar
                'feature_weekly_reports': 'weekly_reports',
                'feature_software_management': 'software_management',
                'feature_ticket_system': 'ticket_system',
                'feature_canteen_plan': 'canteen_plan',
            }

            updates = {}
            for form_key, feature_key in form_to_feature_keys.items():
                # Checkboxen senden nur etwas, wenn sie angehakt sind →
                # abgehakte müssen explizit auf False gesetzt werden
                updates[feature_key] = (request.form.get(form_key) == 'on')

            # Einstellungen für aktuelle Abteilung speichern
            from app.models.feature_system import feature_system
            for feature_name, enabled in updates.items():
                feature_system.set_feature_setting(feature_name, enabled, current_department)

            flash(f'Feature-Einstellungen für {current_department} erfolgreich gespeichert', 'success')
            return redirect(url_for('admin.feature_settings'))

        # Aktuelle Feature-Einstellungen für aktuelle Abteilung laden
        from app.models.feature_system import feature_system
        feature_settings = feature_system.get_feature_settings(current_department)

        # Alle verfügbaren Abteilungen für Abteilungswechsel
        from app.utils.context_processors import inject_departments
        departments_ctx = inject_departments()
        available_departments = departments_ctx['departments']['allowed']

        return render_template('admin/feature_settings.html',
                             feature_settings=feature_settings,
                             current_department=current_department,
                             available_departments=available_departments)

    except Exception as e:
        logger.error(f"Fehler beim Laden der Feature-Einstellungen: [Interner Fehler]")
        flash('Fehler beim Laden der Feature-Einstellungen', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/change_department', methods=['POST'])
@admin_required
def change_department():
    """Wechselt die aktuelle Abteilung in der Session"""
    try:
        data = request.get_json()
        new_department = data.get('department')

        if new_department:
            session['department'] = new_department
            g.current_department = new_department
            return jsonify({'success': True, 'department': new_department})
        else:
            return jsonify({'success': False, 'error': 'Keine Abteilung angegeben'}), 400

    except Exception as e:
        logger.error(f"Fehler beim Wechseln der Abteilung: [Interner Fehler]")
        return jsonify({'success': False, 'error': 'Ein interner Fehler ist aufgetreten.'}), 500

@bp.route('/role_permissions', methods=['GET', 'POST'])
@admin_required
def role_permissions():
    """Rollen- und Berechtigungs-Matrix verwalten."""
    try:
        if request.method == 'POST':
            # Erwartet JSON im Formularfeld 'permissions' oder einzelne Checkboxen
            if request.is_json:
                payload = request.get_json()
                permissions = payload.get('permissions', {})
            else:
                # Aus HTML-Form-Checkboxen zusammensetzen: name="perm[role][area][action]"
                permissions = get_role_permissions()
                # Flaches Formular in Matrix zurückschreiben
                for key, value in request.form.items():
                    if not key.startswith('perm[') or value != 'on':
                        continue
                    try:
                        # perm[role][area][action]
                        parts = key.split('[')
                        role = parts[1][:-1]
                        area = parts[2][:-1]
                        action = parts[3][:-1]
                        permissions.setdefault(role, {}).setdefault(area, [])
                        if action not in permissions[role][area]:
                            permissions[role][area].append(action)
                    except Exception:
                        continue

            # Guardrail: Admin immer alles und unzulässige Aktionen filtern
            permissions['admin'] = DEFAULT_ROLE_PERMISSIONS['admin']
            permissions = normalize_permissions(permissions)

            if set_role_permissions(permissions):
                flash('Berechtigungen erfolgreich gespeichert', 'success')
            else:
                flash('Fehler beim Speichern der Berechtigungen', 'error')
            return redirect(url_for('admin.role_permissions'))

        # GET: aktuelle Matrix anzeigen
        permissions = get_role_permissions()
        # Bereiche: aus erlaubten Bereichen, ergänzt um evtl. vorhandene Einträge
        areas = sorted(set(ALLOWED_ACTIONS.keys()) | {a for r in permissions.values() for a in r.keys()})
        # Aktionen: Superset aller erlaubten Aktionen
        actions = get_all_actions()
        roles = sorted(permissions.keys())
        return render_template('admin/role_permissions.html',
                               permissions=permissions,
                               roles=roles,
                               areas=areas,
                               actions=actions,
                               allowed_actions=ALLOWED_ACTIONS)
    except Exception as e:
        logger.error(f"Fehler beim Laden der Rollenrechte: [Interner Fehler]")
        flash('Fehler beim Laden der Rollenrechte', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/departments')
@mitarbeiter_required
def get_departments():
    """Gibt alle Abteilungen zurück"""
    try:
        # Verwende den AdminSystemSettingsService
        departments = AdminSystemSettingsService.get_departments_from_settings()
        return jsonify({
            'success': True,
            'departments': [{'name': dept} for dept in departments]
        })
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Abteilungen: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Abteilungen'
        })

@bp.route('/departments/manage')
@mitarbeiter_required
def departments_manage_page():
    """Seite zur Verwaltung der Abteilungen (Bereiche)."""
    try:
        return render_template('admin/departments.html')
    except Exception as e:
        logger.error(f"Fehler beim Rendern der Abteilungsseite: [Interner Fehler]")
        flash('Fehler beim Laden der Abteilungsverwaltung', 'error')
        return redirect(url_for('admin.system'))

@bp.route('/departments/add', methods=['POST'])
@mitarbeiter_required
def add_department():
    """Fügt eine neue Abteilung hinzu"""
    try:
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('department', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Verwende den AdminSystemSettingsService
        success, message = AdminSystemSettingsService.add_department(name)

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
        logger.error(f"Fehler beim Hinzufügen der Abteilung: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/departments/rename', methods=['POST'])
@mitarbeiter_required
def rename_department():
    """Benennt eine Abteilung um (inkl. Migration)."""
    try:
        old_name = request.form.get('old_name', '').strip()
        new_name = request.form.get('new_name', '').strip()
        success, message = AdminSystemSettingsService.rename_department(old_name, new_name)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error(f"Fehler beim Umbenennen der Abteilung: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Ein Fehler ist aufgetreten.'})

@bp.route('/categories')
@mitarbeiter_required
def get_categories_admin():
    """Gibt alle Kategorien der aktuellen/angefragten Abteilung zurück (dedizierte Collection)."""
    try:
        req_dept = request.args.get('dept')
        from flask import g
        current_dept = req_dept or getattr(g, 'current_department', None)
        if not current_dept:
            return jsonify({'success': True, 'categories': []})

        # Verwende den neuen CategoryService
        from app.services.category_service import category_service
        categories = category_service.get_categories_for_department(current_dept)
        return jsonify({'success': True, 'categories': [{'name': n} for n in categories]})
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Kategorien: [Interner Fehler]")
        return jsonify({'success': False, 'message': 'Fehler beim Laden der Kategorien'})

@bp.route('/categories/add', methods=['POST'])
@mitarbeiter_required
def add_category():
    """Fügt eine neue Kategorie hinzu"""
    try:
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('category', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Verwende den neuen CategoryService
        from flask import g
        req_dept = request.form.get('dept')
        current_dept = req_dept or getattr(g, 'current_department', None)
        if not current_dept:
            return jsonify({'success': False, 'message': 'Keine Abteilung ausgewählt.'})

        from app.services.category_service import category_service
        if category_service.create_category(name, current_dept):
            return jsonify({
                'success': True,
                'message': 'Kategorie erfolgreich hinzugefügt.'
            })
        else:
            return jsonify({'success': False, 'message': 'Diese Kategorie existiert bereits in dieser Abteilung.'})

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen der Kategorie: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/locations')
@mitarbeiter_required
def get_locations():
    """Gibt alle Standorte zurück"""
    try:
        req_dept = request.args.get('dept')
        from flask import g
        current_dept = req_dept or getattr(g, 'current_department', None)
        if not current_dept:
            return jsonify({'success': True, 'locations': []})

        # Verwende den neuen LocationService
        from app.services.location_service import location_service
        locations = location_service.get_locations_for_department(current_dept)
        return jsonify({'success': True, 'locations': [{'name': n} for n in locations]})
    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Standorte: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Standorte'
        })

@bp.route('/locations/add', methods=['POST'])
@mitarbeiter_required
def add_location():
    """Fügt einen neuen Standort hinzu"""
    try:
        # Unterstütze beide Feldnamen für Kompatibilität
        name = request.form.get('name', '').strip() or request.form.get('location', '').strip()
        if not name:
            return jsonify({
                'success': False,
                'message': 'Bitte geben Sie einen Namen ein.'
            })

        # Verwende den neuen LocationService
        from flask import g
        req_dept = request.form.get('dept')
        current_dept = req_dept or getattr(g, 'current_department', None)
        if not current_dept:
            return jsonify({'success': False, 'message': 'Keine Abteilung ausgewählt.'})

        from app.services.location_service import location_service
        if location_service.create_location(name, current_dept):
            return jsonify({
                'success': True,
                'message': 'Standort erfolgreich hinzugefügt.'
            })
        else:
            return jsonify({'success': False, 'message': 'Dieser Standort existiert bereits in dieser Abteilung.'})

    except Exception as e:
        logger.error(f"Fehler beim Hinzufügen des Standorts: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Ein Fehler ist aufgetreten.'
        })

@bp.route('/available-logos')
@mitarbeiter_required
def available_logos():
    """Gibt eine Liste der verfügbaren Logos zurück"""
    try:
        # Verwende den AdminDebugService
        logos = AdminDebugService.get_available_logos()
        return jsonify({
            'success': True,
            'logos': logos
        })
    except Exception as e:
        logger.error(f"Fehler beim Laden der Logos: [Interner Fehler]")
        return jsonify({
            'success': False,
            'message': 'Fehler beim Laden der Logos'
        }), 500

@bp.route('/email_settings', methods=['GET', 'POST'])
@admin_required
def email_settings():
    """E-Mail-Konfiguration verwalten"""
    try:
        # Automatische E-Mail-Reparatur beim Aufruf der E-Mail-Einstellungen
        try:
            AdminDebugService.fix_email_configuration()
            logger.info("Automatische E-Mail-Reparatur durchgeführt")
        except Exception as e:
            logger.warning(f"Automatische E-Mail-Reparatur fehlgeschlagen: [Interner Fehler]")

        # Session-Persistierung vor dem Speichern
        current_user_id = session.get('user_id')
        current_username = session.get('username')
        current_role = session.get('role')
        current_authenticated = session.get('is_authenticated', False)

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'save':
                # E-Mail-Konfiguration speichern
                use_auth = request.form.get('use_auth') == 'on'

                if use_auth:
                    # Mit Authentifizierung
                    new_password = request.form.get('mail_password', '').strip()

                    # Wenn kein neues Passwort eingegeben wurde, verwende das gespeicherte
                    if not new_password:
                        stored_config = AdminEmailService.get_email_config()
                        if stored_config and stored_config.get('mail_password'):
                            new_password = stored_config['mail_password']

                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('mail_username', ''),
                        'mail_password': new_password,
                        'test_email': request.form.get('test_email', ''),
                        'use_auth': True
                    }
                else:
                    # Ohne Authentifizierung
                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('sender_email', ''),  # Absender-E-Mail
                        'mail_password': '',  # Kein Passwort
                        'test_email': request.form.get('test_email', ''),
                        'use_auth': False
                    }

                success, message = AdminEmailService.save_email_config(config_data)

                # Session wiederherstellen nach dem Speichern
                if current_user_id:
                    session['user_id'] = current_user_id
                if current_username:
                    session['username'] = current_username
                if current_role:
                    session['role'] = current_role
                if current_authenticated:
                    session['is_authenticated'] = current_authenticated

                if success:
                    flash(message, 'success')
                else:
                    flash(message, 'error')

            elif action == 'test':
                # E-Mail-Konfiguration testen
                use_auth = request.form.get('use_auth') == 'on'

                if use_auth:
                    # Mit Authentifizierung
                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('mail_username', ''),
                        'mail_password': request.form.get('mail_password', ''),
                        'test_email': request.form.get('test_email', '')
                    }

                    # Wenn kein neues Passwort eingegeben wurde, verwende das gespeicherte
                    if not config_data['mail_password']:
                        stored_config = AdminEmailService.get_email_config()
                        if stored_config and stored_config.get('mail_password'):
                            config_data['mail_password'] = stored_config['mail_password']
                else:
                    # Ohne Authentifizierung
                    config_data = {
                        'mail_server': request.form.get('mail_server', 'smtp.gmail.com'),
                        'mail_port': int(request.form.get('mail_port', 587)),
                        'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                        'mail_username': request.form.get('sender_email', ''),  # Absender-E-Mail
                        'mail_password': '',  # Kein Passwort
                        'test_email': request.form.get('test_email', '')
                    }

                success, message = AdminEmailService.test_email_config(config_data)

                # Session wiederherstellen nach dem Test
                if current_user_id:
                    session['user_id'] = current_user_id
                if current_username:
                    session['username'] = current_username
                if current_role:
                    session['role'] = current_role
                if current_authenticated:
                    session['is_authenticated'] = current_authenticated

                if success:
                    flash(f'E-Mail-Test erfolgreich: {message}', 'success')
                else:
                    flash(f'E-Mail-Test fehlgeschlagen: {message}', 'error')

        # Lade aktuelle Konfiguration und Vorlagen-Infos
        config = AdminEmailService.get_email_config()
        try:
            from app.services.admin_email_templates_service import AdminEmailTemplatesService
            # Standardvorlagen sicherstellen (einmalig)
            AdminEmailTemplatesService.ensure_default_templates()
            templates = AdminEmailTemplatesService.list_templates()
            mappings = AdminEmailTemplatesService.get_template_mappings()
            # Mapping key -> template
            templates_by_key = {t.get('key'): t for t in templates}
        except Exception:
            templates = []
            mappings = {'auftrag_confirmation': 'auftrag_confirmation', 'password_reset': 'password_reset', 'user_welcome': 'user_welcome'}
            templates_by_key = {}

        # Entferne das Passwort aus der Konfiguration für das Template
        if config and 'mail_password' in config:
            config['mail_password'] = ''  # Leeres Feld, da Passwort verschlüsselt ist

        return render_template('admin/email_settings.html', config=config, templates=templates, mappings=mappings, templates_by_key=templates_by_key)

    except Exception as e:
        logger.error(f"Fehler bei E-Mail-Einstellungen: [Interner Fehler]")

        # Session wiederherstellen bei Fehlern
        if current_user_id:
            session['user_id'] = current_user_id
        if current_username:
            session['username'] = current_username
        if current_role:
            session['role'] = current_role
        if current_authenticated:
            session['is_authenticated'] = current_authenticated

        flash('Fehler beim Laden der E-Mail-Einstellungen.', 'error')
        return redirect(url_for('admin.dashboard'))

@bp.route('/switch-department/<department>')
@login_required
def switch_department(department):
    """Setzt das aktive Department in der Session, falls der Benutzer berechtigt ist."""
    try:
        user = mongodb.find_one('users', {'username': current_user.username})
        user_role = (user or {}).get('role') or getattr(current_user, 'role', None)

        # Admins: dürfen in jedes vorhandene Department wechseln
        if user_role == 'admin':
            depts_setting = mongodb.find_one('settings', {'key': 'departments'})
            all_departments = (depts_setting or {}).get('value', [])
            if department in all_departments:
                session['department'] = department
                flash(f'Aktives Department: {department}', 'success')
            else:
                flash('Abteilung existiert nicht', 'error')

            from app.utils.auth_utils import is_safe_url
            target = request.referrer if is_safe_url(request.referrer) else url_for('main.index')
            return redirect(target)

        # Nicht-Admins: nur innerhalb erlaubter Abteilungen
        allowed = user.get('allowed_departments', []) if user else []
        if department in allowed:
            session['department'] = department
            flash(f'Aktives Department: {department}', 'success')
        else:
            flash('Keine Berechtigung für diese Abteilung', 'error')
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Fehler beim Wechseln des Departments: [Interner Fehler]")
        flash('Fehler beim Wechseln des Departments', 'error')

    from app.utils.auth_utils import is_safe_url
    target = request.referrer if is_safe_url(request.referrer) else url_for('main.index')
    return redirect(target)

@bp.route('/admin/email/diagnose', methods=['POST'])
@login_required
@admin_required
def diagnose_email():
    """Diagnostiziert die SMTP-Verbindung"""
    try:
        config_data = AdminEmailService.get_email_config()
        if not config_data:
            return jsonify({'success': False, 'message': 'Keine E-Mail-Konfiguration gefunden'})

        success, result = AdminEmailService.diagnose_smtp_connection(config_data)

        if success:
            return jsonify({
                'success': True,
                'message': 'SMTP-Diagnose erfolgreich',
                'diagnosis': result
            })
        else:
            return jsonify({
                'success': False,
                'message': result
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Diagnose-Fehler: [Interner Fehler]'
        })

@bp.route('/version/check', methods=['GET'])
@login_required
@admin_required
def check_version():
    """Prüft ob Updates verfügbar sind"""
    try:
        from app.utils.version_checker import check_version

        result = check_version()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Fehler beim Versionscheck: [Interner Fehler]")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Versionscheck: [Interner Fehler]'
        }), 500

@bp.route('/version_check', methods=['GET'])
@login_required
def version_check():
    """Prüft ob Updates verfügbar sind (für alle Benutzer)"""
    try:
        from app.utils.version_checker import check_version

        result = check_version()

        # Vereinfachte Antwort für das Menü
        if result.get('status') == 'update_available':
            return jsonify({
                'update_available': True,
                'current_version': result.get('current_version'),
                'latest_version': result.get('latest_version')
            })
        else:
            return jsonify({
                'update_available': False,
                'current_version': result.get('current_version')
            })

    except Exception as e:
        logger.error(f"Fehler beim Versionscheck: [Interner Fehler]")
        return jsonify({
            'update_available': False,
            'error': 'Ein interner Fehler ist aufgetreten.'
        })

@bp.route('/version/info', methods=['GET'])
@login_required
@admin_required
def get_version_info():
    """Gibt detaillierte Versionsinformationen zurück"""
    try:
        from app.utils.version_checker import get_version_info

        info = get_version_info()
        return jsonify(info)

    except Exception as e:
        logger.error(f"Fehler beim Abrufen der Versionsinformationen: [Interner Fehler]")
        return jsonify({
            'status': 'error',
            'message': f'Fehler beim Abrufen der Versionsinformationen: [Interner Fehler]'
        }), 500

@bp.route('/version', methods=['GET'])
@login_required
@admin_required
def version_check_page():
    """Versionscheck-Seite"""
    try:
        return render_template('admin/version_check.html')
    except Exception as e:
        logger.error(f"Fehler beim Laden der Versionscheck-Seite: [Interner Fehler]")
        flash(f'Fehler beim Laden der Seite: [Interner Fehler]', 'error')
        return redirect(url_for('admin.dashboard'))
