"""
Security utilities for Scandy

Provides security hardening, input validation, and protection against common attacks.
"""

import re
import hashlib
import secrets
import bleach
from typing import Dict, Any, List, Optional, Union
from flask import request, current_app
from functools import wraps
import ipaddress
import time
from datetime import datetime, timedelta

from app.utils.logger import log_security_event


class InputValidator:
    """Comprehensive input validation and sanitization"""

    # Regex patterns for validation
    PATTERNS = {
        'username': re.compile(r'^[a-zA-Z0-9_-]{3,50}$'),
        'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        'barcode': re.compile(r'^[A-Z0-9]{6,20}$'),
        'phone': re.compile(r'^\+?[0-9\s\-\(\)]{7,20}$'),
        'name': re.compile(r'^[a-zA-ZäöüÄÖÜß\s\-]{1,100}$'),
        'safe_text': re.compile(r'^[a-zA-Z0-9äöüÄÖÜß\s\-.,!?()]{1,500}$'),
    }

    ALLOWED_HTML_TAGS = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    ALLOWED_HTML_ATTRS = {'*': ['class']}

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML input to prevent XSS"""
        if not isinstance(text, str):
            return ""
        return bleach.clean(text, tags=InputValidator.ALLOWED_HTML_TAGS,
                          attributes=InputValidator.ALLOWED_HTML_ATTRS, strip=True)

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not isinstance(username, str):
            return False
        return bool(InputValidator.PATTERNS['username'].match(username))

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not isinstance(email, str):
            return False
        return bool(InputValidator.PATTERNS['email'].match(email.lower()))

    @staticmethod
    def validate_barcode(barcode: str) -> bool:
        """Validate barcode format"""
        if not isinstance(barcode, str):
            return False
        return bool(InputValidator.PATTERNS['barcode'].match(barcode.upper()))

    @staticmethod
    def validate_name(name: str) -> bool:
        """Validate name format"""
        if not isinstance(name, str):
            return False
        return bool(InputValidator.PATTERNS['name'].match(name.strip()))

    @staticmethod
    def validate_safe_text(text: str, max_length: int = 500) -> bool:
        """Validate safe text input"""
        if not isinstance(text, str):
            return False
        if len(text) > max_length:
            return False
        return bool(InputValidator.PATTERNS['safe_text'].match(text))

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal"""
        if not filename:
            return ""

        # Remove path separators
        filename = re.sub(r'[\/\\]', '', filename)

        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)

        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]

        return filename


class SecurityManager:
    """Central security management"""

    def __init__(self):
        self.failed_login_attempts = {}
        self.blocked_ips = set()
        self.suspicious_activity = {}

    def record_failed_login(self, ip_address: str, username: str) -> bool:
        """Record failed login attempt and check for brute force"""
        key = f"{ip_address}:{username}"

        if key not in self.failed_login_attempts:
            self.failed_login_attempts[key] = []

        self.failed_login_attempts[key].append(time.time())

        # Clean old attempts (older than 1 hour)
        cutoff = time.time() - 3600
        self.failed_login_attempts[key] = [
            attempt for attempt in self.failed_login_attempts[key]
            if attempt > cutoff
        ]

        # Check for brute force (more than 5 attempts in last hour)
        if len(self.failed_login_attempts[key]) >= 5:
            self.block_ip(ip_address, "Brute force login attempts")
            log_security_event('brute_force_attempt', username, ip_address,
                             {'attempts': len(self.failed_login_attempts[key])})
            return True  # Blocked

        return False

    def block_ip(self, ip_address: str, reason: str) -> None:
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        log_security_event('ip_blocked', None, ip_address, {'reason': reason})

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips

    def check_rate_limit(self, identifier: str, limit: int = 100, window: int = 60) -> bool:
        """Check rate limiting"""
        # This would be implemented with Redis in production
        # For now, return False (not limited)
        return False

    def validate_request_origin(self) -> bool:
        """Validate request origin for CSRF protection"""
        # Check Referer header
        referer = request.headers.get('Referer', '')
        host = request.headers.get('Host', '')

        if not referer:
            return False

        # Allow requests from same domain
        if host in referer:
            return True

        # Log suspicious request
        log_security_event('suspicious_request', None, request.remote_addr,
                         {'referer': referer, 'host': host})
        return False


class PasswordPolicy:
    """Password security policy"""

    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True

    COMMON_PASSWORDS = {
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey'
    }

    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password against security policy"""
        issues = []

        if len(password) < PasswordPolicy.MIN_LENGTH:
            issues.append(f"Password must be at least {PasswordPolicy.MIN_LENGTH} characters")

        if PasswordPolicy.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            issues.append("Password must contain uppercase letter")

        if PasswordPolicy.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            issues.append("Password must contain lowercase letter")

        if PasswordPolicy.REQUIRE_DIGITS and not re.search(r'[0-9]', password):
            issues.append("Password must contain digit")

        if PasswordPolicy.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain special character")

        if password.lower() in PasswordPolicy.COMMON_PASSWORDS:
            issues.append("Password is too common")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'strength': PasswordPolicy._calculate_strength(password)
        }

    @staticmethod
    def _calculate_strength(password: str) -> str:
        """Calculate password strength"""
        score = 0

        if len(password) >= 12:
            score += 1
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'[0-9]', password):
            score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        if len(password) >= 16:
            score += 1

        if score <= 2:
            return 'weak'
        elif score <= 4:
            return 'medium'
        else:
            return 'strong'


class SecureHeaders:
    """Security headers management"""

    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=(self)',
        'Cross-Origin-Embedder-Policy': 'require-corp',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-origin'
    }

    CSP_POLICY = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.ipify.org; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    @staticmethod
    def get_headers(enable_hsts: bool = False) -> Dict[str, str]:
        """Get security headers"""
        headers = SecureHeaders.SECURITY_HEADERS.copy()
        headers['Content-Security-Policy'] = SecureHeaders.CSP_POLICY

        if enable_hsts:
            headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return headers


# Global security manager instance
security_manager = SecurityManager()


def require_secure_password(func):
    """Decorator to enforce password validation"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        password = kwargs.get('password')
        if password:
            validation = PasswordPolicy.validate_password(password)
            if not validation['valid']:
                log_security_event('weak_password_attempt', None, request.remote_addr,
                                 {'issues': validation['issues']})
                raise ValueError(f"Password does not meet security requirements: {', '.join(validation['issues'])}")
        return func(*args, **kwargs)
    return wrapper


def rate_limit(limit: int = 100, window: int = 60):
    """Rate limiting decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            identifier = request.remote_addr
            if security_manager.check_rate_limit(identifier, limit, window):
                log_security_event('rate_limit_exceeded', None, identifier)
                return {'error': 'Rate limit exceeded'}, 429
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_input(**validators):
    """Input validation decorator"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for field, validator_func in validators.items():
                value = kwargs.get(field)
                if value is not None and not validator_func(value):
                    log_security_event('invalid_input', None, request.remote_addr,
                                     {'field': field, 'value': str(value)[:100]})
                    return {'error': f'Invalid {field}'}, 400
            return func(*args, **kwargs)
        return wrapper
    return decorator
