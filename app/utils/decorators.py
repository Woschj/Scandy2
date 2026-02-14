from functools import wraps
from flask import session, redirect, url_for, request, flash, abort, jsonify
from datetime import datetime
from app.utils.logger import loggers, log_security_event, log_user_action, log_performance_metric
from flask_login import current_user
import logging # Import logging
import time
# needs_setup wird nur in login_required verwendet
# from app.utils.auth_utils import needs_setup

logger = logging.getLogger(__name__) # Logger für dieses Modul

def login_required(f):
    """Decorator, der sicherstellt, dass ein Benutzer eingeloggt ist.

    Prüft zuerst, ob das System-Setup benötigt wird (via needs_setup()).
    Wenn ja, wird zur Login-Seite weitergeleitet mit einer Flash-Nachricht.
    Wenn nein, wird geprüft, ob eine 'user_id' in der Session vorhanden ist.
    Wenn nicht, wird zur Login-Seite weitergeleitet.
    Andernfalls wird die ursprüngliche Funktion ausgeführt.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Importiere needs_setup hier, um Zirkelimporte zu vermeiden
        from app.utils.auth_utils import needs_setup

        # Wenn Setup benötigt wird, zur Setup-Seite weiterleiten
        if needs_setup():
            flash('System-Setup erforderlich. Bitte erstellen Sie einen Administrator-Account.', 'info')
            return redirect(url_for('setup.setup_admin'))

        # Wenn nicht eingeloggt, zum Login weiterleiten
        if not current_user.is_authenticated:
            # Logge unautorisierte Zugriffe
            log_security_event('unauthorized_access', 'anonymous', request.remote_addr, {
                'endpoint': request.endpoint,
                'url': request.url
            })
            flash('Bitte melden Sie sich an, um auf diese Seite zuzugreifen.', 'info')
            return redirect(url_for('auth.login', next=request.url))

        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """Decorator, der sicherstellt, dass der Benutzer eine bestimmte Rolle hat."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Bitte melden Sie sich an, um auf diese Seite zuzugreifen.", "info")
                return redirect(url_for('auth.login', next=request.url))

            # Prüfe die Rolle
            if current_user.role != role_name:
                abort(403) # Gibt eine "Zugriff verweigert"-Seite zurück
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator für Routen, die nur Admins zugänglich sind."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"[DECORATOR] admin_required: Checking user {getattr(current_user, 'id', 'Guest')}")
        if not current_user.is_authenticated:
            logger.warning(f"[DECORATOR] admin_required: User not authenticated. Redirecting to login.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Bitte melden Sie sich an.',
                    'redirect': url_for('auth.login', next=request.url)
                }), 401
            flash("Bitte melden Sie sich an.", "info")
            return redirect(url_for('auth.login', next=request.url))

        if current_user.role != 'admin':
            # Logge unautorisierte Admin-Zugriffe
            log_security_event('unauthorized_admin_access', current_user.username, request.remote_addr, {
                'endpoint': request.endpoint,
                'user_role': current_user.role
            })
            logger.warning(f"[DECORATOR] admin_required: User {current_user.id} lacks admin permission. Aborting with 403.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Keine Berechtigung für diese Aktion.'
                }), 403
            abort(403)

        logger.debug(f"[DECORATOR] admin_required: Access granted for user {current_user.id}. Proceeding to route function.")
        return f(*args, **kwargs)
    return decorated_function

def mitarbeiter_required(f):
    """Decorator: erlaubt admin, mitarbeiter, anwender; verbietet nur teilnehmer."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"[DECORATOR] mitarbeiter_required: Checking user {getattr(current_user, 'id', 'Guest')}")
        if not current_user.is_authenticated:
            logger.warning(f"[DECORATOR] mitarbeiter_required: User not authenticated. Redirecting to login.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Bitte melden Sie sich an.',
                    'redirect': url_for('auth.login', next=request.url)
                }), 401
            flash("Bitte melden Sie sich an.", "info")
            return redirect(url_for('auth.login', next=request.url))

        # Erlaube alle Rollen außer 'teilnehmer'
        user_role = getattr(current_user, 'role', 'anwender')
        is_allowed = user_role != 'teilnehmer'

        logger.debug(f"[DECORATOR] mitarbeiter_required: User role is '{user_role}', is_allowed evaluated to {is_allowed}")

        if not is_allowed:
            # Logge unautorisierte Zugriffe
            log_security_event('unauthorized_mitarbeiter_access', current_user.username, request.remote_addr, {
                'endpoint': request.endpoint,
                'user_role': user_role
            })
            logger.warning(f"[DECORATOR] mitarbeiter_required: User {current_user.id} (role: {user_role}) lacks permission. Aborting with 403.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Keine Berechtigung für diese Aktion.'
                }), 403
            abort(403)

        logger.debug(f"[DECORATOR] mitarbeiter_required: Access granted for user {current_user.id} (role: {user_role}). Proceeding to route function.")
        return f(*args, **kwargs)
    return decorated_function

def teilnehmer_required(f):
    """Decorator für Routen, die nur Teilnehmern zugänglich sind."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"[DECORATOR] teilnehmer_required: Checking user {getattr(current_user, 'id', 'Guest')}")
        if not current_user.is_authenticated:
            logger.warning(f"[DECORATOR] teilnehmer_required: User not authenticated. Redirecting to login.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Bitte melden Sie sich an.',
                    'redirect': url_for('auth.login', next=request.url)
                }), 401
            flash("Bitte melden Sie sich an.", "info")
            return redirect(url_for('auth.login', next=request.url))

        if current_user.role != 'teilnehmer':
            # Logge unautorisierte Zugriffe
            log_security_event('unauthorized_teilnehmer_access', current_user.username, request.remote_addr, {
                'endpoint': request.endpoint,
                'user_role': current_user.role
            })
            logger.warning(f"[DECORATOR] teilnehmer_required: User {current_user.id} lacks permission. Aborting with 403.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Keine Berechtigung für diese Aktion.'
                }), 403
            abort(403)

        logger.debug(f"[DECORATOR] teilnehmer_required: Access granted for user {current_user.id}. Proceeding to route function.")
        return f(*args, **kwargs)
    return decorated_function

