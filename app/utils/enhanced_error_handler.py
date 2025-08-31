"""
Erweiterte Fehlerbehandlung und Logging für Scandy

Dieses Modul bietet verbesserte Fehlerbehandlung mit:
- Spezifischen Exception-Typen
- Strukturiertes Logging
- Fehler-Kontext-Informationen
- Performance-Monitoring
"""

import logging
import traceback
import time
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import request, g, current_app
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError, ConnectionFailure
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ScandyException(Exception):
    """Basis-Exception für Scandy-spezifische Fehler"""

    def __init__(self, message: str, error_code: str = "GENERIC_ERROR", details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()

class DatabaseException(ScandyException):
    """Datenbank-spezifische Fehler"""
    def __init__(self, message: str, operation: str = None, collection: str = None):
        super().__init__(message, "DATABASE_ERROR", {
            "operation": operation,
            "collection": collection
        })

class ValidationException(ScandyException):
    """Validierungsfehler"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message, "VALIDATION_ERROR", {
            "field": field,
            "value": value
        })

class PermissionException(ScandyException):
    """Berechtigungsfehler"""
    def __init__(self, message: str, required_permission: str = None, user_role: str = None):
        super().__init__(message, "PERMISSION_ERROR", {
            "required_permission": required_permission,
            "user_role": user_role
        })

class ExternalServiceException(ScandyException):
    """Externe Service-Fehler"""
    def __init__(self, message: str, service: str = None, status_code: int = None):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", {
            "service": service,
            "status_code": status_code
        })

def log_error(error: Exception, context: Dict[str, Any] = None, level: int = logging.ERROR) -> str:
    """
    Erweiterte Fehler-Logging-Funktion

    Args:
        error: Die Exception
        context: Zusätzlicher Kontext
        level: Logging-Level

    Returns:
        Error-ID für Nachverfolgung
    """
    error_id = f"ERR_{int(time.time() * 1000000)}"

    # Sammle Kontext-Informationen
    error_context = {
        "error_id": error_id,
        "timestamp": datetime.now().isoformat(),
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "request_info": get_request_context(),
        "user_info": get_user_context()
    }

    # Füge benutzerdefinierten Kontext hinzu
    if context:
        error_context["additional_context"] = context

    # Logge den Fehler
    logger.log(level, f"Error {error_id}: {error_context}")

    # Bei kritischen Fehlern auch als JSON loggen
    if level >= logging.ERROR:
        logger.log(level, f"Error JSON: {json.dumps(error_context, default=str)}")

    return error_id

def get_request_context() -> Dict[str, Any]:
    """Sammelt Request-Kontext-Informationen"""
    try:
        return {
            "method": getattr(request, 'method', None),
            "url": getattr(request, 'url', None),
            "endpoint": getattr(request, 'endpoint', None),
            "remote_addr": getattr(request, 'remote_addr', None),
            "user_agent": getattr(request, 'user_agent', {}).get('string') if hasattr(request, 'user_agent') else None,
            "form_data": dict(request.form) if hasattr(request, 'form') else {},
            "args": dict(request.args) if hasattr(request, 'args') else {}
        }
    except Exception:
        return {"error": "Could not collect request context"}

def get_user_context() -> Dict[str, Any]:
    """Sammelt User-Kontext-Informationen"""
    try:
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return {
                "user_id": getattr(current_user, 'id', None),
                "username": getattr(current_user, 'username', None),
                "role": getattr(current_user, 'role', None),
                "department": getattr(g, 'current_department', None)
            }
        return {"user": "anonymous"}
    except Exception:
        return {"error": "Could not collect user context"}

def safe_db_operation(operation_name: str, collection: str = None):
    """
    Decorator für sichere Datenbankoperationen

    Args:
        operation_name: Name der Operation
        collection: MongoDB-Collection (optional)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Logge erfolgreiche Operationen (nur bei langsamen Queries)
                if execution_time > 1.0:  # Mehr als 1 Sekunde
                    logger.warning(f"Slow DB operation: {operation_name} took {execution_time:.2f}s")

                return result

            except ServerSelectionTimeoutError as e:
                error_id = log_error(e, {
                    "operation": operation_name,
                    "collection": collection,
                    "error_type": "database_connection_timeout"
                })
                raise DatabaseException(f"Datenbank-Verbindungsfehler: {str(e)}", operation_name, collection)

            except ConnectionFailure as e:
                error_id = log_error(e, {
                    "operation": operation_name,
                    "collection": collection,
                    "error_type": "database_connection_failure"
                })
                raise DatabaseException(f"Datenbank-Verbindungsfehler: {str(e)}", operation_name, collection)

            except PyMongoError as e:
                error_id = log_error(e, {
                    "operation": operation_name,
                    "collection": collection,
                    "error_type": "database_error"
                })
                raise DatabaseException(f"Datenbankfehler: {str(e)}", operation_name, collection)

            except Exception as e:
                error_id = log_error(e, {
                    "operation": operation_name,
                    "collection": collection,
                    "error_type": "unexpected_error"
                })
                raise ScandyException(f"Unerwarteter Fehler in {operation_name}: {str(e)}")

        return wrapper
    return decorator

def handle_service_errors(service_name: str):
    """
    Decorator für Service-Methoden mit verbesserter Fehlerbehandlung

    Args:
        service_name: Name des Services
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ScandyException:
                # Scandy-spezifische Fehler weiterleiten
                raise
            except Exception as e:
                # Allgemeine Fehler in ScandyException konvertieren
                error_id = log_error(e, {"service": service_name, "method": func.__name__})
                raise ScandyException(
                    f"Fehler in {service_name}.{func.__name__}: {str(e)}",
                    details={"original_error": str(e), "error_id": error_id}
                )
        return wrapper
    return decorator

def with_performance_monitoring(operation_name: str, threshold: float = 1.0):
    """
    Decorator für Performance-Monitoring

    Args:
        operation_name: Name der Operation
        threshold: Schwellenwert für Logging in Sekunden
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                if execution_time > threshold:
                    logger.warning(f"Performance: {operation_name} took {execution_time:.2f}s "
                                 f"(threshold: {threshold}s)")

                # Füge Performance-Info zum Result hinzu
                if isinstance(result, dict):
                    result["_performance"] = {
                        "operation": operation_name,
                        "execution_time": execution_time,
                        "threshold": threshold
                    }

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                log_error(e, {
                    "operation": operation_name,
                    "execution_time": execution_time,
                    "performance_issue": execution_time > threshold
                })
                raise

        return wrapper
    return decorator

class ErrorCollector:
    """Sammelt Fehler während eines Request-Lebenszyklus"""

    def __init__(self):
        self.errors = []
        self.warnings = []

    def add_error(self, error: Exception, context: Dict[str, Any] = None):
        """Fügt einen Fehler zur Sammlung hinzu"""
        error_info = {
            "error": str(error),
            "type": type(error).__name__,
            "timestamp": datetime.now(),
            "context": context or {}
        }
        self.errors.append(error_info)
        logger.error(f"Collected error: {error_info}")

    def add_warning(self, message: str, context: Dict[str, Any] = None):
        """Fügt eine Warnung zur Sammlung hinzu"""
        warning_info = {
            "message": message,
            "timestamp": datetime.now(),
            "context": context or {}
        }
        self.warnings.append(warning_info)
        logger.warning(f"Collected warning: {warning_info}")

    def get_summary(self) -> Dict[str, Any]:
        """Gibt eine Zusammenfassung der gesammelten Fehler zurück"""
        return {
            "total_errors": len(self.errors),
            "total_warnings": len(self.warnings),
            "errors": self.errors[-5:],  # Letzte 5 Fehler
            "warnings": self.warnings[-5:]  # Letzte 5 Warnungen
        }

    def has_errors(self) -> bool:
        """Prüft ob Fehler vorhanden sind"""
        return len(self.errors) > 0

def get_error_collector() -> ErrorCollector:
    """Gibt den ErrorCollector für den aktuellen Request zurück"""
    if not hasattr(g, 'error_collector'):
        g.error_collector = ErrorCollector()
    return g.error_collector

# Globale Exception-Handler für Flask
def register_enhanced_error_handlers(app):
    """Registriert erweiterte Fehler-Handler für die Flask-App"""

    @app.errorhandler(ScandyException)
    def handle_scandy_exception(error):
        """Handler für Scandy-spezifische Exceptions"""
        error_id = log_error(error, {
            "error_code": error.error_code,
            "details": error.details
        })

        if request.path.startswith('/api/'):
            return jsonify({
                'error': error.message,
                'error_code': error.error_code,
                'error_id': error_id
            }), 500

        return render_template('errors/custom_error.html',
                             error=error,
                             error_id=error_id), 500

    @app.errorhandler(DatabaseException)
    def handle_database_exception(error):
        """Handler für Datenbank-Exceptions"""
        error_id = log_error(error, {
            "operation": error.details.get('operation'),
            "collection": error.details.get('collection')
        })

        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Datenbankfehler',
                'error_id': error_id
            }), 500

        return render_template('errors/database_error.html',
                             error=error,
                             error_id=error_id), 500

    @app.errorhandler(PermissionException)
    def handle_permission_exception(error):
        """Handler für Berechtigungsfehler"""
        error_id = log_error(error, {
            "required_permission": error.details.get('required_permission'),
            "user_role": error.details.get('user_role')
        })

        if request.path.startswith('/api/'):
            return jsonify({
                'error': 'Keine Berechtigung',
                'error_id': error_id
            }), 403

        return render_template('errors/permission_error.html',
                             error=error,
                             error_id=error_id), 403

    @app.errorhandler(ValidationException)
    def handle_validation_exception(error):
        """Handler für Validierungsfehler"""
        error_id = log_error(error, {
            "field": error.details.get('field'),
            "value": error.details.get('value')
        })

        if request.path.startswith('/api/'):
            return jsonify({
                'error': error.message,
                'field': error.details.get('field'),
                'error_id': error_id
            }), 400

        return render_template('errors/validation_error.html',
                             error=error,
                             error_id=error_id), 400

    # Erweitere Request-Logging
    @app.before_request
    def enhanced_request_logging():
        """Erweiterte Request-Logging"""
        g.request_start_time = time.time()
        g.error_collector = ErrorCollector()

        logger.info(f"Request: {request.method} {request.url} - IP: {request.remote_addr} - User: {get_user_context()}")

    @app.after_request
    def enhanced_response_logging(response):
        """Erweiterte Response-Logging"""
        if hasattr(g, 'request_start_time'):
            execution_time = time.time() - g.request_start_time

            # Sammle Performance-Informationen (sichere Größenberechnung)
            response_size = 0
            try:
                if hasattr(response, 'direct_passthrough') and response.direct_passthrough:
                    # Bei direkten Dateien (CSS, JS, Bilder) keine Größe berechnen
                    response_size = "direct_passthrough"
                elif hasattr(response, 'get_data'):
                    response_size = len(response.get_data())
                else:
                    response_size = "unknown"
            except (RuntimeError, AttributeError):
                # Fallback bei Problemen mit der Größenberechnung
                response_size = "error_calculating"

            performance_info = {
                "execution_time": execution_time,
                "status_code": response.status_code,
                "response_size": response_size
            }

            # Logge langsame Requests
            if execution_time > 2.0:  # Mehr als 2 Sekunden
                logger.warning(f"Slow request: {request.method} {request.url} took {execution_time:.2f}s")

            # Sammle Error-Informationen
            if hasattr(g, 'error_collector'):
                error_summary = g.error_collector.get_summary()
                if error_summary['total_errors'] > 0:
                    performance_info['errors'] = error_summary

            # Berechne Error-Count sicher
            error_count = 0
            if 'error_summary' in locals():
                error_count = error_summary.get('total_errors', 0)

            logger.info(f"Response: {response.status} - Time: {execution_time:.3f}s - Errors: {error_count}")

        return response

