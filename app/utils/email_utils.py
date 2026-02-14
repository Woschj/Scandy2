from flask_mail import Mail, Message
from flask import current_app, has_app_context
import os
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
import base64
import os
import hashlib
try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None
import traceback

mail = None
logger = logging.getLogger(__name__)

def _get_encryption_key():
    """Leitet einen stabilen 32-Byte Key aus SECRET_KEY ab (base64 urlsafe)."""
    try:
        if not has_app_context():
            logger.warning("Kein App-Kontext verfügbar für E-Mail-Verschlüsselung")
            return None
        secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
        key = hashlib.sha256(secret_key.encode()).digest()
        return base64.urlsafe_b64encode(key)
    except Exception as e:
        logger.error(f"Fehler beim Generieren des Verschlüsselungsschlüssels: {str(e)}")
        return None

def _get_fernet():
    """Gibt eine Fernet-Instanz zurück, falls verfügbar, sonst None."""
    try:
        if Fernet is None:
            return None
        key = _get_encryption_key()
        if not key:
            return None
        return Fernet(key)
    except Exception as e:
        logger.error(f"Fehler beim Initialisieren von Fernet: {str(e)}")
        return None

def _encrypt_password(password):
    """Verschlüsselt E-Mail-Passwort. Bevorzugt Fernet, Fallback XOR+Base64.
    Gibt Wert mit Präfix 'fernet:' zurück, wenn Fernet genutzt wird.
    """
    if not password:
        return None
    # Versuche Fernet
    f = _get_fernet()
    if f is not None:
        try:
            token = f.encrypt(password.encode('utf-8')).decode('utf-8')
            return f"fernet:{token}"
        except Exception as e:
            logger.warning(f"Fernet-Verschlüsselung fehlgeschlagen, verwende XOR-Fallback: {str(e)}")
    # Fallback XOR
    try:
        key = _get_encryption_key()
        key_bytes = base64.urlsafe_b64decode(key)
        password_bytes = password.encode('utf-8')
        encrypted = bytearray()
        for i, byte in enumerate(password_bytes):
            encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        return base64.urlsafe_b64encode(bytes(encrypted)).decode()
    except Exception as e:
        logger.error(f"Fehler beim Verschlüsseln des Passworts: {str(e)}")
        return None

