import os
import json
import zipfile
import shutil
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from bson import json_util
from app.models.mongodb_database import mongodb

logger = logging.getLogger(__name__)

class SimpleBackup:
    def __init__(self, backup_dir=None):
        # Use project root for backups if not specified
        project_root = Path(__file__).resolve().parents[2]
        self.backup_dir = Path(backup_dir or os.environ.get('SCANDY_BACKUP_DIR', project_root / 'backups'))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir = Path('app/static/uploads')

    def create_backup(self, include_media=True):
        """Creates a backup of the database and optionally the media files."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"scandy_backup_{timestamp}"
            zip_filename = f"{backup_name}.zip"
            zip_path = self.backup_dir / zip_filename

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)

                # Export MongoDB collections to JSON
                db_path = tmp_path / 'database'
                db_path.mkdir()
                collections = mongodb.db.list_collection_names()
                for coll in collections:
                    if coll.startswith('system.'):
                        continue
                    docs = list(mongodb.db[coll].find())
                    with open(db_path / f"{coll}.json", 'w', encoding='utf-8') as f:
                        f.write(json_util.dumps(docs, indent=2, ensure_ascii=False))

                # Copy Uploads directory
                if include_media and self.upload_dir.exists():
                    shutil.copytree(self.upload_dir, tmp_path / 'uploads', dirs_exist_ok=True)

                # Zip the temporary directory content
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(tmp_path):
                        for file in files:
                            p = Path(root) / file
                            zipf.write(p, p.relative_to(tmp_path))

            logger.info(f"Backup created: {zip_path}")
            return zip_filename
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def restore_backup(self, zip_filename):
        """Restores a backup from a zip file."""
        try:
            zip_path = self.backup_dir / zip_filename
            if not zip_path.exists():
                return False, "Backup-Datei nicht gefunden"

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    zipf.extractall(tmp_path)

                # Restore Database from JSON files
                db_path = tmp_path / 'database'
                if db_path.exists():
                    for json_file in db_path.glob('*.json'):
                        coll_name = json_file.stem
                        with open(json_file, 'r', encoding='utf-8') as f:
                            docs = json_util.loads(f.read())

                        # We don't want to overwrite users to avoid locking ourselves out
                        if coll_name == 'users':
                            continue

                        mongodb.db[coll_name].delete_many({})
                        if docs:
                            mongodb.db[coll_name].insert_many(docs)

                # Restore Uploads
                uploads_path = tmp_path / 'uploads'
                if uploads_path.exists():
                    # Clear current uploads first? User didn't specify, but usually better.
                    # For now, we use dirs_exist_ok=True which overwrites but keeps extra files.
                    shutil.copytree(uploads_path, self.upload_dir, dirs_exist_ok=True)

            logger.info(f"Backup restored: {zip_filename}")
            return True, "Backup erfolgreich wiederhergestellt"
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False, f"Fehler bei der Wiederherstellung: {str(e)}"

    def list_backups(self):
        """Lists all available backups."""
        try:
            backups = []
            for f in self.backup_dir.glob('*.zip'):
                backups.append({
                    'filename': f.name,
                    'size': self._format_size(f.stat().st_size),
                    'created_at': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
            return sorted(backups, key=lambda x: x['created_at'], reverse=True)
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    def delete_backup(self, zip_filename):
        """Deletes a backup file."""
        try:
            zip_path = self.backup_dir / zip_filename
            if zip_path.exists():
                zip_path.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            return False

    def _format_size(self, size_bytes):
        """Formats size in bytes to a human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

simple_backup = SimpleBackup()
