import pytest
from unittest.mock import patch, MagicMock
from app.services.admin_notification_service import AdminNotificationService

@pytest.fixture
def admin_notification_service():
    return AdminNotificationService()

def test_create_system_notification_success(admin_notification_service):
    with patch.object(AdminNotificationService, 'create_notification') as mock_create_notification:
        mock_create_notification.return_value = (True, "Benachrichtigung erfolgreich erstellt", "123")

        success, message = admin_notification_service.create_system_notification(
            title="System Alert",
            message="This is a system alert",
            notification_type="warning",
            priority="high"
        )

        assert success is True
        assert message == "Benachrichtigung erfolgreich erstellt"

        mock_create_notification.assert_called_once_with({
            'title': "System Alert",
            'message': "This is a system alert",
            'type': "warning",
            'priority': "high"
        })

def test_create_system_notification_default_args(admin_notification_service):
    with patch.object(AdminNotificationService, 'create_notification') as mock_create_notification:
        mock_create_notification.return_value = (True, "Benachrichtigung erfolgreich erstellt", "123")

        success, message = admin_notification_service.create_system_notification(
            title="System Alert",
            message="This is a system alert"
        )

        assert success is True
        assert message == "Benachrichtigung erfolgreich erstellt"

        mock_create_notification.assert_called_once_with({
            'title': "System Alert",
            'message': "This is a system alert",
            'type': "info",
            'priority': "normal"
        })

def test_create_system_notification_failure(admin_notification_service):
    with patch.object(AdminNotificationService, 'create_notification') as mock_create_notification:
        mock_create_notification.side_effect = Exception("DB Error")

        success, message = admin_notification_service.create_system_notification(
            title="System Alert",
            message="This is a system alert"
        )

        assert success is False
        assert message == "Fehler beim Erstellen der System-Benachrichtigung: [Interner Fehler]"
        mock_create_notification.assert_called_once()
