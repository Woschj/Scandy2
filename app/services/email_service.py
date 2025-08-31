"""
Email Service - Wrapper für UnifiedNotificationService

Dieser Service behält die alte API bei, verwendet aber den neuen
UnifiedNotificationService für die eigentliche Funktionalität.
"""

from typing import Dict, Any, Tuple
from app.services.unified_notification_service import unified_notification_service

class EmailService:
    """Wrapper für E-Mail-Funktionen"""

    @staticmethod
    def send_notification_email(user_email: str, subject: str, message: str, notification_type: str = "info") -> bool:
        """Sendet eine Benachrichtigungs-E-Mail"""
        success, _ = unified_notification_service.send_notification_email(user_email, subject, message)
        return success

    @staticmethod
    def send_ticket_notification_email(user_email: str, ticket_data: Dict[str, Any], action: str) -> bool:
        """Sendet eine Ticket-Benachrichtigungs-E-Mail"""
        return unified_notification_service.send_ticket_notification_email(user_email, ticket_data, action)

    @staticmethod
    def send_lending_notification_email(user_email: str, lending_data: Dict[str, Any], action: str) -> bool:
        """Sendet eine Ausleih-Benachrichtigungs-E-Mail"""
        return unified_notification_service.send_lending_notification_email(user_email, lending_data, action)
