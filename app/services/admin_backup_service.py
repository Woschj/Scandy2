"""
Simplified Admin Backup Service using SimpleBackup
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from app.utils.simple_backup import simple_backup

logger = logging.getLogger(__name__)

class AdminBackupService:
    """Simplified Service for Admin Backup functions"""
    
    @staticmethod
    def get_backup_list() -> List[Dict[str, Any]]:
        return simple_backup.list_backups()

    @staticmethod
    def create_backup() -> Tuple[bool, str, Optional[str]]:
        filename = simple_backup.create_backup()
        if filename:
            return True, f"Backup '{filename}' erfolgreich erstellt", filename
        return False, "Fehler beim Erstellen des Backups", None

    @staticmethod
    def restore_backup(filename: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        success, message = simple_backup.restore_backup(filename)
        return success, message, None

    @staticmethod
    def delete_backup(filename: str) -> Tuple[bool, str]:
        if simple_backup.delete_backup(filename):
            return True, f"Backup '{filename}' erfolgreich gelöscht"
        return False, "Backup nicht gefunden"

    @staticmethod
    def fix_dashboard_after_backup():
        """Placeholder for dashboard fixing logic if needed"""
        return {'total': 0}

    @staticmethod
    def _fix_missing_created_at_fields():
        """Placeholder for field fixing logic if needed"""
        return 0
