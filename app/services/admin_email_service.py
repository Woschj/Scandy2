"""
Admin Email Service - Wrapper für UnifiedNotificationService

Dieser Service behält die alte API bei, verwendet aber den neuen
UnifiedNotificationService für die eigentliche Funktionalität.
"""

from typing import Dict, Any, Tuple
from app.services.unified_notification_service import unified_notification_service

class AdminEmailService:
    """Wrapper für E-Mail-Funktionen"""

    @staticmethod
    def send_notification_email(recipient_email: str, subject: str, message: str) -> Tuple[bool, str]:
        """Sendet eine einfache Benachrichtigungs-E-Mail"""
        return unified_notification_service.send_notification_email(recipient_email, subject, message)

    @staticmethod
    def send_low_stock_notification(consumable_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Sendet eine Benachrichtigung bei niedrigem Lagerbestand"""
        return unified_notification_service.send_low_stock_notification(consumable_data)

    @staticmethod
    def send_overdue_notification(lending_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Sendet eine Benachrichtigung bei überfälligen Ausleihen"""
        return unified_notification_service.send_overdue_notification(lending_data)

    @staticmethod
    def get_email_settings() -> Dict[str, Any]:
        """Holt die E-Mail-Einstellungen"""
        return unified_notification_service.get_notification_settings()

    @staticmethod
    def get_email_statistics() -> Dict[str, Any]:
        """Holt E-Mail-Statistiken"""
        return unified_notification_service.get_notification_statistics()