def _decrypt_password(encrypted_password):
    """Entschlüsselt E-Mail-Passwort. Unterstützt 'fernet:' Präfix und alten XOR.
    Akzeptiert außerdem rohe Fernet-Tokens (beginnend mit 'gAAAAA').
    """
    if not encrypted_password:
        return None
    # Fernet mit Präfix
    try:
        if isinstance(encrypted_password, str) and encrypted_password.startswith('fernet:'):
            token = encrypted_password.split(':', 1)[1]
            f = _get_fernet()
            if f is None:
                logger.error("Fernet nicht verfügbar für Entschlüsselung")
                return None
            return f.decrypt(token.encode('utf-8')).decode('utf-8')
        # Kompatibilität: rohe Fernet Tokens ohne Präfix
        if isinstance(encrypted_password, str) and encrypted_password.startswith('gAAAAA'):
            f = _get_fernet()
            if f is None:
                logger.error("Fernet nicht verfügbar für Entschlüsselung (raw token)")
                return None
            return f.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Fernet-Entschlüsselung fehlgeschlagen: {str(e)}")
        return None
    # Fallback XOR
    try:
        key = _get_encryption_key()
        if not key:
            logger.warning("Verschlüsselungsschlüssel konnte nicht generiert werden")
            return None
        key_bytes = base64.urlsafe_b64decode(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        return bytes(decrypted).decode('utf-8')
    except Exception as e:
        logger.error(f"Fehler beim Entschlüsseln des Passworts: {str(e)}")
        return None

def get_email_config():
    """Lädt die E-Mail-Konfiguration aus der Datenbank"""
    try:
        from app.models.mongodb_database import MongoDB
        mongodb = MongoDB()
        
        config = {
            'mail_server': 'smtp.gmail.com',
            'mail_port': 587,
            'mail_use_tls': True,
            'mail_username': '',
            'mail_password': '',
            'test_email': '',
            'use_auth': True
        }
        
        # Lade Konfiguration aus der Datenbank
        db_config = mongodb.find_one('email_config', {'_id': 'email_config'})
        if db_config:
            # Überschreibe Standard-Konfiguration mit Datenbank-Werten
            for key, value in db_config.items():
                if key != '_id':  # Überspringe MongoDB _id
                    if key == 'mail_password' and value:
                        # Passwort entschlüsseln, falls es verschlüsselt ist
                        if not value.startswith('$2b$'):
                            config[key] = _decrypt_password(value)
                        else:
                            config[key] = value  # Bereits gehasht (alte Daten)
                    else:
                        config[key] = value
        
        # Konvertiere Typen
        config['mail_port'] = int(config['mail_port'])
        config['mail_use_tls'] = config['mail_use_tls'] == 'true' if isinstance(config['mail_use_tls'], str) else config['mail_use_tls']
        
        # Prüfe ob Konfiguration vollständig ist
        if not config['mail_username'] or not config['mail_password']:
            logger.warning("E-Mail-Konfiguration unvollständig - Benutzername oder Passwort fehlt")
            return None
        
        return config
    except Exception as e:
        logger.error(f"Fehler beim Laden der E-Mail-Konfiguration: {str(e)}")
        return None

def save_email_config(config_data):
    """Speichert die E-Mail-Konfiguration in der Datenbank"""
    try:
        from app.models.mongodb_database import MongoDB
        
        mongodb = MongoDB()
        
        # Absender-E-Mail automatisch aus SMTP-Anmeldedaten setzen (wird in init_mail verwendet)
        config_data['mail_default_sender'] = config_data['mail_username']
        
        # Passwort verschlüsseln, falls vorhanden
        if 'mail_password' in config_data and config_data['mail_password']:
            # Prüfe ob das Passwort bereits verschlüsselt ist
            if not config_data['mail_password'].startswith('$2b$') and not config_data['mail_password'].startswith('fernet:') and not config_data['mail_password'].startswith('gAAAAA'):
                encrypted_password = _encrypt_password(config_data['mail_password'])
                if encrypted_password:
                    config_data['mail_password'] = encrypted_password
                else:
                    logger.error("Fehler beim Verschlüsseln des E-Mail-Passworts")
                    return False
        
        # Konfiguration speichern oder aktualisieren
        # Passwort wird jetzt verschlüsselt gespeichert
        mongodb.update_one(
            'email_config',
            {'_id': 'email_config'},
            config_data,
            upsert=True
        )
        
        # E-Mail-System wird beim nächsten Neustart neu initialisiert
        logger.info("E-Mail-Konfiguration gespeichert. Neustart erforderlich für Aktivierung.")
        
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der E-Mail-Konfiguration: {str(e)}")
        return False

def test_email_config(config_data):
    """Testet die E-Mail-Konfiguration"""
    try:
        # Prüfe ob Konfiguration vollständig ist
        if not config_data.get('mail_username') or not config_data.get('mail_password'):
            logger.error("E-Mail-Konfiguration unvollständig - Benutzername oder Passwort fehlt")
            return False, "E-Mail-Konfiguration unvollständig - Benutzername oder Passwort fehlt"
        
        # Passwort entschlüsseln falls verschlüsselt
        password = config_data['mail_password']
        if password.startswith('gAAAAA'):
            try:
                decrypted_password = _decrypt_password(password)
                if decrypted_password:
                    password = decrypted_password
                else:
                    logger.warning("Passwort konnte nicht entschlüsselt werden")
                    return False, "Passwort konnte nicht entschlüsselt werden"
            except Exception as e:
                logger.error(f"Fehler beim Entschlüsseln des Passworts: {str(e)}")
                return False, f"Fehler beim Entschlüsseln des Passworts: {str(e)}"
        
        # Teste SMTP-Verbindung direkt
        import smtplib
        from email.mime.text import MIMEText
        
        logger.info("Teste E-Mail-Konfiguration")
        
        # SMTP-Verbindung aufbauen
        if config_data['mail_use_tls'] and config_data['mail_port'] == 465:
            server = smtplib.SMTP_SSL(config_data['mail_server'], config_data['mail_port'])
        else:
            server = smtplib.SMTP(config_data['mail_server'], config_data['mail_port'])
        
        # EHLO senden
        server.ehlo()
        
        # STARTTLS aktivieren falls konfiguriert
        if config_data['mail_use_tls'] and config_data['mail_port'] == 587:
            server.starttls()
            server.ehlo()
        
        # Authentifizierung testen
        server.login(config_data['mail_username'], password)
        
        # Test-E-Mail senden
        test_msg = MIMEText("Dies ist eine Test-E-Mail von Scandy.")
        test_msg['Subject'] = 'Scandy E-Mail-Test'
        test_msg['From'] = config_data['mail_username']
        test_msg['To'] = config_data.get('test_email', config_data['mail_username'])
        
        server.send_message(test_msg)
        server.quit()
        
        logger.info("E-Mail-Konfiguration erfolgreich getestet")
        return True, "E-Mail-Konfiguration funktioniert"
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP-Authentifizierungsfehler: {str(e)}")
        return False, f"Authentifizierungsfehler: {str(e)}"
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP-Verbindungsfehler: {str(e)}")
        return False, f"Verbindungsfehler: {str(e)}"
    except smtplib.SMTPException as e:
        logger.error(f"SMTP-Fehler: {str(e)}")
        return False, f"SMTP-Fehler: {str(e)}"
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim E-Mail-Test: {str(e)}")
        return False, f"Unerwarteter Fehler: {str(e)}"

def init_mail(app):
    global mail
    
    # Prüfe ob bereits initialisiert
    if mail is not None:
        return mail
    
    try:
        # Lade Konfiguration aus der Datenbank
        config = get_email_config()
        
        if config:
            # Verwende Datenbank-Konfiguration
            app.config['MAIL_SERVER'] = config['mail_server']
            app.config['MAIL_PORT'] = config['mail_port']
            app.config['MAIL_USE_TLS'] = config['mail_use_tls']
            app.config['MAIL_USE_SSL'] = not config['mail_use_tls'] and int(config['mail_port']) == 465
            
            # Prüfe ob Server Authentifizierung unterstützt
            # Verwende use_auth Einstellung, falls vorhanden, sonst prüfe Server-Capabilities
            if 'use_auth' in config:
                auth_required = config['use_auth']
            else:
                auth_required = _check_auth_required(config['mail_server'], config['mail_port'], config['mail_use_tls'])
            
            if auth_required:
                # Server benötigt Authentifizierung
                if not config['mail_username'] or not config['mail_password']:
                    app.logger.error("E-Mail-Server benötigt Authentifizierung, aber keine Anmeldedaten angegeben")
                    mail = None
                    return None
                
                app.config['MAIL_USERNAME'] = config['mail_username']
                app.config['MAIL_PASSWORD'] = config['mail_password']
                app.config['MAIL_DEFAULT_SENDER'] = config['mail_username']  # Absender = SMTP-Username
            else:
                # Server ohne Authentifizierung
                if not config.get('mail_username'):
                    app.logger.error("Für Server ohne Authentifizierung ist eine Absender-E-Mail-Adresse erforderlich")
                    mail = None
                    return None
                    
                app.config['MAIL_USERNAME'] = config['mail_username']  # Wird als Absender verwendet
                app.config['MAIL_PASSWORD'] = ''  # Kein Passwort für Server ohne Auth
                app.config['MAIL_DEFAULT_SENDER'] = config['mail_username']
            
            # Zusätzliche Flask-Mail Konfiguration für bessere Kompatibilität
            app.config['MAIL_ASCII_ATTACHMENTS'] = False
            app.config['MAIL_SUPPRESS_SEND'] = False
            
            try:
                mail = Mail(app)
                app.logger.info("E-Mail-System mit Datenbank-Konfiguration initialisiert")
                app.logger.info(f"SMTP-Server: {config['mail_server']}:{config['mail_port']}")
                app.logger.info(f"TLS: {config['mail_use_tls']}, SSL: {app.config['MAIL_USE_SSL']}")
                return mail
            except Exception as e:
                app.logger.error(f"Fehler bei E-Mail-Initialisierung: {str(e)}")
                mail = None
                return None
        else:
            # Keine E-Mail-Konfiguration verfügbar
            app.logger.warning("Keine E-Mail-Konfiguration verfügbar - E-Mail-System wird nicht initialisiert")
            mail = None
            return None
    except Exception as e:
        app.logger.error(f"Fehler bei E-Mail-Initialisierung: {str(e)}")
        mail = None
        return None


def _check_auth_required(server, port, use_tls):
    """Prüft ob ein SMTP-Server Authentifizierung benötigt"""
    try:
        import smtplib
        
        # Verbindung testen
        if use_tls and port == 465:
            smtp_server = smtplib.SMTP_SSL(server, port)
        else:
            smtp_server = smtplib.SMTP(server, port)
        
        # EHLO senden
        capabilities = smtp_server.ehlo()
        
        # STARTTLS aktivieren falls konfiguriert
        if use_tls and port == 587:
            try:
                smtp_server.starttls()
                capabilities = smtp_server.ehlo()
            except Exception as e:
                logger.warning(f"STARTTLS nicht verfügbar: {str(e)}")
                pass  # STARTTLS nicht verfügbar
        
        # Prüfe AUTH in Capabilities (korrigiert für btz-koeln.net)
        auth_supported = False
        if hasattr(smtp_server, 'esmtp_features') and smtp_server.esmtp_features:
            auth_supported = 'auth' in smtp_server.esmtp_features
        
        # Fallback: Prüfe in Capabilities-Strings
        if not auth_supported and capabilities and len(capabilities) > 1:
            for cap in capabilities[1]:
                if isinstance(cap, bytes):
                    try:
                        cap_str = cap.decode('utf-8', errors='ignore')
                    except UnicodeDecodeError:
                        cap_str = cap.decode('latin-1', errors='ignore')
                else:
                    cap_str = str(cap)
                
                if 'auth' in cap_str.lower():
                    auth_supported = True
                    break
        
        smtp_server.quit()
        return auth_supported
        
    except Exception as e:
        logger.warning(f"Konnte Auth-Status für {server}:{port} nicht prüfen: {str(e)}")
        # Bei Fehlern annehmen, dass Auth erforderlich ist (sicherer Fallback)
        return True





def _send_email_direct(recipient, subject, body, attachments=None, mail_type="default"):
    """Sendet E-Mails direkt über SMTP ohne Speicherung im 'Gesendet'-Ordner und loggt alle Details."""
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        import smtplib

        # Lade E-Mail-Konfiguration
        config = get_email_config()
        if not config:
            logger.error("[MAIL] E-Mail-Konfiguration nicht verfügbar")
            return False

        # Logge alle Parameter vor dem Versand
        logger.info("[MAIL] Versand wird vorbereitet")

        # Erstelle E-Mail-Nachricht
        msg = MIMEMultipart()
        msg['From'] = config['mail_username']
        msg['To'] = recipient

        # Subject korrekt als UTF-8 kodieren
        from email.header import Header
        msg['Subject'] = Header(subject, 'utf-8')

        # Message-ID hinzufügen (RFC 5322 Compliance für Gmail)
        import uuid
        import socket
        from email.utils import formatdate
        hostname = socket.gethostname()
        message_id = f"<{uuid.uuid4()}@{hostname}>"
        msg['Message-ID'] = message_id
        msg['Date'] = formatdate(localtime=True)

        # Spezielle Header um Speicherung im "Gesendet"-Ordner zu verhindern
        msg['X-Auto-Response-Suppress'] = 'All'
        msg['Precedence'] = 'bulk'
        msg['X-Mailer'] = 'Scandy-System'

        # Body hinzufügen - explizit UTF-8 kodieren
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Anhänge hinzufügen (falls vorhanden)
        if attachments:
            for attachment in attachments:
                with open(attachment['path'], 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 
                                   f'attachment; filename= {attachment["filename"]}')
                    msg.attach(part)

        # SMTP-Verbindung aufbauen
        if config['mail_use_tls'] and config['mail_port'] == 465:
            server = smtplib.SMTP_SSL(config['mail_server'], config['mail_port'])
        else:
            server = smtplib.SMTP(config['mail_server'], config['mail_port'])

        # STARTTLS aktivieren falls konfiguriert
        if config['mail_use_tls'] and config['mail_port'] == 587:
            server.starttls()

        # UTF-8 für SMTP-Verbindung aktivieren
        server.ehlo()
        if hasattr(server, 'esmtp_features') and server.esmtp_features:
            if '8bitmime' in server.esmtp_features:
                logger.info(f"[MAIL][{mail_type}] 8BITMIME wird unterstützt - UTF-8 E-Mails möglich")
            else:
                logger.warning(f"[MAIL][{mail_type}] 8BITMIME nicht unterstützt - E-Mails werden als 7-bit gesendet")

        # Authentifizierung (falls erforderlich)
        if config.get('use_auth', True) and config['mail_username'] and config['mail_password']:
            server.login(config['mail_username'], config['mail_password'])

        # E-Mail senden - explizit als UTF-8 kodieren
        text = msg.as_string()
        if isinstance(text, str):
            text = text.encode('utf-8')
        server.sendmail(config['mail_username'], recipient, text)
        server.quit()

        logger.info("[MAIL] E-Mail erfolgreich versendet")
        return True

    except Exception as e:
        logger.error("[MAIL] Fehler beim E-Mail-Versand")
        return False

def _send_email_direct_html(recipient, subject, html_content=None, text_content=None, attachments=None, mail_type="default"):
    """Sendet HTML-E-Mails direkt über SMTP mit HTML- und Text-Inhalten"""
    try:
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        import smtplib

        # Lade E-Mail-Konfiguration
        config = get_email_config()
        if not config:
            logger.error("[MAIL] E-Mail-Konfiguration nicht verfügbar")
            return False

        # Logge alle Parameter vor dem Versand
        logger.info("[MAIL] HTML-E-Mail Versand wird vorbereitet")

        # Erstelle E-Mail-Nachricht
        msg = MIMEMultipart('alternative')
        msg['From'] = config['mail_username']
        msg['To'] = recipient

        # Subject korrekt als UTF-8 kodieren
        from email.header import Header
        msg['Subject'] = Header(subject, 'utf-8')

        # Message-ID hinzufügen (RFC 5322 Compliance für Gmail)
        import uuid
        import socket
        from email.utils import formatdate
        hostname = socket.gethostname()
        message_id = f"<{uuid.uuid4()}@{hostname}>"
        msg['Message-ID'] = message_id
        msg['Date'] = formatdate(localtime=True)

        # Spezielle Header um Speicherung im "Gesendet"-Ordner zu verhindern
        msg['X-Auto-Response-Suppress'] = 'All'
        msg['Precedence'] = 'bulk'
        msg['X-Mailer'] = 'Scandy-System'

        # Text-Version hinzufügen (falls vorhanden)
        if text_content:
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(text_part)

        # HTML-Version hinzufügen (falls vorhanden)
        if html_content:
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

        # Anhänge hinzufügen (falls vorhanden)
        if attachments:
            for attachment in attachments:
                with open(attachment['path'], 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', 
                                   f'attachment; filename= {attachment["filename"]}')
                    msg.attach(part)

        # SMTP-Verbindung aufbauen
        if config['mail_use_tls'] and config['mail_port'] == 465:
            server = smtplib.SMTP_SSL(config['mail_server'], config['mail_port'])
        else:
            server = smtplib.SMTP(config['mail_server'], config['mail_port'])

        # STARTTLS aktivieren falls konfiguriert
        if config['mail_use_tls'] and config['mail_port'] == 587:
            server.starttls()

        # UTF-8 für SMTP-Verbindung aktivieren
        server.ehlo()
        if hasattr(server, 'esmtp_features') and server.esmtp_features:
            if '8bitmime' in server.esmtp_features:
                logger.info(f"[MAIL][{mail_type}] 8BITMIME wird unterstützt - UTF-8 E-Mails möglich")
            else:
                logger.warning(f"[MAIL][{mail_type}] 8BITMIME nicht unterstützt - E-Mails werden als 7-bit gesendet")

        # Authentifizierung (falls erforderlich)
        if config.get('use_auth', True) and config['mail_username'] and config['mail_password']:
            server.login(config['mail_username'], config['mail_password'])

        # E-Mail senden - explizit als UTF-8 kodieren
        text = msg.as_string()
        if isinstance(text, str):
            text = text.encode('utf-8')
        server.sendmail(config['mail_username'], recipient, text)
        server.quit()

        logger.info("[MAIL] HTML-E-Mail erfolgreich versendet")
        return True

    except Exception as e:
        logger.error("[MAIL] Fehler beim HTML-E-Mail-Versand")
        return False

def ensure_app_context(func):
    def wrapper(*args, **kwargs):
        if has_app_context():
            return func(*args, **kwargs)
        else:
            from app import app
            with app.app_context():
                return func(*args, **kwargs)
    return wrapper

def send_email(to_email, subject, html_content=None, text_content=None, from_name=None):
    """Sendet E-Mails mit HTML- und Text-Inhalten über _send_email_direct"""
    try:
        # Prüfe ob E-Mail-Konfiguration verfügbar ist
        config = get_email_config()
        if not config:
            logger.warning(f"[MAIL][auftrag] E-Mail-Konfiguration nicht verfügbar - E-Mail wird nicht versendet")
            logger.info(f"[MAIL][auftrag] Empfänger: {to_email}, Betreff: {subject}")
            return False
        
        # Verwende direkte SMTP-Verbindung mit detailliertem Logging
        # Sende als HTML-E-Mail mit beiden Inhalten
        success = _send_email_direct_html(to_email, subject, html_content, text_content, mail_type="auftrag")
        
        if success:
            logger.info(f"[MAIL][auftrag] E-Mail erfolgreich versendet: Empfänger={to_email}, Betreff={subject}, From={from_name}")
        else:
            logger.error(f"[MAIL][auftrag] E-Mail NICHT versendet: Empfänger={to_email}, Betreff={subject}, From={from_name}")
        
        return success
        
    except Exception as e:
        logger.error(f"[MAIL][auftrag] Fehler beim Senden der E-Mail: {str(e)}\nEmpfänger={to_email}, Betreff={subject}, From={from_name}\n{traceback.format_exc()}")
        return False

@ensure_app_context
def send_auftrag_confirmation_email(ticket_data, auftrag_details, recipient_email):
    """Sendet eine Bestätigungs-E-Mail für einen neuen Auftrag (unterstützt Admin-Vorlagen)."""
    try:
        # Vorlage bevorzugt verwenden
        try:
            from app.services.admin_email_templates_service import AdminEmailTemplatesService
            rendered = AdminEmailTemplatesService.render_template_by_key('auftrag_confirmation', {
                'ticket': ticket_data,
                'auftrag': auftrag_details,
            })
            default_subject = f"Auftragsbestätigung - {ticket_data.get('ticket_number', 'Neuer Auftrag')}"
            if rendered and (rendered.get('html_content') or rendered.get('text_content')):
                return send_email(
                    to_email=recipient_email,
                    subject=rendered.get('subject') or default_subject,
                    html_content=rendered.get('html_content'),
                    text_content=rendered.get('text_content'),
                    from_name="BTZ Köln - Auftragssystem"
                )
        except Exception as _tpl_err:
            logger.warning(f"E-Mail-Vorlage 'auftrag_confirmation' nicht verfügbar/nutzbar: {_tpl_err}")

        # Fallback: bestehendes statisches Template
        email_config = get_email_config()
        if not email_config:
            logger.error("E-Mail-Konfiguration nicht verfügbar")
            return False
        
        # E-Mail-Inhalt erstellen
        subject = f"Auftragsbestätigung - {ticket_data.get('ticket_number', 'Neuer Auftrag')}"
        
        # HTML-E-Mail-Template
        html_content = f"""
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Auftragsbestätigung</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #ffffff; padding: 30px; border: 1px solid #dee2e6; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; font-size: 14px; color: #6c757d; }}
                .success-icon {{ color: #28a745; font-size: 48px; margin-bottom: 20px; }}
                .ticket-number {{ background-color: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0; }}
                .ticket-number .number {{ font-size: 24px; font-weight: bold; color: #007bff; font-family: monospace; }}
                .details {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .details h3 {{ margin-top: 0; color: #495057; }}
                .details table {{ width: 100%; border-collapse: collapse; }}
                .details td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
                .details td:first-child {{ font-weight: bold; width: 30%; }}
                .priority-badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
                .priority-normal {{ background-color: #007bff; color: white; }}
                .priority-hoch {{ background-color: #dc3545; color: white; }}
                .priority-niedrig {{ background-color: #6c757d; color: white; }}
                .next-steps {{ background-color: #d1ecf1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .next-steps h3 {{ margin-top: 0; color: #0c5460; }}
                .next-steps ul {{ margin: 0; padding-left: 20px; }}
                .next-steps li {{ margin-bottom: 8px; }}
                .contact-info {{ background-color: #e2e3e5; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .contact-info h3 {{ margin-top: 0; color: #383d41; }}
                .btn {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .btn:hover {{ background-color: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">✓</div>
                    <h1 style="margin: 0; color: #28a745;">Auftrag erfolgreich erstellt!</h1>
                    <p style="margin: 10px 0 0 0; color: #6c757d;">Vielen Dank für Ihren Auftrag</p>
                </div>
                
                <div class="content">
                    <div class="ticket-number">
                        <p style="margin: 0 0 10px 0; font-weight: bold;">Ihre Auftragsnummer:</p>
                        <div class="number">{ticket_data.get('ticket_number', 'N/A')}</div>
                    </div>
                    
                    <div class="details">
                        <h3>Auftragsdetails</h3>
                        <table>
                            <tr>
                                <td>Titel:</td>
                                <td>{ticket_data.get('title', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td>Kategorie:</td>
                                <td>{ticket_data.get('category', 'Nicht angegeben')}</td>
                            </tr>
                            <tr>
                                <td>Priorität:</td>
                                <td>
                                    <span class="priority-badge priority-{ticket_data.get('priority', 'normal')}">
                                        {ticket_data.get('priority', 'normal').title()}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <td>Auftraggeber:</td>
                                <td>{auftrag_details.get('auftraggeber_name', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td>Bereich:</td>
                                <td>{auftrag_details.get('bereich', 'Nicht angegeben')}</td>
                            </tr>
                            <tr>
                                <td>Erstellt am:</td>
                                <td>{ticket_data.get('created_at', 'N/A')}</td>
                            </tr>
                        </table>
                        
                        <h4 style="margin-top: 20px;">Beschreibung:</h4>
                        <p style="background-color: white; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;">
                            {ticket_data.get('description', 'Keine Beschreibung vorhanden')}
                        </p>
                    </div>
                    
                    <div class="next-steps">
                        <h3>Nächste Schritte</h3>
                        <ul>
                            <li>Wir haben Ihren Auftrag in unserem System erfasst</li>
                            <li>Wir werden die Details besprechen und einen Zeitplan erstellen</li>
                            <li>Sie erhalten Updates zum Fortschritt Ihres Auftrags</li>
                        </ul>
                    </div>
                    
                    <div class="contact-info">
                        <h3>Kontakt</h3>
                        <p style="margin-bottom: 10px;">Bei Fragen erreichen Sie uns über das Scandy-System.</p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px;">
                        <a href="/tickets/auftrag-neu" class="btn">Neuen Auftrag erstellen</a>
                        <a href="/" class="btn" style="background-color: #6c757d;">Zur Startseite</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht auf diese E-Mail.</p>
                    <p>Scandy - Ihr Auftragssystem</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain-Text-Version
        text_content = f"""
Auftragsbestätigung - {ticket_data.get('ticket_number', 'Neuer Auftrag')}

Vielen Dank für Ihren Auftrag!

Ihre Auftragsnummer: {ticket_data.get('ticket_number', 'N/A')}

AUFTRAGSDETAILS:
- Titel: {ticket_data.get('title', 'N/A')}
- Kategorie: {ticket_data.get('category', 'Nicht angegeben')}
- Priorität: {ticket_data.get('priority', 'normal').title()}
- Auftraggeber: {auftrag_details.get('auftraggeber_name', 'N/A')}
- Bereich: {auftrag_details.get('bereich', 'Nicht angegeben')}
- Erstellt am: {ticket_data.get('created_at', 'N/A')}

Beschreibung:
{ticket_data.get('description', 'Keine Beschreibung vorhanden')}

NÄCHSTE SCHRITTE:
- Wir haben Ihren Auftrag in unserem System erfasst
- Wir werden die Details besprechen und einen Zeitplan erstellen
- Sie erhalten Updates zum Fortschritt Ihres Auftrags

KONTAKT:
Bei Fragen erreichen Sie uns über das Scandy-System.

Scandy - Ihr Auftragssystem
        """
        
        # E-Mail senden
        result = send_email(
            to_email=recipient_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            from_name="BTZ Köln - Auftragssystem"
        )
        if result:
            logger.info(f"Bestätigungs-E-Mail für Auftrag {ticket_data.get('ticket_number')} erfolgreich an {recipient_email} versendet.")
        else:
            logger.error(f"Bestätigungs-E-Mail für Auftrag {ticket_data.get('ticket_number')} an {recipient_email} NICHT versendet!")
        return result
        
    except Exception as e:
        logger.error(f"Fehler beim Senden der Auftragsbestätigungs-E-Mail: {str(e)}")
        return False 

@ensure_app_context
def send_password_mail(recipient, password):
    subject = 'Ihr Zugang zu Scandy'
    body = f"Willkommen bei Scandy!\n\nIhr initiales Passwort lautet: {password}\nBitte ändern Sie es nach dem ersten Login.\n\nMit freundlichen Grüßen\nIhr Scandy-Team"
    try:
        # Verwende direkte SMTP-Verbindung um "Gesendet"-Ordner zu vermeiden
        success = _send_email_direct(recipient, subject, body, mail_type="password")
        if success:
            logger.info(f"Passwort-E-Mail erfolgreich an {recipient} gesendet (ohne Speicherung im Gesendet-Ordner)")
        return success
    except Exception as e:
        logger.error(f"Fehler beim Versenden der Passwort-E-Mail: {str(e)}")
        return False

@ensure_app_context
def send_password_reset_mail(recipient, password=None, reset_link=None):
    """Sendet Passwort-Reset-E-Mail"""
    try:
        subject = 'Scandy Passwort-Reset'
        
        # Prüfe ob E-Mail-Konfiguration verfügbar ist
        config = get_email_config()
        if not config:
            logger.error(f"[MAIL][reset] E-Mail-Konfiguration nicht verfügbar - Passwort-Reset-E-Mail kann nicht gesendet werden an {recipient}")
            return False
        
        # Prüfe ob alle erforderlichen E-Mail-Einstellungen vorhanden sind
        required_settings = ['mail_server', 'mail_port', 'mail_username', 'mail_password']
        for setting in required_settings:
            if not config.get(setting):
                logger.error(f"[MAIL][reset] Fehlende E-Mail-Einstellung: {setting}")
                return False
        
        logger.info("[MAIL][reset] Passwort-Reset-E-Mail wird vorbereitet")
        
        # Zusätzliche Kontextdaten ermitteln (z. B. Benutzername) für bessere Template-Kompatibilität
        username = None
        try:
            from app.models.mongodb_database import mongodb as _mdb
            user_row = _mdb.find_one('users', {'email': {'$regex': f'^{recipient}$', '$options': 'i'}})
            if user_row:
                username = user_row.get('username') or user_row.get('email')
        except Exception:
            username = None

        # Versuch über Admin-Vorlage (Key: password_reset)
        try:
            from app.services.admin_email_templates_service import AdminEmailTemplatesService
            context = {
                'reset_link': reset_link,
                'password': password,
                'recipient': recipient,
                'username': username,
                # Synonyme für bessere Abwärtskompatibilität mit älteren/angepassten Templates
                'link': reset_link,
                'new_password': password,
                'passwort': password,
                'pwd': password,
                'server_url': (current_app.config.get('BASE_URL') or '').rstrip('/'),
                'base_url': (current_app.config.get('BASE_URL') or '').rstrip('/'),
            }
            rendered = AdminEmailTemplatesService.render_template_by_key('password_reset', context)
            if rendered and (rendered.get('html_content') or rendered.get('text_content')):
                subj = rendered.get('subject') or subject
                logger.info(f"[MAIL][reset] Verwende E-Mail-Vorlage für Passwort-Reset")
                success = _send_email_direct_html(recipient, subj, rendered.get('html_content'), rendered.get('text_content'), mail_type="reset")
                if success:
                    logger.info(f"[MAIL][reset] Passwort-Reset-E-Mail erfolgreich an {recipient} gesendet (Vorlage)")
                else:
                    logger.error(f"[MAIL][reset] Passwort-Reset-E-Mail fehlgeschlagen (Vorlage)")
                return success
        except Exception as _tpl_err:
            logger.warning(f"[MAIL][reset] E-Mail-Vorlage 'password_reset' nicht verfügbar/nutzbar: {_tpl_err}")

        # Fallback: HTML + Textkörper mit klickbarem Link/Passwort
        logger.info(f"[MAIL][reset] Verwende Fallback-HTML/Text für Passwort-Reset")
        base_url = (current_app.config.get('BASE_URL') or '').rstrip('/')
        html_body = ""
        text_body = ""
        # Vorbereitete HTML/Text-Snippets, um Backslashes in f-String-Expressions zu vermeiden
        link_html = (f'<p>Zur Startseite: <a href="{base_url}" style="color:#1d4ed8">{base_url}</a></p>'
                     if base_url else '')
        login_html = (f'<p>Zur Anmeldung: <a href="{base_url}" style="color:#1d4ed8">{base_url}</a></p>'
                      if base_url else '')
        start_text = (f'Startseite: {base_url}\n\n' if base_url else '')
        login_text = (f'Anmeldung: {base_url}\n\n' if base_url else '')
        if reset_link:
            html_body = f"""
            <div style=\"font-family:Arial,sans-serif;line-height:1.5;color:#111\">
              <p>Sie haben einen Passwort-Reset angefordert.</p>
              <p>Bitte klicken Sie auf den folgenden Link, um Ihr Passwort zurückzusetzen:</p>
              <p><a href=\"{reset_link}\" style=\"color:#1d4ed8\">Passwort zurücksetzen</a></p>
              <p>Oder kopieren Sie diesen Link in die Adresszeile Ihres Browsers:<br>
                 <span style=\"font-family:monospace;color:#374151\">{reset_link}</span>
              </p>
              {link_html}
              <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
            </div>
            """
            text_body = f"Sie haben einen Passwort-Reset angefordert.\n\nLink zum Zurücksetzen: {reset_link}\n\n{start_text}Mit freundlichen Grüßen\nIhr Scandy-Team"
        elif password:
            html_body = f"""
            <div style=\"font-family:Arial,sans-serif;line-height:1.5;color:#111\">
              <p>Ihr neues Passwort lautet:</p>
              <p><strong style=\"font-family:monospace\">{password}</strong></p>
              {login_html}
              <p>Bitte ändern Sie es nach dem Login.</p>
              <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
            </div>
            """
            text_body = f"Ihr neues Passwort lautet: {password}\n\nBitte ändern Sie es nach dem Login.\n\n{login_text}Mit freundlichen Grüßen\nIhr Scandy-Team"
        else:
            html_body = "<p>Es ist ein Fehler aufgetreten. Bitte kontaktieren Sie den Administrator.</p>"
            text_body = "Es ist ein Fehler aufgetreten. Bitte kontaktieren Sie den Administrator."

        try:
            # Verwende HTML-Versand mit Text-Alternative
            success = _send_email_direct_html(recipient, subject, html_body, text_body, mail_type="reset")
            if success:
                logger.info(f"[MAIL][reset] Passwort-Reset-E-Mail erfolgreich an {recipient} gesendet (Fallback HTML)")
            else:
                logger.error(f"[MAIL][reset] Passwort-Reset-E-Mail fehlgeschlagen (Fallback HTML)")
            return success
        except Exception as e:
            logger.error(f"[MAIL][reset] Fehler beim Versenden der Passwort-Reset-E-Mail (Fallback): {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"[MAIL][reset] Unerwarteter Fehler in send_password_reset_mail: {str(e)}")
        return False

@ensure_app_context
def send_backup_mail(recipient, backup_path):
    """Sendet eine E-Mail mit Backup-Anhang"""
    try:
        subject = f'Scandy Backup - {datetime.now().strftime("%d.%m.%Y %H:%M")}'
        body = f"""Hallo,

ein neues Backup von Scandy wurde erstellt.

Backup-Datei: {backup_path}
Erstellt am: {datetime.now().strftime("%d.%m.%Y %H:%M")}

Das Backup ist als Anhang beigefügt.

Mit freundlichen Grüßen
Ihr Scandy-System"""

        # Backup als Attachment vorbereiten
        attachments = None
        if backup_path and os.path.exists(backup_path):
            attachments = [{
                'path': backup_path,
                'filename': os.path.basename(backup_path)
            }]

        # Verwende direkte SMTP-Verbindung mit detailliertem Logging
        success = _send_email_direct(recipient, subject, body, attachments=attachments, mail_type="backup")
        
        if success:
            logger.info(f"[MAIL][backup] Backup-E-Mail erfolgreich versendet: Empfänger={recipient}, Backup={backup_path}")
        else:
            logger.error(f"[MAIL][backup] Backup-E-Mail NICHT versendet: Empfänger={recipient}, Backup={backup_path}")
        
        return success
        
    except Exception as e:
        logger.error(f"[MAIL][backup] Fehler beim Senden der Backup-E-Mail: {str(e)}\nEmpfänger={recipient}, Backup={backup_path}\n{traceback.format_exc()}")
        return False

@ensure_app_context
def send_weekly_backup_mail(recipient, archive_path):
    """Sendet eine E-Mail mit wöchentlichem Backup-Archiv"""
    try:
        subject = f'Scandy Wöchentliches Backup-Archiv - {datetime.now().strftime("%d.%m.%Y")}'
        body = f"""Hallo,

das wöchentliche Backup-Archiv von Scandy wurde erstellt.

Archiv-Datei: {archive_path}
Erstellt am: {datetime.now().strftime("%d.%m.%Y %H:%M")}

Das Archiv ist als Anhang beigefügt.

Mit freundlichen Grüßen
Ihr Scandy-System"""

        # Archiv als Attachment vorbereiten
        attachments = None
        if archive_path and os.path.exists(archive_path):
            attachments = [{
                'path': archive_path,
                'filename': os.path.basename(archive_path)
            }]

        # Verwende direkte SMTP-Verbindung mit detailliertem Logging
        success = _send_email_direct(recipient, subject, body, attachments=attachments, mail_type="weekly_backup")
        
        if success:
            logger.info(f"[MAIL][weekly_backup] Wöchentliches Backup-Archiv erfolgreich versendet: Empfänger={recipient}, Archiv={archive_path}")
        else:
            logger.error(f"[MAIL][weekly_backup] Wöchentliches Backup-Archiv NICHT versendet: Empfänger={recipient}, Archiv={archive_path}")
        
        return success
        
    except Exception as e:
        logger.error(f"[MAIL][weekly_backup] Fehler beim Senden des wöchentlichen Backup-Archivs: {str(e)}\nEmpfänger={recipient}, Archiv={archive_path}\n{traceback.format_exc()}")
        return False

def diagnose_smtp_connection(config_data):
    """Diagnostiziert die SMTP-Verbindung und gibt detaillierte Informationen zurück"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        results = {
            'success': False,
            'steps': [],
            'error': None,
            'capabilities': {},
            'auth_methods': []
        }
        
        # Schritt 1: SMTP-Verbindung aufbauen
        results['steps'].append("Verbindung zu SMTP-Server wird aufgebaut...")
        
        if config_data['mail_use_tls'] and config_data['mail_port'] == 465:
            server = smtplib.SMTP_SSL(config_data['mail_server'], config_data['mail_port'])
            results['steps'].append(f"SSL-Verbindung zu {config_data['mail_server']}:{config_data['mail_port']} aufgebaut")
        else:
            server = smtplib.SMTP(config_data['mail_server'], config_data['mail_port'])
            results['steps'].append(f"Verbindung zu {config_data['mail_server']}:{config_data['mail_port']} aufgebaut")
        
        # Schritt 2: EHLO senden
        results['steps'].append("EHLO wird gesendet...")
        capabilities = server.ehlo()
        results['steps'].append(f"EHLO erfolgreich: {capabilities[0] if capabilities else 'Keine Antwort'}")
        
        # Schritt 3: Server-Capabilities analysieren
        if hasattr(server, 'esmtp_features') and server.esmtp_features:
            results['capabilities'] = dict(server.esmtp_features)
            results['steps'].append(f"Server-Capabilities: {list(server.esmtp_features.keys())}")
            
            # AUTH-Methoden extrahieren
            if 'auth' in server.esmtp_features:
                auth_methods = server.esmtp_features['auth'].decode() if isinstance(server.esmtp_features['auth'], bytes) else str(server.esmtp_features['auth'])
                results['auth_methods'] = auth_methods.split()
                results['steps'].append(f"Unterstützte AUTH-Methoden: {results['auth_methods']}")
        
        # Schritt 4: STARTTLS testen (falls konfiguriert)
        if config_data['mail_use_tls'] and config_data['mail_port'] == 587:
            results['steps'].append("STARTTLS wird aktiviert...")
            try:
                server.starttls()
                results['steps'].append("STARTTLS erfolgreich aktiviert")
                
                # Neue EHLO nach TLS
                capabilities_after = server.ehlo()
                results['steps'].append(f"EHLO nach TLS: {capabilities_after[0] if capabilities_after else 'Keine Antwort'}")
                
                if hasattr(server, 'esmtp_features') and server.esmtp_features:
                    results['capabilities_after_tls'] = dict(server.esmtp_features)
                    results['steps'].append(f"Capabilities nach TLS: {list(server.esmtp_features.keys())}")
                    
            except Exception as e:
                results['steps'].append(f"STARTTLS fehlgeschlagen: {str(e)}")
                results['error'] = f"STARTTLS-Fehler: {str(e)}"
        
        # Schritt 5: Authentifizierung testen (falls Anmeldedaten vorhanden)
        if config_data.get('mail_username') and config_data.get('mail_password'):
            results['steps'].append("Authentifizierung wird getestet...")
            try:
                server.login(config_data['mail_username'], config_data['mail_password'])
                results['steps'].append("Authentifizierung erfolgreich")
                results['auth_success'] = True
            except Exception as e:
                results['steps'].append(f"Authentifizierung fehlgeschlagen: {str(e)}")
                results['auth_success'] = False
                results['error'] = f"Auth-Fehler: {str(e)}"
        else:
            results['steps'].append("Keine Anmeldedaten vorhanden - Authentifizierung übersprungen")
            results['auth_success'] = None
        
        # Schritt 6: Test-E-Mail senden
        if results.get('auth_success') is not False:  # Nur wenn Auth nicht fehlgeschlagen ist
            results['steps'].append("Test-E-Mail wird gesendet...")
            try:
                test_msg = MIMEText("Dies ist eine Test-E-Mail von Scandy zur SMTP-Diagnose.")
                test_msg['Subject'] = 'Scandy SMTP-Diagnose Test'
                test_msg['From'] = config_data['mail_username']
                test_msg['To'] = config_data.get('test_email', config_data['mail_username'])
                
                server.send_message(test_msg)
                results['steps'].append("Test-E-Mail erfolgreich gesendet")
                results['test_email_success'] = True
            except Exception as e:
                results['steps'].append(f"Test-E-Mail fehlgeschlagen: {str(e)}")
                results['test_email_success'] = False
                results['error'] = f"Test-E-Mail-Fehler: {str(e)}"
        
        server.quit()
        results['steps'].append("SMTP-Verbindung geschlossen")
        
        # Gesamterfolg bestimmen
        if results.get('test_email_success') or results.get('auth_success') is not False:
            results['success'] = True
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'steps': [f"Fehler bei der Diagnose: {str(e)}"],
            'error': 'Ein interner Fehler ist aufgetreten.',
            'capabilities': {},
            'auth_methods': []
        }

