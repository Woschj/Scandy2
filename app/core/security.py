"""
Security module for Flask application.

Handles authentication, session management, and security-related configurations.
"""

import logging
import secrets
from datetime import datetime, timedelta
from flask import Flask, request, session, g
from flask_login import LoginManager, current_user
import os

logger = logging.getLogger(__name__)

# Flask-Login Manager
login_manager = LoginManager()
login_manager.session_protection = "basic"  # Less strict for HTTP
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"


def init_security(app):
    """
    Initialize security-related components.

    Args:
        app: Flask application instance
    """
    # Initialize Flask-Login
    login_manager.init_app(app)

    # Configure session security based on HTTPS settings
    configure_session_security(app)

    # Set up session cleanup
    setup_session_cleanup(app)

    logger.info("Security components initialized")


def configure_session_security(app):
    """
    Configure session security settings based on environment.

    Args:
        app: Flask application instance
    """
    # Session configuration
    app.config.setdefault('SESSION_TYPE', 'filesystem')
    app.config.setdefault('SESSION_FILE_DIR', os.path.join(app.root_path, 'flask_session'))
    app.config.setdefault('SESSION_FILE_THRESHOLD', 500)
    app.config.setdefault('SESSION_FILE_MODE', 0o644)

    # Session cookie settings for HTTP (Port 80)
    if not app.config.get('SESSION_COOKIE_SECURE', False):
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['SESSION_COOKIE_DOMAIN'] = None  # No domain restriction for intranet
        app.config['REMEMBER_COOKIE_SECURE'] = False
        app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
        app.config['REMEMBER_COOKIE_DOMAIN'] = None

    app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(days=7))  # 7 days for intranet

    logger.info("Session security configured")


def setup_session_cleanup(app):
    """
    Set up automatic session file cleanup.

    Args:
        app: Flask application instance
    """
    def cleanup_old_sessions():
        """Clean up old session files"""
        try:
            session_dir = app.config['SESSION_FILE_DIR']
            if os.path.exists(session_dir):
                current_time = datetime.now()
                session_lifetime = app.config.get('PERMANENT_SESSION_LIFETIME', timedelta(days=7))

                # Ensure session_lifetime is a timedelta
                if isinstance(session_lifetime, int):
                    session_lifetime = timedelta(days=session_lifetime)

                cutoff_time = current_time - session_lifetime
                cleaned_count = 0

                for filename in os.listdir(session_dir):
                    file_path = os.path.join(session_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            if file_mtime < cutoff_time:
                                os.remove(file_path)
                                cleaned_count += 1
                        except Exception:
                            pass

                if cleaned_count > 0:
                    app.logger.info(f"Session cleanup: {cleaned_count} old session files deleted")

                # Ensure all remaining session files have correct permissions
                for filename in os.listdir(session_dir):
                    file_path = os.path.join(session_dir, filename)
                    if os.path.isfile(file_path):
                        try:
                            os.chmod(file_path, 0o644)  # rw-r--r--
                        except Exception:
                            pass
        except Exception as e:
            app.logger.warning(f"Error during session cleanup: {str(e)}")

    # Run cleanup on startup
    cleanup_old_sessions()


@login_manager.user_loader
def load_user(user_id):
    """
    Load user from database for Flask-Login.

    Args:
        user_id: User ID (always a string from Flask-Login)

    Returns:
        User object or None if not found
    """
    try:
        from app.models.mongodb_models import MongoDBUser
        from app.models.user import User
        from app.models.mongodb_database import mongodb

        logging.debug(f"load_user called for ID: {user_id}")

        # Debug: Show all available user IDs
        all_users = MongoDBUser.get_all()
        logging.debug(f"Available user IDs: {[str(user.get('_id', 'No ID')) for user in all_users]}")

        # Method 1: Direct string search
        user_data = mongodb.find_one('users', {'_id': user_id})
        if user_data:
            logging.debug(f"User found with string ID: {user_data.get('username')}")
            user = User(user_data)
            logging.debug(f"User loaded: {user.username}, ID: {user.id}")
            return user

        # Method 2: ObjectId search
        try:
            from bson import ObjectId
            obj_id = ObjectId(user_id)
            user_data = mongodb.find_one('users', {'_id': obj_id})
            if user_data:
                logging.debug(f"User found with ObjectId: {user_data.get('username')}")
                user = User(user_data)
                logging.debug(f"User loaded: {user.username}, ID: {user.id}")
                return user
        except Exception as e:
            logging.debug(f"ObjectId conversion failed: {str(e)}")

        # Method 3: Fallback with MongoDBUser.get_by_id
        user_data = MongoDBUser.get_by_id(user_id)
        if user_data:
            logging.debug(f"User found with MongoDBUser.get_by_id: {user_data.get('username')}")
            user = User(user_data)
            logging.debug(f"User loaded: {user.username}, ID: {user.id}")
            return user

        # Method 4: Session repair - try to clear session
        logging.debug(f"No user found for ID: {user_id} - resetting session")
        try:
            from flask import session
            session.clear()
            logging.debug("Session cleared")
        except Exception as e:
            logging.debug(f"Error clearing session: {str(e)}")

        return None

    except Exception as e:
        logging.error(f"Error loading user {user_id}: {str(e)}")
        # Clear session on error
        try:
            from flask import session
            session.clear()
            logging.debug("Session cleared after error")
        except Exception as session_error:
            logging.debug(f"Error clearing session: {session_error}")
        return None


def load_current_department():
    """
    Load current department into request context.
    Fallback: Use user's default department or first allowed department.
    """
    try:
        dept = session.get('department')

        # If no department in session, derive from user profile
        if not dept and current_user.is_authenticated:
            try:
                from app.models.mongodb_database import mongodb
                user = mongodb.find_one('users', {'username': current_user.username})

                # Admin: Use first global department if available
                if getattr(current_user, 'role', None) == 'admin':
                    depts_setting = mongodb.find_one('settings', {'key': 'departments'})
                    all_departments = depts_setting.get('value', []) if depts_setting else []

                    # Admin: Prefer user default, otherwise first global
                    if user and user.get('default_department'):
                        dept = user.get('default_department')
                    elif isinstance(all_departments, list) and all_departments:
                        dept = all_departments[0]
                    else:
                        dept = (user.get('allowed_departments') or [None])[0] if user else None
                else:
                    if user:
                        dept = user.get('default_department') or (user.get('allowed_departments') or [None])[0]

                if dept:
                    session['department'] = dept
            except Exception:
                pass

        g.current_department = dept
    except Exception:
        g.current_department = None


def ensure_directories_exist():
    """
    Ensure all required directories exist.

    Creates:
    - Backup directory
    - Upload directory
    - Temporary directory
    - Session file directory
    """
    from app.config.config import config as config_instance
    from pathlib import Path

    current_config = config_instance
    project_root = Path(current_config.base_dir)

    # List of directories to create
    directories = [
        current_config.backup_dir,
        current_config.upload_folder,
        project_root / 'tmp',
        current_config.session.file_dir
    ]

    # Create directories
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Directory created: {dir_path}")
        else:
            logging.info(f"Directory already exists: {dir_path}")
