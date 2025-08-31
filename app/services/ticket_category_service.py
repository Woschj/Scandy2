"""
Service für Ticket-Kategorien-Verwaltung

Dieser Service verwaltet Ticket-Kategorien pro Abteilung
und stellt sicher, dass Nutzende nur die Ticket-Kategorien ihrer Abteilung sehen.
"""

from typing import List, Dict, Any, Optional
from flask import g
import logging
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class TicketCategoryService:
    """Service für department-scoped Ticket-Kategorien"""
    
    @classmethod
    def get_current_department(cls) -> Optional[str]:
        """Holt das aktuelle Department aus dem Request-Context"""
        try:
            return getattr(g, 'current_department', None)
        except Exception:
            return None
    
    @classmethod
    def get_ticket_categories_for_department(cls, department: Optional[str] = None) -> List[str]:
        """
        Holt Ticket-Kategorien für eine bestimmte Abteilung
        
        Args:
            department: Abteilung (falls None, wird aktuelle Abteilung verwendet)
            
        Returns:
            Liste der Ticket-Kategorien für die Abteilung
        """
        if department is None:
            department = cls.get_current_department()
        
        if not department:
            logger.warning("Kein Department verfügbar für Ticket-Kategorien")
            return []
        
        try:
            # Lade department-spezifische Ticket-Kategorien
            categories = mongodb.find('ticket_categories', {
                'department': department,
                'deleted': {'$ne': True}
            })
            
            category_names = []
            for category in categories:
                name = category.get('name', '').strip()
                if name:
                    category_names.append(name)
            
            # Kein Fallback mehr: Ticket-Kategorien sind strikt abteilungsgebunden
            
            return sorted(category_names, key=str.casefold)
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Ticket-Kategorien für {department}: {e}")
            return []

# Globale Instanz für einfache Verwendung
ticket_category_service = TicketCategoryService()
