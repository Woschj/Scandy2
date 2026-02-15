from app.utils.id_helpers import convert_id_for_query
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user, login_user, logout_user
from app.models.mongodb_database import mongodb
from app.models.user import User
from app.models.mongodb_models import MongoDBUser
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.auth_utils import needs_setup, is_safe_url
from datetime import datetime
from bson import ObjectId
import secrets
import logging
import re
from urllib.parse import urlparse

bp = Blueprint('auth', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)

def get_objectid_if_possible(id_value):
    if isinstance(id_value, str) and len(id_value) == 24:
        try:
            return ObjectId(id_value)
        except Exception:
            return id_value
    return id_value

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        username_or_email = (request.form.get('username') or '').strip()
        if not username_or_email:
            flash('Bitte Benutzername oder E-Mail eingeben', 'error')
            return render_template('auth/reset_password.html')
        # User suchen: E-Mail und Username case-insensitiv
        if '@' in username_or_email:
            pattern = {'$regex': f'^{re.escape(username_or_email)}$', '$options': 'i'}
            user = mongodb.find_one('users', {'email': pattern})
        else:
            pattern = {'$regex': f'^{re.escape(username_or_email)}$', '$options': 'i'}
            user = mongodb.find_one('users', {'username': pattern})
        if not user:
            flash('Kein Benutzer gefunden', 'error')
            return render_template('auth/reset_password.html')
        # E-Mail-Adresse prüfen
        recipient_email = (user.get('email') or '').strip()
        if not recipient_email:
            flash('Für diesen Benutzer ist keine E-Mail-Adresse hinterlegt. Bitte wenden Sie sich an den Administrator.', 'error')
            return render_template('auth/reset_password.html')

        # Token erzeugen und in DB speichern (gültig 60 Minuten)
        from datetime import timedelta
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=60)
        try:
            mongodb.insert_one('password_reset_tokens', {
                'token': token,
                'user_id': user.get('_id'),
                'username': user.get('username'),
                'email': recipient_email,
                'created_at': datetime.utcnow(),
                'expires_at': expires_at,
                'used': False
            })
        except Exception:
            flash('Fehler beim Erstellen des Reset-Links. Bitte später erneut versuchen.', 'error')
            return render_template('auth/reset_password.html')

        # E-Mail versenden
        try:
            from app.utils.email_utils import send_password_reset_email
            if send_password_reset_email(recipient_email, token):
                flash('Ein Link zum Zurücksetzen Ihres Passworts wurde an Ihre E-Mail-Adresse gesendet.', 'success')
            else:
                flash('Der Reset-Link konnte nicht per E-Mail versendet werden. Bitte kontaktieren Sie den Administrator.', 'error')
        except Exception as e:
            logger.error(f"Fehler beim E-Mail-Versand: [Interner Fehler]")
            flash('Ein technischer Fehler ist aufgetreten. Bitte kontaktieren Sie den Administrator.', 'error')

        return render_template('auth/reset_password.html')

    return render_template('auth/reset_password.html')

@bp.route('/reset_password_confirm/<token>', methods=['GET', 'POST'])
def reset_password_confirm(token):
    # Token validieren
    token_doc = mongodb.find_one('password_reset_tokens', {
        'token': token,
        'used': False,
        'expires_at': {'$gt': datetime.utcnow()}
    })

    if not token_doc:
        flash('Der Link zum Zurücksetzen des Passworts ist ungültig oder abgelaufen.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if not password or len(password) < 8:
            flash('Das Passwort muss mindestens 8 Zeichen lang sein.', 'error')
            return render_template('auth/reset_password_confirm.html', token=token)

        if password != confirm:
            flash('Die Passwörter stimmen nicht überein.', 'error')
            return render_template('auth/reset_password_confirm.html', token=token)

        # Passwort aktualisieren
        try:
            user_id = token_doc.get('user_id')
            mongodb.update_one('users',
                             {'_id': user_id},
                             {'$set': {
                                 'password_hash': generate_password_hash(password),
                                 'updated_at': datetime.now()
                             }})

            # Token als verwendet markieren
            mongodb.update_one('password_reset_tokens',
                             {'_id': token_doc['_id']},
                             {'$set': {'used': True}})

            flash('Ihr Passwort wurde erfolgreich zurückgesetzt. Sie können sich nun anmelden.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error(f"Fehler beim Zurücksetzen des Passworts: [Interner Fehler]")
            flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.', 'error')

    return render_template('auth/reset_password_confirm.html', token=token)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Benutzeranmeldung.
    """
    # Wenn bereits eingeloggt, zum Dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        # Validierung
        if not username or not password:
            flash('Bitte geben Sie Benutzername und Passwort ein.', 'error')
            return render_template('auth/login.html')

        # Benutzer suchen (case-insensitive)
        user_data = mongodb.find_one('users', {
            'username': {'$regex': f'^{re.escape(username)}$', '$options': 'i'}
        })

        if user_data:
            # Passwort prüfen
            if check_password_hash(user_data.get('password_hash', ''), password):
                # Status prüfen
                if not user_data.get('is_active', True):
                    flash('Dieses Benutzerkonto ist deaktiviert.', 'error')
                    return render_template('auth/login.html')

                # User-Objekt erstellen und einloggen
                user = User(user_data)
                login_user(user, remember=remember)

                # Letzten Login speichern
                mongodb.update_one('users',
                                 {'_id': user_data['_id']},
                                 {'$set': {'last_login': datetime.now()}})

                # Department setzen (falls vorhanden)
                if user_data.get('default_department'):
                    session['department'] = user_data['default_department']
                elif user_data.get('allowed_departments'):
                    session['department'] = user_data['allowed_departments'][0]

                # Redirect zur ursprünglich gewünschten Seite
                next_page = request.args.get('next')
                if next_page and is_safe_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('dashboard.index'))

        flash('Ungültiger Benutzername oder Passwort.', 'error')

    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    """Benutzer abmelden"""
    logout_user()
    session.clear()
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Benutzerprofil anzeigen und bearbeiten"""
    user_data = mongodb.find_one('users', {'username': current_user.username})

    if request.method == 'POST':
        # E-Mail aktualisieren
        email = request.form.get('email', '').strip()

        updates = {'updated_at': datetime.now()}
        if email:
            updates['email'] = email

        # Passwort ändern falls eingegeben
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            if len(new_password) < 8:
                flash('Das neue Passwort muss mindestens 8 Zeichen lang sein.', 'error')
                return render_template('auth/profile.html', user=user_data)
            updates['password_hash'] = generate_password_hash(new_password)

        try:
            mongodb.update_one('users',
                             {'_id': user_data['_id']},
                             {'$set': updates})
            flash('Profil erfolgreich aktualisiert.', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as e:
            logger.error(f"Fehler beim Profil-Update: [Interner Fehler]")
            flash('Ein Fehler ist aufgetreten.', 'error')

    return render_template('auth/profile.html', user=user_data)
