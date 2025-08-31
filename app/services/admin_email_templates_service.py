"""
Admin Email Templates Service - Wrapper für UnifiedNotificationService

Dieser Service behält die alte API bei, verwendet aber den neuen
UnifiedNotificationService für die eigentliche Funktionalität.
"""

from typing import List, Dict, Any, Tuple, Optional
from app.services.unified_notification_service import unified_notification_service

class AdminEmailTemplatesService:
    """Wrapper für E-Mail-Template-Funktionen"""

    @staticmethod
    def get_email_templates() -> List[Dict[str, Any]]:
        """Holt alle E-Mail-Templates"""
        return unified_notification_service.get_email_templates()

    @staticmethod
    def get_email_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
        """Holt ein E-Mail-Template anhand der ID"""
        return unified_notification_service.get_email_template_by_id(template_id)

    @staticmethod
    def create_email_template(template_data: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """Erstellt ein neues E-Mail-Template"""
        return unified_notification_service.create_email_template(template_data)

    @staticmethod
    def update_email_template(template_id: str, template_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Aktualisiert ein E-Mail-Template"""
        return unified_notification_service.update_email_template(template_id, template_data)

    @staticmethod
    def delete_email_template(template_id: str) -> Tuple[bool, str]:
        """Löscht ein E-Mail-Template"""
        return unified_notification_service.delete_email_template(template_id)

    @staticmethod
    def render_email_template(template_id: str, variables: Dict[str, Any]) -> Tuple[bool, str, str]:
        """Rendert ein E-Mail-Template mit Variablen"""
        return unified_notification_service.render_email_template(template_id, variables)
