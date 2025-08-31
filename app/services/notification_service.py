"""
Notification Service - Wrapper für UnifiedNotificationService

Dieser Service behält die alte API bei, verwendet aber den neuen
UnifiedNotificationService für die eigentliche Funktionalität.
"""

from typing import Dict, Any, Tuple
from app.services.unified_notification_service import unified_notification_service

class NotificationService:
    """Wrapper für Benachrichtigungsfunktionen"""

    @staticmethod
    def send_system_notification(user_email: str, subject: str, message: str, notification_type: str = "info") -> bool:
        """Sendet eine System-Benachrichtigung per E-Mail"""
        return unified_notification_service.send_system_notification(user_email, subject, message, notification_type)

    @staticmethod
    def get_notification_settings() -> Dict[str, Any]:
        """Holt die Benachrichtigungseinstellungen"""
        return unified_notification_service.get_notification_settings()

    @staticmethod
    def update_notification_settings(settings: Dict[str, Any]) -> Tuple[bool, str]:
        """Aktualisiert die Benachrichtigungseinstellungen"""
        return unified_notification_service.update_notification_settings(settings)
