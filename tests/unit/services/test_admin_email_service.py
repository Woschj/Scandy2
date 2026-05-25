import pytest
from unittest.mock import patch, MagicMock
from app.services.admin_email_service import AdminEmailService

class TestAdminEmailService:
    @patch('app.services.admin_email_service.mongodb')
    def test_get_email_settings(self, mock_mongodb):
        mock_mongodb.find.return_value = [
            {'key': 'email_test', 'value': 'test_value'},
            {'key': 'email_other', 'value': 'other_value'}
        ]

        settings = AdminEmailService.get_email_settings()

        mock_mongodb.find.assert_called_once_with('settings', {'key': {'$regex': '^email_'}})
        assert settings == {'email_test': 'test_value', 'email_other': 'other_value'}
