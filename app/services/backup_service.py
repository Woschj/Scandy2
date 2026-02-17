"""
Simplified Backup Service for Scandy
"""
from typing import Dict, Any, List, Tuple, Optional
from app.utils.simple_backup import simple_backup
import logging

logger = logging.getLogger(__name__)

class BackupService:
    """Simplified Service for all backup operations"""
    
    def create_backup(self, include_files: bool = True) -> Tuple[bool, str, Optional[str]]:
        filename = simple_backup.create_backup(include_media=include_files)
        if filename:
            return True, f"Backup erfolgreich erstellt: {filename}", filename
        return False, "Fehler beim Erstellen des Backups", None

    def restore_backup(self, backup_path: str) -> Tuple[bool, str]:
        # backup_path here is likely just the filename or full path
        import os
        filename = os.path.basename(backup_path)
        success, message = simple_backup.restore_backup(filename)
        return success, message

    def get_backup_list(self) -> List[Dict[str, Any]]:
        return simple_backup.list_backups()

    def delete_backup(self, backup_path: str) -> Tuple[bool, str]:
        import os
        filename = os.path.basename(backup_path)
        if simple_backup.delete_backup(filename):
            return True, "Backup erfolgreich gelöscht"
        return False, "Backup nicht gefunden"
