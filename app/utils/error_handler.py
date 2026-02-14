from functools import wraps
from flask import render_template, flash, jsonify, request, current_app, session
from pymongo.errors import PyMongoError
import logging
import traceback
import sys
from werkzeug.exceptions import HTTPException
import os
from datetime import datetime

logger = logging.getLogger('app.error_handler')

def setup_logging():
    """Richtet das Logging-System ein"""
    try:
        log_dir = os.path.join(current_app.root_path, '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)

        # Log-Datei mit Datum
        log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')

        # Konfiguriere File-Handler nur für unseren App-Logger
        app_logger = logging.getLogger('app')
        app_logger.setLevel(logging.INFO)

        # Prüfe ob Handler bereits existieren
        if not app_logger.handlers:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            app_logger.addHandler(file_handler)

            # Console-Handler nur für App-Logger
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            app_logger.addHandler(console_handler)

        # Verhindere Propagation zum Root-Logger
        app_logger.propagate = False

    except Exception as e:
        # Fallback: Verwende nur Console-Logging
        print(f"Logging-Setup fehlgeschlagen: {str(e)}")
        app_logger = logging.getLogger('app')
        app_logger.setLevel(logging.INFO)
        if not app_logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            app_logger.addHandler(console_handler)
        app_logger.propagate = False

def handle_errors(app):
    """Registriert Error-Handler für die Flask-App"""

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(401)
    def unauthorized_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Unauthorized'}), 401
        return render_template('errors/401.html'), 401

    # Bad Request Handler
    @app.errorhandler(400)
    def bad_request_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Bad request'}), 400
        return render_template('errors/400.html'), 400

    # Allgemeiner Exception-Handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Logge den Fehler
        logger.error(f"Unbehandelter Fehler: {str(e)}")

        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

    @app.before_request
    def log_request_info():
        """Loggt Informationen über eingehende Anfragen"""
        logger.info(f"Request: {request.method} {request.url} - IP: {request.remote_addr}")

    @app.after_request
    def log_response_info(response):
        """Loggt Informationen über die Antwort"""
        try:
            # Prüfe ob es sich um eine statische Datei handelt
            if hasattr(response, 'direct_passthrough') and response.direct_passthrough:
                logger.info(f"Response: {response.status} {response.status_code} - Static File")
                return response

            # Für normale Antworten
            logger.info(f"Response: {response.status} {response.status_code} - Size: {len(response.get_data())} bytes")
        except Exception as e:
            logger.error(f"Fehler beim Loggen der Antwort: {str(e)}")
        return response

def safe_db_query(func):
    """Decorator für sichere Datenbankabfragen"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PyMongoError as e:
            logger.error(f"Datenbankfehler in {func.__name__}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            return []  # Leere Liste bei Datenbankfehlern
        except Exception as e:
            logger.error(f"Unerwarteter Fehler in {func.__name__}: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            return []
    return wrapper