def reload_email_config(app):
    """Lädt die E-Mail-Konfiguration neu und initialisiert das E-Mail-System"""
    try:
        # E-Mail-System neu initialisieren
        init_mail(app)
        logger.info("E-Mail-Konfiguration erfolgreich neu geladen")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Neuladen der E-Mail-Konfiguration: {str(e)}")
        return False

def debug_email_status():
    """Debug-Funktion um den E-Mail-Status zu prüfen"""
    try:
        config = get_email_config()
        if not config:
            return {
                'status': 'error',
                'message': 'Keine E-Mail-Konfiguration gefunden',
                'details': 'Bitte konfigurieren Sie das E-Mail-System im Admin-Bereich'
            }
        
        # Prüfe ob alle erforderlichen Felder vorhanden sind
        required_fields = ['mail_server', 'mail_port', 'mail_username', 'mail_password']
        missing_fields = [field for field in required_fields if not config.get(field)]
        
        if missing_fields:
            return {
                'status': 'error',
                'message': f'Unvollständige E-Mail-Konfiguration',
                'details': f'Fehlende Felder: {", ".join(missing_fields)}',
                'config': {k: v if k != 'mail_password' else '***' for k, v in config.items()}
            }
        
        return {
            'status': 'ok',
            'message': 'E-Mail-Konfiguration vollständig',
            'details': f'SMTP: {config["mail_server"]}:{config["mail_port"]}, TLS: {config["mail_use_tls"]}',
            'config': {k: v if k != 'mail_password' else '***' for k, v in config.items()}
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Fehler beim Prüfen des E-Mail-Status: {str(e)}',
            'details': 'Überprüfen Sie die Logs für weitere Details'
        }

