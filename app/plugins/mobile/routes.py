from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models.mongodb_database import mongodb
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('mobile', __name__)

@bp.before_request
def ensure_mobile_department():
    """Sorge dafür, dass eine Abteilung im Request-Kontext gesetzt ist,
    damit die Mongo-Scopes (department) Treffer liefern."""
    try:
        if getattr(g, 'current_department', None):
            return
        dept = session.get('current_department')
        if not dept and current_user.is_authenticated:
            # bevorzugt Default-Abteilung des Users
            dept = getattr(current_user, 'default_department', None)
            if not dept:
                # Fallback: erste verfügbare Abteilung aus Settings
                settings_departments = mongodb.find_one('settings', {'key': 'departments'})
                if settings_departments and settings_departments.get('value'):
                    dept = settings_departments['value'][0]
        if dept:
            g.current_department = dept
    except Exception as e:
        logger.warning(f"Mobile ensure_department Fehler: {e}")

@bp.route('/quickscan')
def quickscan():
    """Mobile Quickscan-App"""
    return render_template('mobile/quickscan.html')

@bp.route('/login', methods=['POST'])
def login():
    """Mobile Login für Quickscan-App"""
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Benutzername und Passwort sind erforderlich', 'error')
            return redirect(url_for('mobile.quickscan'))
        
        # Benutzer in der Datenbank suchen
        user_data = mongodb.find_one('users', {'username': username})
        
        if not user_data:
            flash('Ungültige Anmeldedaten', 'error')
            return redirect(url_for('mobile.quickscan'))
        
        # Passwort überprüfen
        from werkzeug.security import check_password_hash
        if not check_password_hash(user_data.get('password_hash', ''), password):
            flash('Ungültige Anmeldedaten', 'error')
            return redirect(url_for('mobile.quickscan'))
        
        # User-Objekt erstellen und anmelden
        from app.models.user import User as AppUser
        user = AppUser(user_data)
        
        login_user(user, remember=True)
        
        flash('Erfolgreich angemeldet', 'success')
        return redirect(url_for('mobile.quickscan'))
        
    except Exception as e:
        logger.error(f"Mobile Login-Fehler: {str(e)}")
        flash('Anmeldung fehlgeschlagen', 'error')
        return redirect(url_for('mobile.quickscan'))

@bp.route('/logout')
@login_required
def logout():
    """Mobile Logout"""
    try:
        # Department aus Session und Context entfernen
        session.pop('department', None)
        session.pop('current_department', None)
        if hasattr(g, 'current_department'):
            g.current_department = None
    except Exception:
        pass
    logout_user()
    flash('Erfolgreich abgemeldet', 'success')
    return redirect(url_for('mobile.quickscan'))

