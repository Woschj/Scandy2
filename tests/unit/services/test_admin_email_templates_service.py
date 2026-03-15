"""
Unit tests for AdminEmailTemplatesService.
"""

import pytest
from unittest.mock import patch

from app.services.admin_email_templates_service import AdminEmailTemplatesService

class TestAdminEmailTemplatesService:
    @patch('app.services.admin_email_templates_service.mongodb')
    def test_get_template_mappings_exception_fallback(self, mock_mongodb):
        """Test that get_template_mappings returns default mappings when an exception occurs."""
        # Setup mock to raise an exception
        mock_mongodb.find_one.side_effect = Exception("Database connection error")

        # Call the method
        result = AdminEmailTemplatesService.get_template_mappings()

        # Verify result is the default mapping
        expected = {
            'auftrag_confirmation': 'auftrag_confirmation',
            'password_reset': 'password_reset',
            'user_welcome': 'user_welcome',
        }
        assert result == expected

        # Verify mock was called correctly
        mock_mongodb.find_one.assert_called_once_with('settings', {'key': AdminEmailTemplatesService.SETTINGS_KEY_MAP})