def not_teilnehmer_required(f):
    """Decorator für Routen, die Teilnehmern NICHT zugänglich sind."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.debug(f"[DECORATOR] not_teilnehmer_required: Checking user {getattr(current_user, 'id', 'Guest')}")
        if not current_user.is_authenticated:
            logger.warning(f"[DECORATOR] not_teilnehmer_required: User not authenticated. Redirecting to login.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Bitte melden Sie sich an.',
                    'redirect': url_for('auth.login', next=request.url)
                }), 401
            flash("Bitte melden Sie sich an.", "info")
            return redirect(url_for('auth.login', next=request.url))

        if current_user.role == 'teilnehmer':
            logger.warning(f"[DECORATOR] not_teilnehmer_required: User {current_user.id} is teilnehmer. Aborting with 403.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'message': 'Keine Berechtigung für diese Aktion.'
                }), 403
            abort(403)

        logger.debug(f"[DECORATOR] not_teilnehmer_required: Access granted for user {current_user.id}. Proceeding to route function.")
        return f(*args, **kwargs)
    return decorated_function

def log_route(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()

        loggers['user_actions'].info(
            f"Route aufgerufen: {request.endpoint} - "
            f"Methode: {request.method} - "
            f"IP: {request.remote_addr} - "
            f"User-Agent: {request.user_agent} - "
            f"Args: {kwargs}"
        )

        if request.form:
            safe_form = {k: v for k, v in request.form.items() if 'password' not in k.lower()}
            loggers['user_actions'].info(f"Form-Daten: {safe_form}")

        if request.args:
            loggers['user_actions'].info(f"Query-Parameter: {dict(request.args)}")

        try:
            result = f(*args, **kwargs)

            # Performance-Metriken loggen
            duration = time.time() - start_time
            log_performance_metric('route_duration', duration, 'seconds')

            # Logge erfolgreiche Aktionen
            if current_user.is_authenticated:
                log_user_action('route_access', current_user.username, {
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'duration': duration
                })

            return result
        except Exception as e:
            duration = time.time() - start_time
            loggers['errors'].error(
                f"Fehler in {request.endpoint}: {str(e)}",
                exc_info=True
            )

            # Logge Fehler mit Performance-Metriken
            log_performance_metric('route_error_duration', duration, 'seconds')

            # Logge Sicherheitsereignisse bei bestimmten Fehlern
            if '403' in str(e) or '401' in str(e):
                log_security_event('route_access_denied',
                                 getattr(current_user, 'username', 'anonymous'),
                                 request.remote_addr, {
                                     'endpoint': request.endpoint,
                                     'error': 'Ein interner Fehler ist aufgetreten.'
                                 })

            raise
    return decorated_function

def log_db_operation(operation):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time

                # Logge erfolgreiche DB-Operation
                log_database_operation(operation, 'unknown', duration, True)

                # Performance-Metriken
                log_performance_metric('db_operation_duration', duration, 'seconds')

                return result
            except Exception as e:
                duration = time.time() - start_time

                # Logge fehlgeschlagene DB-Operation
                log_database_operation(operation, 'unknown', duration, False)

                # Logge Fehler
                loggers['database'].error(
                    f"DB Operation: {operation} - "
                    f"Dauer: {duration:.2f}s - "
                    f"Fehler: {str(e)}"
                )

                # Performance-Metriken für Fehler
                log_performance_metric('db_operation_error_duration', duration, 'seconds')

                raise
        return wrapper
    return decorator

def performance_monitor(operation_name):
    """Decorator für Performance-Monitoring"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time

                # Logge Performance-Metriken
                log_performance_metric(f'{operation_name}_duration', duration, 'seconds')

                return result
            except Exception as e:
                duration = time.time() - start_time

                # Logge Fehler-Performance
                log_performance_metric(f'{operation_name}_error_duration', duration, 'seconds')

                raise
        return wrapper
    return decorator 