# Utility-Funktionen für verbesserte Fehlerbehandlung
def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    Validiert erforderliche Felder

    Args:
        data: Zu validierende Daten
        required_fields: Liste der erforderlichen Felder

    Raises:
        ValidationException: Bei fehlenden Feldern
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            missing_fields.append(field)

    if missing_fields:
        raise ValidationException(
            f"Fehlende erforderliche Felder: {', '.join(missing_fields)}",
            field=missing_fields[0]
        )

def validate_permission(user_role: str, required_permission: str) -> None:
    """
    Validiert Berechtigungen

    Args:
        user_role: Rolle des Users
        required_permission: Erforderliche Berechtigung

    Raises:
        PermissionException: Bei fehlenden Berechtigungen
    """
    # Vereinfachte Berechtigungslogik - kann erweitert werden
    role_permissions = {
        'admin': ['*'],  # Admin hat alle Berechtigungen
        'mitarbeiter': ['read', 'write', 'update'],
        'anwender': ['read', 'write'],
        'teilnehmer': ['read']
    }

    user_permissions = role_permissions.get(user_role, [])

    if '*' in user_permissions or required_permission in user_permissions:
        return

    raise PermissionException(
        f"Keine Berechtigung für '{required_permission}'",
        required_permission=required_permission,
        user_role=user_role
    )
