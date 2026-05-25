import pytest
from unittest.mock import patch, MagicMock

from app.services.admin_email_templates_service import AdminEmailTemplatesService

class TestAdminEmailTemplatesService:
    @pytest.fixture
    def mock_email_config(self):
        return {
            'mail_server': 'smtp.example.com',
            'mail_port': 587,
            'mail_username': 'test@example.com',
            'mail_password': 'password123',
            'mail_use_tls': True,
            'use_auth': True
        }

    @pytest.fixture
    def mock_template(self):
        return {
            '_id': '123',
            'name': 'Test Template',
            'key': 'test_key',
            'subject': 'Test Subject {{ test_var }}',
            'html_content': '<p>HTML {{ test_var }}</p>',
            'text_content': 'Text {{ test_var }}'
        }

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    def test_send_test_email_template_not_found(self, mock_get_template):
        mock_get_template.return_value = None

        success, message = AdminEmailTemplatesService.send_test_email('invalid_id', 'test@example.com')

        assert not success
        assert message == 'Vorlage nicht gefunden.'
        mock_get_template.assert_called_once_with('invalid_id')

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    def test_send_test_email_recipient_missing(self, mock_get_template, mock_template):
        mock_get_template.return_value = mock_template

        success, message = AdminEmailTemplatesService.send_test_email('123', '')

        assert not success
        assert message == 'Empfänger-E-Mail fehlt.'

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    @patch('app.services.admin_email_service.AdminEmailService.get_email_config')
    def test_send_test_email_config_missing(self, mock_get_config, mock_get_template, mock_template):
        mock_get_template.return_value = mock_template
        mock_get_config.return_value = None

        success, message = AdminEmailTemplatesService.send_test_email('123', 'test@example.com')

        assert not success
        assert 'Keine E-Mail-Konfiguration gefunden' in message

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    @patch('app.services.admin_email_service.AdminEmailService.get_email_config')
    def test_send_test_email_incomplete_config(self, mock_get_config, mock_get_template, mock_template, mock_email_config):
        mock_get_template.return_value = mock_template

        # Remove a required setting
        incomplete_config = mock_email_config.copy()
        incomplete_config['mail_password'] = ''
        mock_get_config.return_value = incomplete_config

        success, message = AdminEmailTemplatesService.send_test_email('123', 'test@example.com')

        assert not success
        assert 'Fehlende E-Mail-Einstellungen' in message
        assert 'password' in message

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    @patch('app.services.admin_email_service.AdminEmailService.get_email_config')
    @patch('smtplib.SMTP')
    def test_send_test_email_success(self, mock_smtp, mock_get_config, mock_get_template, mock_template, mock_email_config, app):
        mock_get_template.return_value = mock_template
        mock_get_config.return_value = mock_email_config

        # Setup SMTP mock
        mock_server_instance = MagicMock()
        mock_smtp.return_value = mock_server_instance

        with app.app_context():
            success, message = AdminEmailTemplatesService.send_test_email('123', 'test@example.com')

        assert success
        assert 'erfolgreich gesendet' in message

        # Verify SMTP interactions
        mock_smtp.assert_called_once_with('smtp.example.com', 587)
        mock_server_instance.starttls.assert_called_once()
        mock_server_instance.login.assert_called_once_with('test@example.com', 'password123')
        mock_server_instance.sendmail.assert_called_once()
        mock_server_instance.quit.assert_called_once()

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    @patch('app.services.admin_email_service.AdminEmailService.get_email_config')
    @patch('smtplib.SMTP')
    def test_send_test_email_smtp_error(self, mock_smtp, mock_get_config, mock_get_template, mock_template, mock_email_config, app):
        mock_get_template.return_value = mock_template
        mock_get_config.return_value = mock_email_config

        # Setup SMTP mock to raise an exception
        mock_smtp.side_effect = Exception("SMTP connection failed")

        with app.app_context():
            success, message = AdminEmailTemplatesService.send_test_email('123', 'test@example.com')

        assert not success
        assert 'E-Mail-Versand fehlgeschlagen' in message

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    @patch('app.services.admin_email_service.AdminEmailService.get_email_config')
    @patch('app.services.admin_email_templates_service.render_template_string')
    @patch('smtplib.SMTP')
    def test_send_test_email_rendering_error_fallback(self, mock_smtp, mock_render, mock_get_config, mock_get_template, mock_template, mock_email_config, app):
        # We need to test the fallback behavior when rendering fails
        mock_get_template.return_value = mock_template
        mock_get_config.return_value = mock_email_config

        # Force render_template_string to fail
        mock_render.side_effect = Exception("Template syntax error")

        mock_server_instance = MagicMock()
        mock_smtp.return_value = mock_server_instance

        with app.app_context():
            success, message = AdminEmailTemplatesService.send_test_email('123', 'test@example.com')

        # Even if rendering fails, it falls back to raw template and sends it
        assert success
        assert 'erfolgreich gesendet' in message
        mock_server_instance.sendmail.assert_called_once()

        # Get the actual message passed to sendmail
        call_args = mock_server_instance.sendmail.call_args[0]
        msg_bytes = call_args[2]

        # Verify it contains the unrendered raw template content (HTML in this case, as it prefers HTML if both exist)
        assert b'HTML {{ test_var }}' in msg_bytes

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template')
    @patch('app.services.admin_email_service.AdminEmailService.get_email_config')
    @patch('smtplib.SMTP_SSL')
    def test_send_test_email_ssl(self, mock_smtp_ssl, mock_get_config, mock_get_template, mock_template, mock_email_config, app):
        mock_get_template.return_value = mock_template

        # Update config for SSL
        ssl_config = mock_email_config.copy()
        ssl_config['mail_port'] = 465
        ssl_config['mail_use_tls'] = True
        mock_get_config.return_value = ssl_config

        # Setup SMTP_SSL mock
        mock_server_instance = MagicMock()
        mock_smtp_ssl.return_value = mock_server_instance

        with app.app_context():
            success, message = AdminEmailTemplatesService.send_test_email('123', 'test@example.com')

        assert success
        mock_smtp_ssl.assert_called_once_with('smtp.example.com', 465)
        # starttls should not be called for port 465
        mock_server_instance.starttls.assert_not_called()
        mock_server_instance.sendmail.assert_called_once()

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template_by_key')
    @patch('app.services.admin_email_templates_service.render_template_string')
    def test_render_template_by_key_success(self, mock_render_template_string, mock_get_template_by_key, mock_template):
        # Wir testen die gesamte Funktionalität inkl. resolve_template_key_for_action
        # Da kein Mapping existiert (oder wir mocken keines), gibt es einfach den Key zurück
        mock_get_template_by_key.return_value = mock_template

        # render_template_string is called 3 times, let's mock it to return predictable values
        mock_render_template_string.side_effect = ['Rendered Subject', 'Rendered HTML', 'Rendered Text']

        context = {'test_var': 'value'}

        result = AdminEmailTemplatesService.render_template_by_key('action_key', context)

        assert result is not None
        # Verify the returned dict matches exactly what the code constructs
        assert result['subject'] == 'Rendered Subject'
        assert result['html_content'] == 'Rendered HTML'
        assert result['text_content'] == 'Rendered Text'

        mock_get_template_by_key.assert_called_once()
        assert mock_render_template_string.call_count == 3

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template_by_key')
    def test_render_template_by_key_not_found(self, mock_get_template_by_key):
        mock_get_template_by_key.return_value = None

        result = AdminEmailTemplatesService.render_template_by_key('action_key', {})

        assert result is None
        mock_get_template_by_key.assert_called_once()

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template_by_key')
    @patch('app.services.admin_email_templates_service.render_template_string')
    def test_render_template_by_key_exception(self, mock_render_template_string, mock_get_template_by_key, mock_template):
        mock_get_template_by_key.return_value = mock_template

        # Force exception
        mock_render_template_string.side_effect = Exception("Render error")

        result = AdminEmailTemplatesService.render_template_by_key('action_key', {})

        assert result is None

    @patch('app.services.admin_email_templates_service.AdminEmailTemplatesService.get_template_by_key')
    @patch('app.services.admin_email_templates_service.render_template_string')
    def test_render_template_by_key_missing_fields(self, mock_render_template_string, mock_get_template_by_key):
        # Template with missing/empty fields
        mock_template_empty = {
            'subject': '',
            'html_content': None
            # text_content missing completely
        }
        mock_get_template_by_key.return_value = mock_template_empty

        result = AdminEmailTemplatesService.render_template_by_key('action_key', {})

        assert result is not None
        assert result['subject'] is None
        assert result['html_content'] is None
        assert result['text_content'] is None

        # render_template_string should not be called since fields are empty/None
        mock_render_template_string.assert_not_called()
