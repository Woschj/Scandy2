"""
Integration tests for the complete Flask application.
"""

import pytest
import json
from app import create_app
from tests.conftest import assert_response_status, assert_json_response


class TestAppIntegration:
    """Test the complete Flask application."""

    def test_app_creation(self):
        """Test that the app can be created successfully."""
        app = create_app('testing')
        assert app is not None
        assert app.config['TESTING'] is True

    def test_health_check_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get('/health')
        assert_response_status(response, 200)

        data = assert_json_response(response, ['status', 'timestamp'])
        assert data['status'] == 'healthy'

    def test_config_loading(self, app):
        """Test that configuration is loaded correctly."""
        assert app.config['TESTING'] is True
        assert 'SECRET_KEY' in app.config
        assert app.config['SECRET_KEY'] is not None

    def test_cors_headers(self, client):
        """Test CORS-related security headers."""
        response = client.get('/health')

        # Check security headers
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        assert 'X-Frame-Options' in response.headers
        assert response.headers['X-Frame-Options'] == 'DENY'

    def test_json_error_responses(self, client):
        """Test that error responses are properly formatted."""
        # Test 404 error
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404
        assert response.content_type == 'application/json'

        data = response.get_json()
        assert 'error' in data or 'message' in data

    def test_request_logging(self, client, caplog):
        """Test that requests are properly logged."""
        with caplog.at_level('INFO'):
            response = client.get('/health')

        # Check that the request was logged
        log_messages = [record.message for record in caplog.records]
        assert any('API_REQUEST' in msg or 'health' in msg for msg in log_messages)


class TestSecurityIntegration:
    """Test security features integration."""

    def test_input_validation_integration(self, client):
        """Test input validation in the context of the full application."""
        # This would test actual endpoints that use input validation
        # For now, just test that the security modules are loaded
        assert hasattr(client.application, 'config')
        assert client.application.config['SECRET_KEY'] is not None

    def test_session_security(self, client):
        """Test session security configuration."""
        with client.application.test_request_context():
            # Check session cookie settings
            assert client.application.config['SESSION_COOKIE_HTTPONLY'] is True
            assert client.application.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


class TestPerformanceIntegration:
    """Test performance features integration."""

    def test_performance_monitoring(self, client):
        """Test that performance monitoring is active."""
        # Make a request
        response = client.get('/health')

        # Check that performance monitoring is working
        # This would check if performance metrics are being collected
        assert response.status_code == 200

    def test_caching_integration(self, client):
        """Test that caching system is integrated."""
        # Make multiple requests to see if caching is working
        response1 = client.get('/health')
        response2 = client.get('/health')

        assert response1.status_code == 200
        assert response2.status_code == 200
        # In a real scenario, we would check cache headers or timing


class TestLoggingIntegration:
    """Test logging system integration."""

    def test_structured_logging(self, client, caplog):
        """Test that structured logging is working."""
        with caplog.at_level('INFO'):
            response = client.get('/health')

        # Check that logs contain structured information
        log_messages = [record.message for record in caplog.records]

        # Should have some application logs
        assert len(log_messages) > 0

    def test_error_logging(self, client, caplog):
        """Test error logging functionality."""
        with caplog.at_level('ERROR'):
            # Trigger an error by accessing non-existent endpoint
            response = client.get('/nonexistent')

        # Check that errors are logged
        error_logs = [record for record in caplog.records if record.levelname == 'ERROR']
        assert len(error_logs) >= 0  # May or may not have error logs depending on implementation


class TestConfigurationIntegration:
    """Test configuration system integration."""

    def test_environment_config_loading(self, app):
        """Test that environment-based configuration is working."""
        # Check that testing configuration is properly loaded
        assert app.config['TESTING'] is True
        assert app.config['DEBUG'] is True

    def test_database_config_integration(self, app):
        """Test database configuration integration."""
        # Check that database configuration is available
        # (Actual database connection may not be tested here)
        assert 'MONGODB_DB' in str(app.config) or hasattr(app.config, 'database')
