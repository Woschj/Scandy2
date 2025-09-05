"""
Unit tests for security utilities.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.utils.security_utils import (
    InputValidator, SecurityManager, PasswordPolicy,
    SecureHeaders, require_secure_password, validate_input
)


class TestInputValidator:
    """Test input validation functions."""

    def test_validate_username_valid(self):
        """Test valid username validation."""
        assert InputValidator.validate_username("testuser123") is True
        assert InputValidator.validate_username("user_name") is True
        assert InputValidator.validate_username("user-name") is True

    def test_validate_username_invalid(self):
        """Test invalid username validation."""
        assert InputValidator.validate_username("") is False
        assert InputValidator.validate_username("us") is False  # Too short
        assert InputValidator.validate_username("user@name") is False  # Invalid char
        assert InputValidator.validate_username("a" * 51) is False  # Too long

    def test_validate_email_valid(self):
        """Test valid email validation."""
        assert InputValidator.validate_email("test@example.com") is True
        assert InputValidator.validate_email("user.name+tag@domain.co.uk") is True

    def test_validate_email_invalid(self):
        """Test invalid email validation."""
        assert InputValidator.validate_email("") is False
        assert InputValidator.validate_email("notanemail") is False
        assert InputValidator.validate_email("test@") is False
        assert InputValidator.validate_email("@example.com") is False

    def test_validate_barcode_valid(self):
        """Test valid barcode validation."""
        assert InputValidator.validate_barcode("ABC123456") is True
        assert InputValidator.validate_barcode("XYZ789012") is True

    def test_validate_barcode_invalid(self):
        """Test invalid barcode validation."""
        assert InputValidator.validate_barcode("") is False
        assert InputValidator.validate_barcode("abc123") is False  # Too short
        assert InputValidator.validate_barcode("ABC12345678") is False  # Too long
        assert InputValidator.validate_barcode("abc123456") is False  # Lowercase

    def test_sanitize_html(self):
        """Test HTML sanitization."""
        html_input = '<script>alert("xss")</script><p>Safe content</p>'
        sanitized = InputValidator.sanitize_html(html_input)

        assert '<script>' not in sanitized
        assert 'Safe content' in sanitized
        assert '<p>' in sanitized

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        dangerous_filename = "../../../etc/passwd"
        sanitized = InputValidator.sanitize_filename(dangerous_filename)

        assert ".." not in sanitized
        assert "/" not in sanitized
        assert "\\" not in sanitized


class TestPasswordPolicy:
    """Test password policy validation."""

    def test_validate_password_strong(self):
        """Test strong password validation."""
        result = PasswordPolicy.validate_password("MySecurePass123!")

        assert result['valid'] is True
        assert result['strength'] == 'strong'

    def test_validate_password_weak(self):
        """Test weak password validation."""
        result = PasswordPolicy.validate_password("password")

        assert result['valid'] is False
        assert result['strength'] == 'weak'
        assert len(result['issues']) > 0

    def test_validate_password_common(self):
        """Test validation of common passwords."""
        result = PasswordPolicy.validate_password("password123")

        assert result['valid'] is False
        assert any("common" in issue.lower() for issue in result['issues'])

    def test_password_requirements(self):
        """Test individual password requirements."""
        # Test missing uppercase
        result = PasswordPolicy.validate_password("mysecurepass123!")
        assert result['valid'] is False

        # Test missing lowercase
        result = PasswordPolicy.validate_password("MYSECUREPASS123!")
        assert result['valid'] is False

        # Test missing digits
        result = PasswordPolicy.validate_password("MySecurePass!")
        assert result['valid'] is False

        # Test missing special chars
        result = PasswordPolicy.validate_password("MySecurePass123")
        assert result['valid'] is False

        # Test too short
        result = PasswordPolicy.validate_password("Pass1!")
        assert result['valid'] is False


class TestSecurityManager:
    """Test security manager functionality."""

    def test_record_failed_login(self):
        """Test failed login recording."""
        manager = SecurityManager()

        # First failed attempt
        blocked = manager.record_failed_login("192.168.1.100", "testuser")
        assert blocked is False

        # Second failed attempt
        blocked = manager.record_failed_login("192.168.1.100", "testuser")
        assert blocked is False

        # Third failed attempt
        blocked = manager.record_failed_login("192.168.1.100", "testuser")
        assert blocked is False

        # Fourth failed attempt
        blocked = manager.record_failed_login("192.168.1.100", "testuser")
        assert blocked is False

        # Fifth failed attempt - should be blocked
        blocked = manager.record_failed_login("192.168.1.100", "testuser")
        assert blocked is True

    def test_block_ip(self):
        """Test IP blocking functionality."""
        manager = SecurityManager()

        assert manager.is_ip_blocked("192.168.1.100") is False

        manager.block_ip("192.168.1.100", "Test blocking")

        assert manager.is_ip_blocked("192.168.1.100") is True


class TestSecureHeaders:
    """Test security headers configuration."""

    def test_get_headers_basic(self):
        """Test basic security headers."""
        headers = SecureHeaders.get_headers(enable_hsts=False)

        assert 'X-Content-Type-Options' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'
        assert 'X-Frame-Options' in headers
        assert headers['X-Frame-Options'] == 'DENY'
        assert 'Content-Security-Policy' in headers

    def test_get_headers_with_hsts(self):
        """Test security headers with HSTS."""
        headers = SecureHeaders.get_headers(enable_hsts=True)

        assert 'Strict-Transport-Security' in headers
        assert 'max-age=31536000' in headers['Strict-Transport-Security']


class TestDecorators:
    """Test security decorators."""

    def test_require_secure_password_valid(self):
        """Test password requirement decorator with valid password."""
        @require_secure_password
        def create_user(password):
            return {"user": "created", "password": password}

        result = create_user("MySecurePass123!")
        assert result["user"] == "created"

    def test_require_secure_password_invalid(self):
        """Test password requirement decorator with invalid password."""
        @require_secure_password
        def create_user(password):
            return {"user": "created", "password": password}

        with pytest.raises(ValueError, match="does not meet security requirements"):
            create_user("password")

    def test_validate_input_valid(self):
        """Test input validation decorator with valid input."""
        @validate_input(username=InputValidator.validate_username)
        def create_user(username):
            return {"user": username}

        result = create_user("validuser123")
        assert result["user"] == "validuser123"

    def test_validate_input_invalid(self):
        """Test input validation decorator with invalid input."""
        @validate_input(username=InputValidator.validate_username)
        def create_user(username):
            return {"user": username}

        with pytest.raises(Exception):  # Should raise 400 error
            create_user("invalid@username")