@bp.route('/scan', methods=['POST'])
@login_required
def scan_barcode():
    """Barcode-Scan API für mobile App"""
    try:
        barcode = request.json.get('barcode')
        
        if not barcode:
            return jsonify({'success': False, 'error': 'Kein Barcode übermittelt'}), 400
        
        # Suche nach dem Barcode in verschiedenen Sammlungen (trim/varianten)
        result = None
        item_type = None
        code = (barcode or '').strip()
        def _norm_all(c: str) -> list:
            base = (c or '').strip()
            s1 = base.replace(' ', '')
            s2 = s1.replace('-', '').replace('_','')
            s3 = s2.replace('.', '').replace('/', '').replace('\\', '')
            out = set([base, s1, s2, s3, base.upper(), base.lower(), s3.upper(), s3.lower()])
            try:
                if s3.isdigit():
                    out.add(str(int(s3)))
            except Exception:
                pass
            return [v for v in out if v]
        variants = _norm_all(code)
        # Numeric-Variante (Mongo kann auch numerisch gespeicherte Barcodes haben)
        num_variant = None
        try:
            if code.isdigit():
                num_variant = int(code)
        except Exception:
            num_variant = None
        logger.info(f"[mobile.scan] Eingehender Barcode: {barcode} | Varianten: {variants} | numeric={num_variant is not None}")
        debug_checks = []
        
        # Heuristik: Worker priorisieren, wenn der Code wie ein Worker-Code aussieht (z.B. USER_*)
        def _looks_like_worker(c: str) -> bool:
            cu = (c or '').upper()
            return cu.startswith('USER_') or cu.startswith('WORKER_')

        priority_worker = any(_looks_like_worker(v) for v in variants)

        # Optionale Suche nach Username aus USER_* Codes
        def _extract_username(c: str) -> str:
            try:
                cu = (c or '').strip()
                if '_' in cu:
                    return cu.split('_', 1)[1]
                return ''
            except Exception:
                return ''

        if priority_worker and not result:
            for v in variants:
                if _looks_like_worker(v):
                    cond = {'barcode': v, 'deleted': {'$ne': True}}
                    debug_checks.append({'scope': 'scoped', 'collection': 'workers', 'query': cond})
                    worker = mongodb.find_one('workers', cond)
                    if worker:
                        logger.info(f"[mobile.scan] Worker via barcode gefunden (gescoped): {v}")
                        result = worker; item_type = 'worker'; barcode = v; break
                    # Fallback: Username-Variante (case-insensitive)
                    username_guess = _extract_username(v)
                    if username_guess:
                        cond2 = {
                            'username': {'$regex': f'^{username_guess}$', '$options': 'i'},
                            'deleted': {'$ne': True}
                        }
                        debug_checks.append({'scope': 'scoped', 'collection': 'workers', 'query': cond2})
                        worker_by_username = mongodb.find_one('workers', cond2)
                        if worker_by_username:
                            logger.info(f"[mobile.scan] Worker via username gefunden (gescoped): {username_guess}")
                            result = worker_by_username; item_type = 'worker'; barcode = worker_by_username.get('barcode', v); break

        # Suche in allen Collections mit Varianten (mit Department-Scoping)
        if not result:
            for v in variants:
                cond_tool = {'barcode': v, 'deleted': {'$ne': True}}
                debug_checks.append({'scope': 'scoped', 'collection': 'tools', 'query': cond_tool})
                tool = mongodb.find_one('tools', cond_tool)
                if tool:
                    logger.info(f"[mobile.scan] Tool gefunden (gescoped): {v}")
                    result = tool; item_type = 'tool'; barcode = v; break
                cond_cons = {'barcode': v, 'deleted': {'$ne': True}}
                debug_checks.append({'scope': 'scoped', 'collection': 'consumables', 'query': cond_cons})
                consumable = mongodb.find_one('consumables', cond_cons)
                if consumable:
                    logger.info(f"[mobile.scan] Consumable gefunden (gescoped): {v}")
                    result = consumable; item_type = 'consumable'; barcode = v; break
                # Nur wenn nicht bereits als Worker priorisiert geprüft
                if not priority_worker:
                    # Mitarbeiter: erlaube Match auf aktuellem Barcode ODER Legacy-Barcodes
                    cond_w = {
                        '$and': [
                            {'deleted': {'$ne': True}},
                            {'$or': [
                                {'barcode': v},
                                {'legacy_barcodes': v}
                            ]}
                        ]
                    }
                    debug_checks.append({'scope': 'scoped', 'collection': 'workers', 'query': cond_w})
                    worker = mongodb.find_one('workers', cond_w)
                    if worker:
                        logger.info(f"[mobile.scan] Worker gefunden (gescoped): {v}")
                        result = worker; item_type = 'worker'; barcode = worker.get('barcode', v); break

        # Fallback: Zuerst Tools/Consumables global prüfen (ohne Department), inkl. numerischer Barcodes
        if not result:
            try:
                for coll_name in ['tools', 'consumables']:
                    coll = mongodb.get_collection(coll_name)
                    for v in variants:
                        q = {'barcode': v, 'deleted': {'$ne': True}}
                        debug_checks.append({'scope': 'global', 'collection': coll_name, 'query': q})
                        found = coll.find_one(q)
                        if found:
                            logger.info(f"[mobile.scan] {coll_name[:-1].title()} via barcode gefunden (global): {v}")
                            result = found; item_type = 'tool' if coll_name == 'tools' else 'consumable'; barcode = v; break
                        if num_variant is not None:
                            qn = {'barcode': num_variant, 'deleted': {'$ne': True}}
                            debug_checks.append({'scope': 'global', 'collection': coll_name, 'query': qn})
                            foundn = coll.find_one(qn)
                            if foundn:
                                logger.info(f"[mobile.scan] {coll_name[:-1].title()} via numeric barcode gefunden (global): {num_variant}")
                                result = foundn; item_type = 'tool' if coll_name == 'tools' else 'consumable'; barcode = str(num_variant); break
                    if result:
                        break
            except Exception:
                pass

        # Fallback: Worker global (ohne Department-Scoping) suchen – wichtig für Barcodes wie USER_ADMIN
        if not result:
            try:
                workers_coll = mongodb.get_collection('workers')
                for v in variants:
                    qw = {
                        '$and': [
                            {'deleted': {'$ne': True}},
                            {'$or': [
                                {'barcode': v},
                                {'legacy_barcodes': v}
                            ]}
                        ]
                    }
                    debug_checks.append({'scope': 'global', 'collection': 'workers', 'query': qw})
                    worker = workers_coll.find_one(qw)
                    if worker:
                        logger.info(f"[mobile.scan] Worker via barcode gefunden (global): {v}")
                        result = worker; item_type = 'worker'; barcode = worker.get('barcode', v); break
                # zusätzlicher Fallback: Username-Match global (case-insensitive)
                if not result and priority_worker:
                    for v in variants:
                        if _looks_like_worker(v):
                            username_guess = _extract_username(v)
                            if username_guess:
                                qw2 = {
                                    'username': {'$regex': f'^{username_guess}$', '$options': 'i'},
                                    'deleted': {'$ne': True}
                                }
                                debug_checks.append({'scope': 'global', 'collection': 'workers', 'query': qw2})
                                worker = workers_coll.find_one(qw2)
                                if worker:
                                    logger.info(f"[mobile.scan] Worker via username gefunden (global): {username_guess}")
                                    result = worker; item_type = 'worker'; barcode = worker.get('barcode', v); break
            except Exception:
                pass
        
        if not result:
            logger.info(f"[mobile.scan] Kein Treffer für Varianten: {variants}")
            return jsonify({
                'success': False, 
                'error': 'Barcode nicht gefunden',
                'barcode': barcode,
                'debug': {
                    'variants': variants,
                    'priority_worker': priority_worker,
                    'current_department': getattr(g, 'current_department', None),
                    'checks': debug_checks
                }
            }), 404
        
        # Aktuelle Ausleihe prüfen
        lending = mongodb.find_one('lendings', {
            'item_barcode': barcode,
            'return_date': None
        })
        
        # Ergebnis formatieren
        response_data = {
            'success': True,
            'item': {
                'id': str(result['_id']),
                'name': result.get('name', result.get('title', 'Unbekannt')),
                'barcode': barcode,
                'type': item_type,
                'description': result.get('description', ''),
                'status': result.get('status', 'verfügbar'),
                'firstname': result.get('firstname'),
                'lastname': result.get('lastname'),
                'username': result.get('username')
            },
            'lending': None
        }
        
        if lending:
            response_data['lending'] = {
                'id': str(lending['_id']),
                'worker_name': lending.get('worker_name', 'Unbekannt'),
                'action_date': lending.get('action_date', ''),
                'return_date': lending.get('return_date')
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Barcode-Scan-Fehler: {str(e)}")
        return jsonify({'success': False, 'error': 'Interner Server-Fehler'}), 500

@bp.route('/lend', methods=['POST'])
@login_required
def lend_item():
    """Item ausleihen/rückgeben"""
    try:
        data = request.json
        barcode = data.get('barcode')
        action = data.get('action')  # 'lend' oder 'return'
        worker_name = data.get('worker_name', current_user.username)
        
        if not barcode or not action:
            return jsonify({'success': False, 'error': 'Ungültige Parameter'}), 400
        
        if action == 'lend':
            # Prüfe ob Item bereits ausgeliehen ist
            existing_lending = mongodb.find_one('lendings', {
                'item_barcode': barcode,
                'return_date': None
            })
            
            if existing_lending:
                return jsonify({
                    'success': False, 
                    'error': 'Item ist bereits ausgeliehen',
                    'lending': {
                        'worker_name': existing_lending.get('worker_name'),
                        'action_date': existing_lending.get('action_date')
                    }
                }), 409
            
            # Neue Ausleihe erstellen
            from datetime import datetime
            lending_data = {
                'item_barcode': barcode,
                'worker_name': worker_name,
                'action_date': datetime.now(),
                'return_date': None,
                'created_by': current_user.username
            }
            
            mongodb.insert('lendings', lending_data)
            
            return jsonify({
                'success': True,
                'message': 'Item erfolgreich ausgeliehen',
                'lending': lending_data
            })
            
        elif action == 'return':
            # Ausleihe beenden
            lending = mongodb.find_one('lendings', {
                'item_barcode': barcode,
                'return_date': None
            })
            
            if not lending:
                return jsonify({
                    'success': False, 
                    'error': 'Keine aktive Ausleihe gefunden'
                }), 404
            
            # Rückgabe-Datum setzen
            from datetime import datetime
            mongodb.update('lendings', 
                         {'_id': lending['_id']}, 
                         {'return_date': datetime.now()})
            
            return jsonify({
                'success': True,
                'message': 'Item erfolgreich zurückgegeben'
            })
        
        else:
            return jsonify({'success': False, 'error': 'Ungültige Aktion'}), 400
            
    except Exception as e:
        logger.error(f"Lending-Fehler: {str(e)}")
        return jsonify({'success': False, 'error': 'Interner Server-Fehler'}), 500 