def send_email_with_config(to_email, subject, html_content=None, text_content=None, config=None):
    """
    Sendet eine E-Mail mit einer spezifischen Konfiguration
    
    Args:
        to_email: Empfänger-E-Mail
        subject: Betreff
        html_content: HTML-Inhalt (optional)
        text_content: Text-Inhalt (optional)
        config: E-Mail-Konfiguration (optional, falls nicht angegeben wird get_email_config() verwendet)
    
    Returns:
        bool: True wenn erfolgreich, False bei Fehler
    """
    try:
        if not config:
            config = get_email_config()
        
        if not config:
            logger.error("Keine E-Mail-Konfiguration verfügbar")
            return False
        
        # Prüfe ob alle erforderlichen Einstellungen vorhanden sind
        required_settings = ['mail_server', 'mail_port', 'mail_username', 'mail_password']
        for setting in required_settings:
            if not config.get(setting):
                logger.error(f"Fehlende E-Mail-Einstellung: {setting}")
                return False
        
        # Passwort entschlüsseln falls verschlüsselt
        password = config['mail_password']
        if password.startswith('gAAAAA'):
            try:
                decrypted_password = _decrypt_password(password)
                if decrypted_password:
                    password = decrypted_password
                else:
                    logger.error("Passwort konnte nicht entschlüsselt werden")
                    return False
            except Exception as e:
                logger.error(f"Fehler beim Entschlüsseln des Passworts: {str(e)}")
                return False
        
        # SMTP-Verbindung aufbauen
        if config.get('mail_use_tls') and config['mail_port'] == 465:
            server = smtplib.SMTP_SSL(config['mail_server'], config['mail_port'])
        else:
            server = smtplib.SMTP(config['mail_server'], config['mail_port'])
        
        # EHLO senden
        server.ehlo()
        
        # STARTTLS aktivieren falls konfiguriert
        if config.get('mail_use_tls') and config['mail_port'] == 587:
            server.starttls()
            server.ehlo()
        
        # Authentifizierung
        server.login(config['mail_username'], password)
        
        # E-Mail erstellen
        if html_content and text_content:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = config['mail_username']
            msg['To'] = to_email
            
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
        elif html_content:
            msg = MIMEText(html_content, 'html', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = config['mail_username']
            msg['To'] = to_email
        else:
            msg = MIMEText(text_content or '', 'plain', 'utf-8')
            msg['Subject'] = subject
            msg['From'] = config['mail_username']
            msg['To'] = to_email
        
        # E-Mail senden
        server.send_message(msg)
        server.quit()
        
        logger.info(f"E-Mail erfolgreich gesendet an {to_email}: {subject}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP-Authentifizierungsfehler: {str(e)}")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP-Verbindungsfehler: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP-Fehler: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unerwarteter Fehler beim E-Mail-Versand: {str(e)}")
        return False 