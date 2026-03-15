import pytest
from unittest.mock import patch, MagicMock
from app.services.notification_service import NotificationService
import datetime

@pytest.fixture
def notification_service():
    with patch('app.services.notification_service.EmailService'):
        return NotificationService()

def test_create_notice_success(notification_service):
    with patch('app.services.notification_service.mongodb') as mock_mongodb:
        mock_mongodb.insert_one.return_value = MagicMock(inserted_id='123')

        success, message = notification_service.create_notice(
            title="Test Notice",
            message="This is a test notice",
            priority=2,
            is_active=True
        )

        assert success is True
        assert "erfolgreich" in message.lower()
        mock_mongodb.insert_one.assert_called_once()

        # Check args
        args, kwargs = mock_mongodb.insert_one.call_args
        assert args[0] == 'homepage_notices'
        assert args[1]['title'] == "Test Notice"
        assert args[1]['message'] == "This is a test notice"
        assert args[1]['priority'] == 2
        assert args[1]['is_active'] is True
        assert 'created_at' in args[1]
        assert args[1]['created_by'] == 'system'

def test_create_notice_failure(notification_service):
    with patch('app.services.notification_service.mongodb') as mock_mongodb:
        mock_mongodb.insert_one.side_effect = Exception("DB Error")

        success, message = notification_service.create_notice(
            title="Test Notice",
            message="This is a test notice"
        )

        assert success is False
        assert "fehler" in message.lower()
