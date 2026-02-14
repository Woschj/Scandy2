"""
Admin Email Templates Service

Verwaltet CRUD und Testversand für E-Mail-Vorlagen in MongoDB.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.models.mongodb_database import mongodb
from app.utils.email_utils import send_email
from flask import render_template_string

logger = logging.getLogger(__name__)


class AdminEmailTemplatesService:
    """Service-Klasse für Verwaltung von E-Mail-Vorlagen."""

    COLLECTION_NAME = 'email_templates'
    SETTINGS_KEY_MAP = 'email_template_map'

    @staticmethod
    def list_templates() -> List[Dict[str, Any]]:
        try:
            templates = list(mongodb.find(AdminEmailTemplatesService.COLLECTION_NAME, {}))
            return sorted(templates, key=lambda t: t.get('name', '').lower())
        except Exception as e:
            logger.error(f"Fehler beim Laden der E-Mail-Vorlagen: [Interner Fehler]")
            return []

    @staticmethod
    def get_template_mappings() -> Dict[str, str]:
        """Liest die Action→Template-Key Zuordnung aus Settings, mit Defaults."""
        try:
            settings_row = mongodb.find_one('settings', {'key': AdminEmailTemplatesService.SETTINGS_KEY_MAP})
            mapping = (settings_row or {}).get('value') or {}
            defaults = {
                'auftrag_confirmation': 'auftrag_confirmation',
                'password_reset': 'password_reset',
                'user_welcome': 'user_welcome',
            }
            # Merge defaults with stored mapping
            return {**defaults, **mapping}
        except Exception:
            return {
                'auftrag_confirmation': 'auftrag_confirmation',
                'password_reset': 'password_reset',
                'user_welcome': 'user_welcome',
            }

    @staticmethod
    def save_template_mappings(mapping: Dict[str, str]) -> Tuple[bool, str]:
        try:
            mongodb.update_one('settings', {'key': AdminEmailTemplatesService.SETTINGS_KEY_MAP}, {'$set': {'value': mapping}}, upsert=True)
            return True, 'Vorlagen-Zuordnungen gespeichert.'
        except Exception as e:
            return False, f'Fehler beim Speichern der Zuordnungen: [Interner Fehler]'

    @staticmethod
    def get_template(template_id: str) -> Optional[Dict[str, Any]]:
        try:
            from bson import ObjectId
            return mongodb.find_one(AdminEmailTemplatesService.COLLECTION_NAME, {'_id': ObjectId(template_id)})
        except Exception as e:
            logger.error(f"Fehler beim Laden der E-Mail-Vorlage {template_id}: [Interner Fehler]")
            return None

    @staticmethod
    def get_template_by_key(template_key: str) -> Optional[Dict[str, Any]]:
        try:
            return mongodb.find_one(AdminEmailTemplatesService.COLLECTION_NAME, {'key': template_key})
        except Exception as e:
            logger.error(f"Fehler beim Laden der E-Mail-Vorlage mit key={template_key}: [Interner Fehler]")
            return None

    @staticmethod
    def create_template(data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        try:
            now = datetime.now()
            doc = {
                'name': data.get('name', '').strip(),
                'key': data.get('key', '').strip(),
                'subject': data.get('subject', '').strip(),
                'html_content': data.get('html_content', ''),
                'text_content': data.get('text_content', ''),
                'created_at': now,
                'updated_at': now,
            }
            if not doc['name'] or not doc['key']:
                return False, 'Name und Schlüssel (key) sind erforderlich.', None

            # Einzigartigkeit des Keys sicherstellen
            existing = AdminEmailTemplatesService.get_template_by_key(doc['key'])
            if existing:
                return False, 'Ein Template mit diesem Schlüssel existiert bereits.', None

            inserted_id = mongodb.insert_one(AdminEmailTemplatesService.COLLECTION_NAME, doc)
            return True, 'E-Mail-Vorlage erstellt.', str(inserted_id)
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der E-Mail-Vorlage: [Interner Fehler]")
            return False, f"Fehler beim Erstellen: [Interner Fehler]", None

    @staticmethod
    def update_template(template_id: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            from bson import ObjectId
            # Name und Key sind systemseitig fix und werden nicht änderbar gemacht
            update = {
                'subject': data.get('subject', '').strip(),
                'html_content': data.get('html_content', ''),
                'text_content': data.get('text_content', ''),
                'updated_at': datetime.now(),
            }

            mongodb.update_one(
                AdminEmailTemplatesService.COLLECTION_NAME,
                {'_id': ObjectId(template_id)},
                {'$set': update}
            )
            return True, 'E-Mail-Vorlage aktualisiert.'
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der E-Mail-Vorlage {template_id}: [Interner Fehler]")
            return False, f"Fehler beim Aktualisieren: [Interner Fehler]"

    @staticmethod
    def delete_template(template_id: str) -> Tuple[bool, str]:
        try:
            from bson import ObjectId
            mongodb.delete_one(AdminEmailTemplatesService.COLLECTION_NAME, {'_id': ObjectId(template_id)})
            return True, 'E-Mail-Vorlage gelöscht.'
        except Exception as e:
            logger.error(f"Fehler beim Löschen der E-Mail-Vorlage {template_id}: [Interner Fehler]")
            return False, f"Fehler beim Löschen: [Interner Fehler]"

    @staticmethod
    def send_test_email(template_id: str, recipient_email: str) -> Tuple[bool, str]:
        try:
            template = AdminEmailTemplatesService.get_template(template_id)
            if not template:
                return False, 'Vorlage nicht gefunden.'
            if not recipient_email:
                return False, 'Empfänger-E-Mail fehlt.'

            # Prüfe ob E-Mail-Konfiguration vorhanden ist
            from app.services.admin_email_service import AdminEmailService
            email_config = AdminEmailService.get_email_config()
            if not email_config:
                return False, 'Keine E-Mail-Konfiguration gefunden. Bitte konfigurieren Sie zuerst das E-Mail-System.'

            # Prüfe ob alle erforderlichen E-Mail-Einstellungen vorhanden sind
            required_settings = ['mail_server', 'mail_port', 'mail_username', 'mail_password']
            missing_settings = []
            for setting in required_settings:
                if setting not in email_config or not email_config[setting]:
                    missing_settings.append(setting.replace('mail_', ''))
            
            if missing_settings:
                return False, f'Fehlende E-Mail-Einstellungen: {", ".join(missing_settings)}. Bitte vervollständigen Sie die E-Mail-Konfiguration.'

            subject_tpl = template.get('subject') or 'Test-E-Mail'
            html_tpl = template.get('html_content') or ''
            text_tpl = template.get('text_content') or ''

            # Beispieldaten für das Test-Rendering je nach Key
            key = template.get('key') or ''
            sample_context: Dict[str, Any] = {}
            if key == 'auftrag_confirmation':
                sample_context = {
                    'ticket': {
                        'ticket_number': 'A-2025-0001',
                        'title': 'Beispielauftrag',
                        'category': 'Allgemein',
                        'priority': 'normal',
                        'description': 'Dies ist eine Beispielbeschreibung.',
                        'created_at': '14.08.2025 10:00',
                    },
                    'auftrag': {
                        'auftraggeber_name': 'Max Mustermann',
                        'bereich': 'IT',
                    }
                }
            elif key == 'password_reset':
                sample_context = {
                    'username': 'mmustermann',
                    'reset_link': 'https://example.local/auth/reset/TESTTOKEN',
                    'password': 'NeuesPasswort123',
                }
            elif key == 'user_welcome':
                sample_context = {
                    'firstname': 'Max',
                    'username': 'mmustermann',
                    'password': 'StartPasswort!',
                    'login_url': 'https://example.local/auth/login',
                }

            try:
                subject = render_template_string(subject_tpl, **sample_context) if subject_tpl else 'Test-E-Mail'
                html_content = render_template_string(html_tpl, **sample_context) if html_tpl else ''
                text_content = render_template_string(text_tpl, **sample_context) if text_tpl else ''
            except Exception as e:
                logger.warning(f"Test-Rendering fehlgeschlagen, sende Rohtext: [Interner Fehler]")
                subject = subject_tpl
                html_content = html_tpl
                text_content = text_tpl

            # Sende Test-E-Mail mit direkter SMTP-Verbindung
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                from email.header import Header
                
                # E-Mail-Nachricht erstellen
                msg = MIMEMultipart()
                msg['From'] = email_config['mail_username']
                msg['To'] = recipient_email
                msg['Subject'] = Header(subject, 'utf-8')
                
                # Body hinzufügen
                if html_content:
                    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
                elif text_content:
                    msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
                else:
                    msg.attach(MIMEText('Test-E-Mail ohne Inhalt', 'plain', 'utf-8'))
                
                # SMTP-Verbindung aufbauen
                if email_config['mail_use_tls'] and email_config['mail_port'] == 465:
                    server = smtplib.SMTP_SSL(email_config['mail_server'], email_config['mail_port'])
                else:
                    server = smtplib.SMTP(email_config['mail_server'], email_config['mail_port'])
                
                # STARTTLS aktivieren falls konfiguriert
                if email_config['mail_use_tls'] and email_config['mail_port'] == 587:
                    server.starttls()
                
                # Authentifizierung
                if email_config.get('use_auth', True) and email_config['mail_username'] and email_config['mail_password']:
                    server.login(email_config['mail_username'], email_config['mail_password'])
                
                # E-Mail senden (als Bytes, um ASCII-Kodierungsprobleme zu vermeiden)
                server.sendmail(email_config['mail_username'], recipient_email, msg.as_bytes())
                server.quit()
                
                logger.info(f"Test-E-Mail erfolgreich gesendet an {recipient_email}")
                return True, f'Test-E-Mail erfolgreich gesendet an {recipient_email}.'
                
            except Exception as e:
                logger.error(f"Fehler beim SMTP-Versand der Test-E-Mail: [Interner Fehler]")
                return False, f'E-Mail-Versand fehlgeschlagen: [Interner Fehler]'
                
        except Exception as e:
            logger.error(f"Fehler beim Testversand: [Interner Fehler]")
            return False, f"Fehler beim Testversand: [Interner Fehler]"

    @staticmethod
    def render_template_by_key(template_key: str, context: Dict[str, Any]) -> Optional[Dict[str, Optional[str]]]:
        """
        Rendert eine E-Mail-Vorlage anhand des Schlüssels mit Jinja2-Variablenersetzung.
        Returns: Dict mit 'subject', 'html_content', 'text_content' oder None, wenn nicht gefunden.
        """
        try:
            # Resolve action->key mapping, falls eine Action übergeben wurde
            resolved_key = AdminEmailTemplatesService.resolve_template_key_for_action(template_key)
            template = AdminEmailTemplatesService.get_template_by_key(resolved_key)
            if not template:
                return None
            subject_tpl = template.get('subject') or ''
            html_tpl = template.get('html_content') or ''
            text_tpl = template.get('text_content') or ''

            rendered = {
                'subject': render_template_string(subject_tpl, **context) if subject_tpl else None,
                'html_content': render_template_string(html_tpl, **context) if html_tpl else None,
                'text_content': render_template_string(text_tpl, **context) if text_tpl else None,
            }
            return rendered
        except Exception as e:
            logger.error(f"Fehler beim Rendern der E-Mail-Vorlage '{template_key}': [Interner Fehler]")
            return None

    @staticmethod
    def resolve_template_key_for_action(action: str) -> str:
        mapping = AdminEmailTemplatesService.get_template_mappings()
        return mapping.get(action, action)

    @staticmethod
    def ensure_default_templates() -> Dict[str, Any]:
        """Erzeugt Standardvorlagen, falls nicht vorhanden. Rückgabe enthält counts."""
        created = 0
        skipped = 0
        defaults: List[Dict[str, Any]] = [
            {
                'name': 'Auftragsbestätigung (Standard)',
                'key': 'auftrag_confirmation',
                'subject': 'Auftragsbestätigung - {{ ticket.ticket_number or "Neuer Auftrag" }}',
                'html_content': (
                    """
                    <!DOCTYPE html>
                    <html lang=\"de\">
                    <head>
                        <meta charset=\"UTF-8\">
                        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
                        <title>Auftragsbestätigung</title>
                        <style>
                            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                            .header { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                            .content { background-color: #ffffff; padding: 30px; border: 1px solid #dee2e6; }
                            .footer { background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; font-size: 14px; color: #6c757d; }
                            .success-icon { color: #28a745; font-size: 48px; margin-bottom: 20px; }
                            .ticket-number { background-color: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0; }
                            .ticket-number .number { font-size: 24px; font-weight: bold; color: #007bff; font-family: monospace; }
                            .details { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
                            .details h3 { margin-top: 0; color: #495057; }
                            .details table { width: 100%; border-collapse: collapse; }
                            .details td { padding: 8px; border-bottom: 1px solid #dee2e6; }
                            .details td:first-child { font-weight: bold; width: 30%; }
                            .priority-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
                            .priority-normal { background-color: #007bff; color: white; }
                            .priority-hoch { background-color: #dc3545; color: white; }
                            .priority-niedrig { background-color: #6c757d; color: white; }
                            .next-steps { background-color: #d1ecf1; padding: 20px; border-radius: 5px; margin: 20px 0; }
                            .next-steps h3 { margin-top: 0; color: #0c5460; }
                            .next-steps ul { margin: 0; padding-left: 20px; }
                            .next-steps li { margin-bottom: 8px; }
                            .contact-info { background-color: #e2e3e5; padding: 20px; border-radius: 5px; margin: 20px 0; }
                            .contact-info h3 { margin-top: 0; color: #383d41; }
                            .btn { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }
                            .btn:hover { background-color: #0056b3; }
                        </style>
                    </head>
                    <body>
                        <div class=\"container\">
                            <div class=\"header\">
                                <div class=\"success-icon\">✓</div>
                                <h1 style=\"margin: 0; color: #28a745;\">Auftrag erfolgreich erstellt!</h1>
                                <p style=\"margin: 10px 0 0 0; color: #6c757d;\">Vielen Dank für Ihren Auftrag</p>
                            </div>
                            <div class=\"content\">
                                <div class=\"ticket-number\">
                                    <p style=\"margin: 0 0 10px 0; font-weight: bold;\">Ihre Auftragsnummer:</p>
                                    <div class=\"number\">{{ ticket.ticket_number }}</div>
                                </div>
                                <div class=\"details\">
                                    <h3>Auftragsdetails</h3>
                                    <table>
                                        <tr><td>Titel:</td><td>{{ ticket.title }}</td></tr>
                                        <tr><td>Kategorie:</td><td>{{ ticket.category or 'Nicht angegeben' }}</td></tr>
                                        <tr><td>Priorität:</td><td><span class=\"priority-badge priority-{{ ticket.priority|default('normal') }}\">{{ ticket.priority|default('normal')|title }}</span></td></tr>
                                        <tr><td>Auftraggeber:</td><td>{{ auftrag.auftraggeber_name or 'N/A' }}</td></tr>
                                        <tr><td>Bereich:</td><td>{{ auftrag.bereich or 'Nicht angegeben' }}</td></tr>
                                        <tr><td>Erstellt am:</td><td>{{ ticket.created_at }}</td></tr>
                                    </table>
                                    <h4 style=\"margin-top: 20px;\">Beschreibung:</h4>
                                    <p style=\"background-color: white; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff;\">{{ ticket.description or 'Keine Beschreibung vorhanden' }}</p>
                                </div>
                                <div class=\"next-steps\">
                                    <h3>Nächste Schritte</h3>
                                    <ul>
                                        <li>Wir haben Ihren Auftrag in unserem System erfasst</li>
                                        <li>Wir werden die Details besprechen und einen Zeitplan erstellen</li>
                                        <li>Sie erhalten Updates zum Fortschritt Ihres Auftrags</li>
                                    </ul>
                                </div>
                                <div class=\"contact-info\">
                                    <h3>Kontakt</h3>
                                    <p style=\"margin-bottom: 10px;\">Bei Fragen erreichen Sie uns über das Scandy-System.</p>
                                </div>
                                <div style=\"text-align: center; margin-top: 30px;\">
                                    <a href=\"/tickets/auftrag-neu\" class=\"btn\">Neuen Auftrag erstellen</a>
                                    <a href=\"/\" class=\"btn\" style=\"background-color: #6c757d;\">Zur Startseite</a>
                                </div>
                            </div>
                            <div class=\"footer\">
                                <p>Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht auf diese E-Mail.</p>
                                <p>Scandy - Ihr Auftragssystem</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                ).strip(),
                'text_content': (
                    """
                    Auftragsbestätigung - {{ ticket.ticket_number or 'Neuer Auftrag' }}\n\nVielen Dank für Ihren Auftrag!\n\nIhre Auftragsnummer: {{ ticket.ticket_number }}\n\nAUFTRAGSDETAILS:\n- Titel: {{ ticket.title }}\n- Kategorie: {{ ticket.category or 'Nicht angegeben' }}\n- Priorität: {{ ticket.priority|default('normal')|title }}\n- Auftraggeber: {{ auftrag.auftraggeber_name or 'N/A' }}\n- Bereich: {{ auftrag.bereich or 'Nicht angegeben' }}\n- Erstellt am: {{ ticket.created_at }}\n\nBeschreibung:\n{{ ticket.description or 'Keine Beschreibung vorhanden' }}\n\nNÄCHSTE SCHRITTE:\n- Wir haben Ihren Auftrag in unserem System erfasst\n- Wir werden die Details besprechen und einen Zeitplan erstellen\n- Sie erhalten Updates zum Fortschritt Ihres Auftrags\n\nKONTAKT:\nBei Fragen erreichen Sie uns über das Scandy-System.\n\nScandy - Ihr Auftragssystem
                    """
                ).strip(),
            },
            {
                'name': 'Passwort-Reset (Standard)',
                'key': 'password_reset',
                'subject': 'Scandy – Passwort zurücksetzen',
                'html_content': (
                    """
                    <h2>Passwort zurücksetzen</h2>
                    <p>Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.</p>
                    {% if reset_link %}<p><a href="{{ reset_link }}">Passwort jetzt zurücksetzen</a></p>{% endif %}
                    {% if password %}<p>Neues Passwort: <strong>{{ password }}</strong></p>{% endif %}
                    <p>Mit freundlichen Grüßen<br>Ihr Scandy-Team</p>
                    """
                ).strip(),
                'text_content': (
                    """
                    Passwort zurücksetzen\n\n{% if reset_link %}Link: {{ reset_link }}{% endif %}{% if password %}\nNeues Passwort: {{ password }}{% endif %}
                    """
                ).strip(),
            },
            {
                'name': 'Willkommensmail neuer Benutzer (Standard)',
                'key': 'user_welcome',
                'subject': 'Scandy – Ihre Zugangsdaten',
                'html_content': (
                    """
                    <h2>Willkommen bei Scandy!</h2>
                    <p>Hallo {{ firstname }}, Ihr Benutzerkonto wurde erstellt.</p>
                    <ul>
                        <li><strong>Benutzername:</strong> {{ username }}</li>
                        <li><strong>Passwort:</strong> {{ password }}</li>
                    </ul>
                    <p>Login: <a href="{{ login_url }}">{{ login_url }}</a></p>
                    <p>Bitte ändern Sie Ihr Passwort nach der ersten Anmeldung.</p>
                    """
                ).strip(),
                'text_content': (
                    """
                    Willkommen bei Scandy\n\nBenutzername: {{ username }}\nPasswort: {{ password }}\nLogin: {{ login_url }}
                    """
                ).strip(),
            },
        ]
        for tpl in defaults:
            if AdminEmailTemplatesService.get_template_by_key(tpl['key']):
                skipped += 1
                continue
            ok, _, _id = AdminEmailTemplatesService.create_template(tpl)
            if ok:
                created += 1
        return {'created': created, 'skipped': skipped}


