"""
Admin Notification Service - Wrapper für UnifiedNotificationService

Dieser Service behält die alte API bei, verwendet aber den neuen
UnifiedNotificationService für die eigentliche Funktionalität.
"""

from typing import List, Dict, Any, Tuple, Optional
from app.services.unified_notification_service import unified_notification_service

class AdminNotificationService:
    """Wrapper für Admin-Benachrichtigungsfunktionen"""

    @staticmethod
    def get_notifications() -> List[Dict[str, Any]]:
        """Holt alle Benachrichtigungen"""
        return unified_notification_service.get_notifications()

    @staticmethod
    def create_notification(notification_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Erstellt eine neue Benachrichtigung"""
        return unified_notification_service.create_notification(notification_data)

    @staticmethod
    def mark_notification_as_read(notification_id: str) -> Tuple[bool, str]:
        """Markiert eine Benachrichtigung als gelesen"""
        return unified_notification_service.mark_notification_as_read(notification_id)

    @staticmethod
    def delete_notification(notification_id: str) -> Tuple[bool, str]:
        """Löscht eine Benachrichtigung"""
        return unified_notification_service.delete_notification(notification_id)

    @staticmethod
    def get_unread_notifications() -> List[Dict[str, Any]]:
        """Holt alle ungelesenen Benachrichtigungen"""
        return unified_notification_service.get_unread_notifications()

    @staticmethod
    def get_notification_count() -> Dict[str, int]:
        """Holt die Anzahl der Benachrichtigungen nach Typ"""
        stats = unified_notification_service.get_notification_count()
        return stats

    @staticmethod
    def create_system_notification(title: str, message: str, notification_type: str = 'info', priority: str = 'normal') -> Tuple[bool, str]:
        """Erstellt eine System-Benachrichtigung"""
        return unified_notification_service.create_system_notification(title, message, notification_type, priority)

    @staticmethod
    def create_low_stock_notification(consumable_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Erstellt eine Benachrichtigung bei niedrigem Lagerbestand"""
        return unified_notification_service.create_low_stock_notification(consumable_data)

    @staticmethod
    def create_overdue_notification(lending_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Erstellt eine Benachrichtigung bei überfälligen Ausleihen"""
        return unified_notification_service.create_overdue_notification(lending_data)

    @staticmethod
    def clear_old_notifications(days: int = 30) -> Tuple[bool, str, int]:
        """Löscht alte Benachrichtigungen"""
        return unified_notification_service.clear_old_notifications(days)

    @staticmethod
    def get_notification_statistics() -> Dict[str, Any]:
        """Holt Statistiken zu Benachrichtigungen"""
        return unified_notification_service.get_notification_statistics()
