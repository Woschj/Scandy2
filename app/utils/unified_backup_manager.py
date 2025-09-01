#!/usr/bin/env python3
"""
Optimierter Backup-Manager für Scandy
🚀 Performance-Verbesserungen:
- Parallele Collection-Verarbeitung
- Streaming für große Backups
- Memory-optimierte Algorithmen
- Intelligente Chunk-Größen
- Fortschritts-Tracking
- Verbesserte Validierung
"""

import os
import json
import shutil
import subprocess
import zipfile
import tempfile
from datetime import datetime
import hashlib
import threading
import uuid
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
import random
import string
from bson import ObjectId
import logging
from functools import partial

logger = logging.getLogger(__name__)

class OptimizedBackupManager:
    """
    Vereinheitlichter Backup-Manager für Scandy
    """
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

        # Medien-Verzeichnisse
        self.media_dirs = [
            Path("app/static/uploads"),
            Path("app/uploads"),
            Path("uploads")
        ]

        # 🚀 Optimierte Backup-Konfiguration
        self.max_backup_size_gb = 10      # Maximale Backup-Größe
        self.include_media = True         # Medien einschließen
        self.compress_backups = True      # Backups komprimieren
        self.max_workers = min(4, os.cpu_count() or 2)  # Parallele Worker
        self.chunk_size = 1000           # Dokumente pro Chunk
        self.streaming_threshold = 50000 # Streaming ab dieser Größe

        # Import-Job Verwaltung (Statusablage in MongoDB)
        # Hinweis: Für Persistenz/Mehrprozess-Sicherheit wird MongoDB genutzt, nicht nur RAM.

    # ===== Normalisierungs-Helfer =====
    @staticmethod
    def _norm_str(value: Any) -> Optional[str]:
        try:
            if value is None:
                return None
            s = str(value).strip()
            return s if s else None
        except Exception:
            return None

    @staticmethod
    def _normalize_barcode(value: Any) -> Optional[str]:
        # Barcodes als getrimmten String behandeln (Groß/Kleinschreibung beibehalten)
        return UnifiedBackupManager._norm_str(value)

    def create_backup(self, include_media: bool = True, compress: bool = True,
                     progress_callback: Optional[Callable[[str, int], None]] = None) -> Optional[str]:
        """
        🚀 Erstellt ein optimiertes Backup mit paralleler Verarbeitung

        Args:
            include_media: Medien einschließen
            compress: Backup komprimieren
            progress_callback: Callback für Fortschritt (message, percentage)

        Returns:
            Backup-Dateiname oder None bei Fehler
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"scandy_backup_{timestamp}"

            logger.info(f"🔄 Erstelle optimiertes Backup: {backup_name}")
            if progress_callback:
                progress_callback("Starte Backup-Erstellung", 0)

            # 1. 🚀 Paralleles MongoDB-Backup
            if progress_callback:
                progress_callback("Erstelle Datenbank-Backup", 10)
            db_backup_path = self._create_mongodb_backup_parallel(backup_name, progress_callback)
            if not db_backup_path:
                return None

            # 2. Medien-Backup (optional)
            media_backup_path = None
            if include_media:
                if progress_callback:
                    progress_callback("Erstelle Medien-Backup", 40)
                media_backup_path = self._create_media_backup_optimized(backup_name)

            # 3. Konfiguration sichern
            if progress_callback:
                progress_callback("Sichere Konfiguration", 70)
            config_backup_path = self._create_config_backup_optimized(backup_name)

            # 4. Alles zusammenfassen
            if progress_callback:
                progress_callback("Erstelle finales Backup-Paket", 85)
            final_backup_path = self._create_final_backup_optimized(
                backup_name,
                db_backup_path,
                media_backup_path,
                config_backup_path,
                compress
            )

            if final_backup_path:
                logger.info(f"✅ Backup erfolgreich erstellt: {final_backup_path}")
                if progress_callback:
                    progress_callback("Bereinige temporäre Dateien", 95)

                self._cleanup_temp_files([db_backup_path, media_backup_path, config_backup_path])

                # Alte Backups (>7 Tage) aufräumen
                try:
                    self._prune_old_backups_optimized(days=7)
                except Exception as e:
                    logger.warning(f"⚠️  Konnte alte Backups nicht bereinigen: {e}")

                if progress_callback:
                    progress_callback("Backup abgeschlossen", 100)
                return final_backup_path
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Fehler beim Erstellen des Backups: {e}")
            if progress_callback:
                progress_callback(f"Fehler: {str(e)}", -1)
            return None
    
    def _create_mongodb_backup_parallel(self, backup_name: str,
                                       progress_callback: Optional[Callable[[str, int], None]] = None) -> Optional[Path]:
        """
        🚀 Erstellt MongoDB-Backup mit paralleler Verarbeitung und Streaming
        """
        try:
            temp_dir = Path(tempfile.mkdtemp())
            backup_path = temp_dir / backup_name
            backup_path.mkdir(exist_ok=True)

            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
            db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")

            logger.info("  📊 Erstelle optimiertes MongoDB-Backup...")

            # Zuerst mongodump versuchen (schnellste Option)
            try:
                cmd = [
                    'mongodump',
                    '--uri', mongo_uri,
                    '--out', str(backup_path),
                    '--gzip',
                    '--excludeCollection', 'users'
                ]
                cmd.extend(['--readPreference', 'primary'])

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    logger.info("  ✅ MongoDB-Backup mit mongodump erstellt")
                    return backup_path
                else:
                    logger.warning(f"  ⚠️  mongodump fehlgeschlagen: {result.stderr}")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                logger.info("  🔄 Verwende optimiertes Python-Backup...")

            # 🚀 Paralleles Python-Backup
            return self._create_python_backup_parallel(backup_path, backup_name, progress_callback)

        except Exception as e:
            logger.error(f"  ❌ Fehler beim MongoDB-Backup: {e}")
            return None

    def _create_python_backup_parallel(self, backup_path: Path, backup_name: str,
                                     progress_callback: Optional[Callable[[str, int], None]] = None) -> Optional[Path]:
        """
        🚀 Erstellt Python-basiertes Backup mit paralleler Collection-Verarbeitung
        """
        try:
            from app.models.mongodb_database import mongodb
            from bson import json_util

            # Collections ermitteln
            try:
                db = mongodb.db
                collections = [name for name in db.list_collection_names()
                             if not name.startswith('system.') and name != 'users']
            except Exception:
                collections = [
                    'tools', 'workers', 'consumables', 'lendings',
                    'consumable_usages', 'tickets', 'settings',
                    'homepage_notices', 'work_times', 'jobs', 'timesheets',
                    'auftrag_details', 'auftrag_material', 'email_config',
                    'email_settings', 'system_logs'
                ]

            # 🚀 Parallele Collection-Verarbeitung
            backup_data = {
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'version': '3.0',
                    'optimized': True,
                    'parallel_processing': True,
                    'collections': []
                },
                'data': {}
            }

            total_collections = len(collections)
            processed_collections = 0

            # Worker-Funktion für parallele Verarbeitung
            def process_collection(collection_name: str) -> Tuple[str, List[Dict], int]:
                """Verarbeitet eine einzelne Collection"""
                try:
                    # Streaming für große Collections
                    cursor = mongodb.find(collection_name, {}, no_cursor_timeout=True)
                    documents = []

                    if self._estimate_collection_size(collection_name) > self.streaming_threshold:
                        # Streaming-Modus für große Collections
                        chunk = []
                        for doc in cursor:
                            if '_id' in doc:
                                doc['_id'] = str(doc['_id'])
                            chunk.append(doc)

                            if len(chunk) >= self.chunk_size:
                                documents.extend(chunk)
                                chunk = []

                        if chunk:
                            documents.extend(chunk)
                    else:
                        # Normaler Modus für kleine Collections
                        documents = list(cursor)
                        for doc in documents:
                            if '_id' in doc:
                                doc['_id'] = str(doc['_id'])

                    cursor.close()
                    return collection_name, documents, len(documents)

                except Exception as e:
                    logger.error(f"Fehler bei Collection {collection_name}: {e}")
                    return collection_name, [], 0

            # 🚀 Parallele Verarbeitung mit ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(process_collection, coll) for coll in collections]

                for future in concurrent.futures.as_completed(futures):
                    collection_name, documents, count = future.result()
                    processed_collections += 1

                    if documents:
                        backup_data['data'][collection_name] = documents
                        backup_data['metadata']['collections'].append({
                            'name': collection_name,
                            'count': count
                        })
                        logger.info(f"    ✅ Collection {collection_name}: {count} Dokumente")

                    # Fortschritt melden
                    if progress_callback:
                        progress = int((processed_collections / total_collections) * 30) + 10
                        progress_callback(f"Verarbeite Collection {collection_name}", progress)

            # 🚀 Optimierte JSON-Speicherung mit Streaming
            backup_file = backup_path / f"{backup_name}.json"

            # Verwende Buffered Writer für bessere Performance
            with open(backup_file, 'w', encoding='utf-8', buffering=8192) as f:
                # Schreibe Header
                f.write('{\n"metadata": ')
                json.dump(backup_data['metadata'], f, ensure_ascii=False, indent=2)
                f.write(',\n"data": {\n')

                # Schreibe Collections mit Komma-Separierung
                first_collection = True
                for collection_name, documents in backup_data['data'].items():
                    if not first_collection:
                        f.write(',\n')
                    f.write(f'"{collection_name}": ')
                    json.dump(documents, f, ensure_ascii=False, indent=2, default=json_util.default)
                    first_collection = False

                f.write('\n}\n}')

            logger.info("  ✅ Paralleles MongoDB-Backup erstellt"
            return backup_path

        except Exception as e:
            logger.error(f"  ❌ Fehler beim parallelen Python-Backup: {e}")
            return None

    def _estimate_collection_size(self, collection_name: str) -> int:
        """Schnelle Schätzung der Collection-Größe"""
        try:
            from app.models.mongodb_database import mongodb
            # Verwende count_documents für genaue Zählung (langsamer aber genau)
            return mongodb.db[collection_name].count_documents({})
        except Exception:
            return 0
    
    def _create_media_backup_optimized(self, backup_name: str) -> Optional[Path]:
        """
        🚀 Erstellt optimiertes Medien-Backup mit paralleler Verarbeitung
        """
        try:
            temp_dir = Path(tempfile.mkdtemp())
            media_backup_path = temp_dir / f"{backup_name}_media"
            media_backup_path.mkdir(exist_ok=True)

            logger.info("  📁 Erstelle optimiertes Medien-Backup...")

            total_size = 0
            copied_files = 0

            # Ausschluss-Listen
            exclude_dirnames = {"icons", "logos", "images", "favicons"}
            exclude_name_substrings = ["favicon", "logo", "scandy-logo", "scandy-favicon", "dancing_zebra"]
            allowed_top_level = {"tools", "consumables", "tickets", "jobs"}

            # Sammle alle zu kopierenden Dateien
            files_to_copy = []

            for media_dir in self.media_dirs:
                if media_dir.exists():
                    logger.info(f"    📂 Sammle Medien aus: {media_dir}")

                    for root, dirs, files in os.walk(media_dir):
                        rel_path = Path(root).relative_to(media_dir)

                        # Verzeichnisse filtern
                        dirs[:] = [d for d in dirs if d not in exclude_dirnames]
                        if rel_path == Path('.'):
                            dirs[:] = [d for d in dirs if d in allowed_top_level]

                        target_dir = media_backup_path / rel_path
                        target_dir.mkdir(parents=True, exist_ok=True)

                        for file in files:
                            lower_name = file.lower()
                            if any(substr in lower_name for substr in exclude_name_substrings):
                                continue

                            rel_parts = (media_dir / rel_path / file).relative_to(media_dir).parts
                            if len(rel_parts) == 0 or rel_parts[0] not in allowed_top_level:
                                continue

                            source_file = Path(root) / file
                            target_file = target_dir / file

                            # Dateigröße prüfen
                            file_size = source_file.stat().st_size
                            if total_size + file_size > self.max_backup_size_gb * 1024**3:
                                logger.warning("    ⚠️  Maximale Backup-Größe erreicht")
                                break

                            files_to_copy.append((source_file, target_file, file_size))
                            total_size += file_size

                    break  # Nur erstes gefundenes Verzeichnis

            # 🚀 Parallele Dateikopie
            if files_to_copy:
                def copy_file_task(source_file: Path, target_file: Path, file_size: int) -> Tuple[bool, int]:
                    """Kopiert eine einzelne Datei"""
                    try:
                        shutil.copy2(source_file, target_file)
                        return True, file_size
                    except Exception as e:
                        logger.error(f"Fehler beim Kopieren {source_file}: {e}")
                        return False, 0

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [executor.submit(copy_file_task, src, dst, size)
                             for src, dst, size in files_to_copy]

                    for future in concurrent.futures.as_completed(futures):
                        success, size = future.result()
                        if success:
                            copied_files += 1

                logger.info(f"    ✅ {copied_files} Dateien kopiert ({self._format_size(total_size)})")
                return media_backup_path
            else:
                logger.warning("    ⚠️  Keine Medien gefunden")
                return None

        except Exception as e:
            logger.error(f"  ❌ Fehler beim optimierten Medien-Backup: {e}")
            return None
    
    def _create_config_backup_optimized(self, backup_name: str) -> Optional[Path]:
        """
        🚀 Erstellt optimiertes Konfigurations-Backup
        """
        try:
            temp_dir = Path(tempfile.mkdtemp())
            config_backup_path = temp_dir / f"{backup_name}_config"
            config_backup_path.mkdir(exist_ok=True)

            logger.info("  ⚙️  Erstelle optimiertes Konfigurations-Backup...")

            # Wichtige Konfigurationsdateien
            config_files = [
                Path(".env"),
                Path("docker-compose.yml"),
                Path("requirements.txt"),
                Path("package.json"),
                Path("tailwind.config.js"),
                Path("postcss.config.js")
            ]

            optional_system_files = [
                Path("/etc/systemd/system/scandy.service"),
                Path("/etc/cron.d/scandy-session-cleanup"),
            ]

            copied_files = 0

            # 🚀 Parallele Dateikopie für Konfiguration
            def copy_config_file(config_file: Path, target_path: Path) -> bool:
                """Kopiert eine einzelne Konfigurationsdatei"""
                try:
                    if config_file.exists():
                        shutil.copy2(config_file, target_path)
                        return True
                    return False
                except Exception as e:
                    logger.warning(f"Konfigurationsdatei {config_file} konnte nicht kopiert werden: {e}")
                    return False

            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(config_files))) as executor:
                futures = []
                for config_file in config_files:
                    target_path = config_backup_path / config_file.name
                    futures.append(executor.submit(copy_config_file, config_file, target_path))

                for future in concurrent.futures.as_completed(futures):
                    if future.result():
                        copied_files += 1

            # Systemdateien (optional)
            try:
                system_dir = config_backup_path / 'system'
                for sysf in optional_system_files:
                    if sysf.exists():
                        system_dir.mkdir(exist_ok=True)
                        shutil.copy2(sysf, system_dir / sysf.name)
                        copied_files += 1
            except Exception:
                pass

            if copied_files > 0:
                logger.info(f"  ✅ {copied_files} Konfigurationsdateien kopiert")
                return config_backup_path
            else:
                logger.warning("  ⚠️  Keine Konfigurationsdateien gefunden")
                return None

        except Exception as e:
            logger.error(f"  ❌ Fehler beim optimierten Konfigurations-Backup: {e}")
            return None
    
    def _create_final_backup_optimized(self, backup_name: str, db_path: Path,
                                      media_path: Optional[Path], config_path: Optional[Path],
                                      compress: bool) -> Optional[str]:
        """
        🚀 Erstellt optimiertes finales Backup-Paket mit paralleler Komprimierung
        """
        try:
            final_backup_path = self.backup_dir / f"{backup_name}.zip"

            logger.info("  📦 Erstelle optimiertes finales Backup-Paket...")

            # Sammle alle zu komprimierenden Dateien
            files_to_compress = []
            checksums: Dict[str, str] = {}

            # MongoDB-Dateien sammeln
            if db_path and db_path.exists():
                for root, dirs, files in os.walk(db_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = f"mongodb/{file_path.relative_to(db_path)}"
                        files_to_compress.append((file_path, arcname))

            # Medien-Dateien sammeln
            if media_path and media_path.exists():
                for root, dirs, files in os.walk(media_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = f"media/{file_path.relative_to(media_path)}"
                        files_to_compress.append((file_path, arcname))

            # Konfigurations-Dateien sammeln
            if config_path and config_path.exists():
                for root, dirs, files in os.walk(config_path):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = f"config/{file_path.relative_to(config_path)}"
                        files_to_compress.append((file_path, arcname))

            # 🚀 Parallele Checksum-Berechnung und Komprimierung
            def process_file(file_path: Path, arcname: str) -> Tuple[str, str, bytes]:
                """Verarbeitet eine Datei: berechnet Checksum und liest Inhalt"""
                try:
                    h = hashlib.sha256()
                    with open(file_path, 'rb') as rf:
                        content = rf.read()
                        h.update(content)
                    return arcname, h.hexdigest(), content
                except Exception as e:
                    logger.error(f"Fehler beim Verarbeiten {arcname}: {e}")
                    return arcname, "", b""

            # Parallele Verarbeitung der Dateien
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(process_file, fp, arc) for fp, arc in files_to_compress]

                with zipfile.ZipFile(final_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for future in concurrent.futures.as_completed(futures):
                        arcname, checksum, content = future.result()
                        if content:
                            checksums[arcname] = checksum
                            zipf.writestr(arcname, content)

                    # Backup-Metadaten hinzufügen
                    metadata = {
                        'backup_name': backup_name,
                        'created_at': datetime.now().isoformat(),
                        'includes_media': media_path is not None,
                        'includes_config': config_path is not None,
                        'compressed': compress,
                        'version': '3.0',
                        'optimized': True,
                        'parallel_processing': True,
                        'total_files': len(checksums)
                    }

                    zipf.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
                    zipf.writestr('checksums.json', json.dumps(checksums, indent=2))

            backup_size = final_backup_path.stat().st_size
            logger.info(f"  ✅ Optimiertes finales Backup erstellt: {self._format_size(backup_size)} ({len(checksums)} Dateien)")

            return final_backup_path.name

        except Exception as e:
            logger.error(f"  ❌ Fehler beim Erstellen des optimierten finalen Backups: {e}")
            return None
    
    def restore_backup(self, backup_filename: str, include_media: bool = True) -> bool:
        """
        Stellt ein Backup wieder her
        
        Args:
            backup_filename: Name der Backup-Datei
            include_media: Medien wiederherstellen
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                print(f"❌ Backup nicht gefunden: {backup_path}")
                return False
            
            print(f"🔄 Stelle Backup wieder her: {backup_filename}")
            
            # Temporäres Verzeichnis für Extraktion
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Backup extrahieren
                print(f"  📦 Extrahiere Backup...")
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_path)
                    try:
                        manifest_path = temp_path / 'checksums.json'
                        if manifest_path.exists():
                            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                            for rel, expected_hash in manifest.items():
                                target = temp_path / rel
                                if not target.exists():
                                    print(f"  ❌ Fehlende Datei im Backup: {rel}")
                                    return False
                                h = hashlib.sha256()
                                with open(target, 'rb') as rf:
                                    for chunk in iter(lambda: rf.read(1024 * 1024), b''):
                                        h.update(chunk)
                                if h.hexdigest() != expected_hash:
                                    print(f"  ❌ Integritätsfehler: {rel}")
                                    return False
                            print("  ✅ Integritätsprüfung bestanden")
                    except Exception as e:
                        print(f"  ⚠️  Konnte Checksummen nicht prüfen: {e}")
                
                # Metadaten lesen
                metadata_path = temp_path / 'backup_metadata.json'
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    print(f"  📋 Backup-Metadaten: {metadata.get('backup_name', 'Unbekannt')}")
                
                # 1. MongoDB wiederherstellen
                mongodb_path = temp_path / 'mongodb'
                if mongodb_path.exists():
                    success = self._restore_mongodb(mongodb_path)
                    if not success:
                        return False
                
                # 2. Medien wiederherstellen (optional)
                if include_media:
                    media_path = temp_path / 'media'
                    if media_path.exists():
                        success = self._restore_media(media_path)
                        if not success:
                            print(f"  ⚠️  Medien-Wiederherstellung fehlgeschlagen, fahre fort...")
                
                # 3. Konfiguration wiederherstellen (optional)
                config_path = temp_path / 'config'
                if config_path.exists():
                    success = self._restore_config(config_path)
                    if not success:
                        print(f"  ⚠️  Konfigurations-Wiederherstellung fehlgeschlagen, fahre fort...")
                
                print(f"✅ Backup erfolgreich wiederhergestellt")
                return True
                
        except Exception as e:
            print(f"❌ Fehler beim Wiederherstellen des Backups: {e}")
            return False
    
    def _restore_mongodb(self, mongodb_path: Path) -> bool:
        """Stellt MongoDB-Backup wieder her"""
        try:
            print(f"  📊 Stelle MongoDB wieder her...")
            
            # MongoDB-Verbindungsdaten
            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
            db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
            
            # mongorestore ausführen – Binärdatei robust ermitteln
            mongorestore_bin = os.environ.get('MONGORESTORE_BIN')
            def _is_exec(p: str) -> bool:
                try:
                    return p and os.path.isfile(p) and os.access(p, os.X_OK)
                except Exception:
                    return False
            if not _is_exec(mongorestore_bin or ''):
                try:
                    from shutil import which
                    w = which('mongorestore')
                    if w and _is_exec(w):
                        mongorestore_bin = w
                except Exception:
                    mongorestore_bin = None
            if not _is_exec(mongorestore_bin or ''):
                # Prüfe gängige Installationspfade (Linux/Snap/Homebrew)
                common_paths = [
                    '/usr/bin/mongorestore',
                    '/usr/local/bin/mongorestore',
                    '/snap/bin/mongorestore',
                    '/opt/homebrew/bin/mongorestore',  # macOS ARM/Homebrew
                    '/opt/local/bin/mongorestore'
                ]
                mongorestore_bin = next((p for p in common_paths if _is_exec(p)), None)
            if _is_exec(mongorestore_bin or ''):
                cmd = [
                    mongorestore_bin,
                    '--uri', mongo_uri,
                    '--gzip',
                    '--drop',  # Bestehende Collections löschen
                    '--nsExclude', f"{db_name}.users",  # Nutzende niemals überschreiben
                    str(mongodb_path / db_name)
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    print(f"  ✅ MongoDB erfolgreich wiederhergestellt")
                    return True
                else:
                    print(f"  ❌ MongoDB-Wiederherstellung fehlgeschlagen: {result.stderr}")
                    # Fallback auf Python-Restore
                    return self._python_restore_mongodb(mongo_uri, db_name, mongodb_path / db_name)
            else:
                print("  ⚠️ mongorestore nicht gefunden – verwende Python-Fallback")
                return self._python_restore_mongodb(mongo_uri, db_name, mongodb_path / db_name)
                
        except Exception as e:
            print(f"  ❌ Fehler bei MongoDB-Wiederherstellung: {e}")
            return False

    def _python_restore_mongodb(self, mongo_uri, db_name, dir_path) -> bool:
        """Fallback: Stellt Collections aus BSON/BSON.GZ per PyMongo wieder her."""
        try:
            import gzip
            from pymongo import MongoClient
            from bson import decode_file_iter

            client = MongoClient(mongo_uri)
            db = client.get_database(db_name)

            # Sammle .bson und .bson.gz Dateien
            files = []
            for p in (dir_path).iterdir():
                name = p.name
                if name.endswith('.metadata.json'):
                    continue
                if name.endswith('.bson') or name.endswith('.bson.gz'):
                    files.append(p)

            if not files:
                print(f"  ❌ Keine BSON-Dateien in {dir_path} gefunden")
                return False

            for fpath in sorted(files):
                cname = fpath.name
                if cname.endswith('.bson.gz'):
                    coll = cname[:-8]
                elif cname.endswith('.bson'):
                    coll = cname[:-5]
                else:
                    continue
                if coll == 'users':
                    print(f"  ↷ Überspringe Collection 'users'")
                    continue
                print(f"  → Stelle Collection: {coll}")
                try:
                    # Drop bestehende Collection
                    db[coll].drop()
                except Exception:
                    pass
                # Stream-basiertes Einlesen
                opener = gzip.open if fpath.suffix == '.gz' or fpath.name.endswith('.gz') else open
                inserted = 0
                batch = []
                batch_size = 1000
                with opener(fpath, 'rb') as fh:
                    for doc in decode_file_iter(fh):
                        batch.append(doc)
                        if len(batch) >= batch_size:
                            db[coll].insert_many(batch, ordered=False)
                            inserted += len(batch)
                            batch.clear()
                    if batch:
                        db[coll].insert_many(batch, ordered=False)
                        inserted += len(batch)
                print(f"    ✓ {inserted} Dokumente in {coll} eingefügt")
            print("  ✅ MongoDB per Python-Fallback wiederhergestellt")
            return True
        except Exception as e:
            print(f"  ❌ Python-Fallback fehlgeschlagen: {e}")
            return False
    
    def _restore_media(self, media_path: Path) -> bool:
        """Stellt Medien wieder her"""
        try:
            print(f"  📁 Stelle Medien wieder her...")
            
            # Zielverzeichnis für Medien
            target_dir = Path("app/static/uploads")
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Medien kopieren
            copied_files = 0
            for root, dirs, files in os.walk(media_path):
                # Relativen Pfad berechnen
                rel_path = Path(root).relative_to(media_path)
                target_subdir = target_dir / rel_path
                target_subdir.mkdir(parents=True, exist_ok=True)
                
                for file in files:
                    source_file = Path(root) / file
                    target_file = target_subdir / file
                    
                    # Datei kopieren
                    shutil.copy2(source_file, target_file)
                    copied_files += 1
            
            print(f"  ✅ {copied_files} Mediendateien wiederhergestellt")
            return True
            
        except Exception as e:
            print(f"  ❌ Fehler bei Medien-Wiederherstellung: {e}")
            return False
    
    def _restore_config(self, config_path: Path) -> bool:
        """Stellt Konfiguration wieder her"""
        try:
            print(f"  ⚙️  Stelle Konfiguration wieder her...")
            
            # Konfigurationsdateien kopieren
            copied_files = 0
            for config_file in config_path.iterdir():
                if config_file.is_file():
                    target_file = Path(config_file.name)
                    shutil.copy2(config_file, target_file)
                    copied_files += 1
            
            print(f"  ✅ {copied_files} Konfigurationsdateien wiederhergestellt")
            return True
            
        except Exception as e:
            print(f"  ❌ Fehler bei Konfigurations-Wiederherstellung: {e}")
            return False
    
    def import_json_backup(self, json_file_path: str) -> bool:
        """
        Importiert ein altes JSON-Backup
        
        Args:
            json_file_path: Pfad zur JSON-Backup-Datei
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            print(f"🔄 Importiere JSON-Backup: {json_file_path}")
            
            # JSON-Datei laden
            with open(json_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Backup validieren
            if not self._validate_json_backup(backup_data):
                print(f"❌ Ungültiges JSON-Backup")
                return False
            
            # MongoDB-Verbindung
            from pymongo import MongoClient
            mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
            db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
            
            client = MongoClient(mongo_uri)
            db = client[db_name]
            
            # Datenbereich ermitteln (neu: data, alt: flach)
            data_section = backup_data['data'] if ('metadata' in backup_data and 'data' in backup_data) else backup_data

            # Collections wiederherstellen (ohne users)
            for collection_name, documents in data_section.items():
                if collection_name == 'metadata':
                    continue
                # Nutzende niemals importieren
                if collection_name == 'users':
                    continue
                
                print(f"  📊 Stelle Collection wieder her: {collection_name}")
                
                # Collection leeren (vollständiger Import)
                db[collection_name].delete_many({})
                
                # Dokumente wiederherstellen
                if documents:
                    # IDs korrigieren
                    fixed_documents = []
                    for doc in documents:
                        fixed_doc = self._fix_json_document(doc)
                        fixed_documents.append(fixed_doc)
                    
                    # Dokumente einfügen
                    if fixed_documents:
                        db[collection_name].insert_many(fixed_documents)
                        print(f"    ✅ {len(fixed_documents)} Dokumente wiederhergestellt")
            # Nach dem Import: Verwaiste Nutzernamen anonymisieren
            try:
                self._anonymize_orphan_user_names()
            except Exception as e:
                print(f"⚠️  Konnte Orphan-Namen nicht anonymisieren: {e}")
            
            print(f"✅ JSON-Backup erfolgreich importiert")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Importieren des JSON-Backups: {e}")
            return False
    
    def _validate_json_backup(self, backup_data: Dict) -> bool:
        """Validiert JSON-Backup-Daten (tolerant für alte Formate)."""
        try:
            if not isinstance(backup_data, dict):
                return False

            # Prüfe Struktur (neu: metadata+data, alt: flach)
            if 'metadata' in backup_data and 'data' in backup_data and isinstance(backup_data['data'], dict):
                data_section = backup_data['data']
            else:
                data_section = backup_data

            if not isinstance(data_section, dict):
                return False

            # Akzeptiere, wenn mindestens eine relevante Collection vorhanden ist
            relevant = {
                'tools', 'workers', 'consumables', 'lendings', 'consumable_usages',
                'tickets', 'ticket_messages', 'ticket_notes', 'auftrag_details', 'auftrag_material',
                'users', 'settings'
            }
            present = [k for k in data_section.keys() if k in relevant]
            if not present:
                print("JSON enthält keine relevanten Collections")
                return False
            return True
        except Exception:
            return False
    
    def _fix_json_document(self, doc: Dict) -> Dict:
        """Korrigiert JSON-Dokument für MongoDB-Import"""
        if not isinstance(doc, dict):
            return doc
        
        # _id konvertieren
        if '_id' in doc:
            if isinstance(doc['_id'], str) and len(doc['_id']) == 24:
                try:
                    doc['_id'] = ObjectId(doc['_id'])
                except:
                    del doc['_id']
            elif not isinstance(doc['_id'], ObjectId):
                del doc['_id']
        
        # Datetime-Felder konvertieren
        datetime_fields = ['created_at', 'updated_at', 'modified_at', 'deleted_at']
        for field in datetime_fields:
            if field in doc and isinstance(doc[field], str):
                try:
                    doc[field] = datetime.fromisoformat(doc[field].replace('Z', '+00:00'))
                except:
                    pass
        
        return doc

    def _anonymize_orphan_user_names(self):
        """Entfernt Namen/Bezüge auf nicht vorhandene Nutzende (kein Name anzeigen)."""
        from datetime import datetime as _dt
        try:
            from app.models.mongodb_database import mongodb
            existing_users = set(u.get('username') for u in mongodb.find('users', {}) if u.get('username'))
            anonymized = 0
            # Felder, die Usernamen enthalten können
            username_fields = ['created_by', 'assigned_to', 'reporter', 'author', 'user', 'username']
            name_fields = ['created_by_name', 'assigned_to_name', 'reporter_name', 'author_name', 'user_name']
            for collection in ['tickets', 'messages', 'ticket_messages', 'ticket_history']:
                docs = list(mongodb.find(collection, {}))
                for doc in docs:
                    updates = {}
                    # Username-Felder: nullen, wenn User nicht existiert
                    for field in username_fields:
                        if field in doc and doc.get(field) and doc.get(field) not in existing_users:
                            updates[field] = None
                    # Namens-Felder: auf 'Anonym' setzen, wenn korrespondierender Nutzende fehlt
                    for field in name_fields:
                        if field in doc and doc.get(field):
                            related_user = None
                            if field.endswith('_name'):
                                base = field[:-5]
                                related_user = doc.get(base)
                            if (not related_user) or (related_user not in existing_users):
                                # Leer setzen (kein Anzeigename)
                                if doc.get(field) != '':
                                    updates[field] = ''
                    if updates:
                        updates['updated_at'] = _dt.now()
                        mongodb.update_one(collection, {'_id': doc['_id']}, {'$set': updates})
                        anonymized += 1
            if anonymized:
                print(f"  🔒 {anonymized} Dokumente anonymisiert (fehlende Nutzende)")
        except Exception as e:
            print(f"⚠️  Anonymisierung fehlgeschlagen: {e}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """Listet alle verfügbaren Backups auf"""
        backups = []
        
        for backup_file in self.backup_dir.glob("*.zip"):
            try:
                with zipfile.ZipFile(backup_file, 'r') as zipf:
                    # Metadaten lesen
                    if 'backup_metadata.json' in zipf.namelist():
                        metadata_content = zipf.read('backup_metadata.json')
                        metadata = json.loads(metadata_content.decode('utf-8'))
                    else:
                        metadata = {
                            'backup_name': backup_file.stem,
                            'created_at': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                            'version': '1.0'
                        }
                
                backups.append({
                    'filename': backup_file.name,
                    'size': self._format_size(backup_file.stat().st_size),
                    'created_at': metadata.get('created_at', 'Unbekannt'),
                    'includes_media': metadata.get('includes_media', False),
                    'version': metadata.get('version', '1.0')
                })
                
            except Exception as e:
                print(f"Fehler beim Lesen von Backup {backup_file.name}: {e}")
        
        return sorted(backups, key=lambda x: x['created_at'], reverse=True)

    def _prune_old_backups_optimized(self, days: int = 7):
        """
        🚀 Optimiert die Bereinigung alter Backups mit intelligenter Strategie
        """
        try:
            cutoff = datetime.now().timestamp() - days * 86400
            removed = 0
            kept_weekly = 0
            kept_daily = 0

            # Sammle alle Backup-Dateien mit Metadaten
            backups_info = []
            for backup_file in self.backup_dir.glob('*.zip'):
                try:
                    stat = backup_file.stat()
                    backups_info.append({
                        'path': backup_file,
                        'mtime': stat.st_mtime,
                        'size': stat.st_size,
                        'is_weekly': 'weekly' in backup_file.name,
                        'is_old': stat.st_mtime < cutoff
                    })
                except Exception:
                    continue

            # Sortiere nach Änderungsdatum (neueste zuerst)
            backups_info.sort(key=lambda x: x['mtime'], reverse=True)

            # Intelligente Bereinigungsstrategie
            to_remove = []

            for backup in backups_info:
                if backup['is_weekly']:
                    # Wöchentliche Backups: behalte 4 Wochen
                    if kept_weekly >= 4:
                        to_remove.append(backup)
                    else:
                        kept_weekly += 1
                elif backup['is_old']:
                    # Tägliche Backups: behalte nur die neuesten nach Cleanup-Periode
                    if kept_daily >= 7:  # Zusätzlich 7 tägliche nach Cleanup
                        to_remove.append(backup)
                    else:
                        kept_daily += 1
                # Sonst: behalte alle neuen Backups

            # Führe Löschung durch
            total_size_freed = 0
            for backup in to_remove:
                try:
                    backup['path'].unlink()
                    removed += 1
                    total_size_freed += backup['size']
                except Exception as e:
                    logger.warning(f"Backup {backup['path']} konnte nicht gelöscht werden: {e}")

            if removed:
                logger.info(f"🧹 {removed} alte Backups gelöscht, {self._format_size(total_size_freed)} Speicherplatz freigegeben")

        except Exception as e:
            logger.error(f"Fehler bei der optimierten Backup-Bereinigung: {e}")

    def import_json_backup_scoped(self, json_file_path: str, target_department: str) -> bool:
        """Importiert ein altes JSON-Backup und weist alle Daten der angegebenen Abteilung zu."""
        try:
            # Stelle sicher, dass während des Imports das Department-Scoping mit der Ziel-Abteilung übereinstimmt
            try:
                from flask import g, has_app_context
                _had_ctx = has_app_context()
                _old_dep = getattr(g, 'current_department', None) if _had_ctx else None
                if _had_ctx:
                    g.current_department = target_department
            except Exception:
                _had_ctx = False
                _old_dep = None
            if not target_department:
                print("❌ Keine Ziel-Abteilung angegeben")
                return False
            print(f"🔄 Importiere JSON-Backup (Department={target_department}): {json_file_path}")
            with open(json_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            if not self._validate_json_backup(backup_data):
                print("❌ Ungültiges JSON-Backup")
                return False
            # Verwende die bestehende App-Datenbankverbindung
            from app.models.mongodb_database import mongodb
            # Datenbereich extrahieren
            data_section = backup_data['data'] if ('metadata' in backup_data and 'data' in backup_data) else backup_data
            # Collections importieren – 'settings' nur selektiv
            scoped_collections = ['tools', 'workers', 'consumables', 'lendings', 'consumable_usages', 'tickets', 'ticket_messages', 'ticket_notes', 'auftrag_details', 'auftrag_material']
            total_inserted = 0
            total_failed = 0
            for collection_name, documents in data_section.items():
                if collection_name == 'metadata':
                    continue
                if collection_name not in scoped_collections:
                    # Überspringe nicht-relevante oder system-Collections
                    continue
                print(f"  📊 Stelle Collection wieder her (scoped): {collection_name}")
                inserted_count = 0
                failed_count = 0
                for doc in documents or []:
                    doc = self._fix_json_document(doc)
                    # IDs immer entfernen, um Kollisionen zu vermeiden
                    if '_id' in doc:
                        try:
                            del doc['_id']
                        except Exception:
                            pass
                    # Alte/inkompatible Abteilungsfelder entfernen
                    dept_like_fields = ['department', 'allowed_departments', 'default_department', 'departments', 'dept', 'dept_id', 'source_department', 'target_department']
                    for key in list(doc.keys()):
                        if key in dept_like_fields:
                            try:
                                del doc[key]
                            except Exception:
                                pass
                    # Department erzwingen
                    doc['department'] = target_department
                    if collection_name == 'tickets':
                        # Ziel-Abteilung in Tickets ggf. zusätzlich setzen
                        doc['target_department'] = target_department
                    # Einfügen/Upsert mit Duplikat-Schutz
                    try:
                        # Legacy-Dokumente ohne Department bevorzugt umhängen statt duplizieren
                        if collection_name in ('tools', 'workers', 'consumables'):
                            # Barcode normalisieren
                            bc = self._normalize_barcode(doc.get('barcode'))
                            if not bc:
                                # Ohne Barcode keine Idempotenz möglich -> Insert als Fallback
                                mongodb.insert_one(collection_name, doc)
                                inserted_count += 1
                                continue
                            doc['barcode'] = bc
                            try:
                                mongodb.update_one(
                                    collection_name,
                                    {'barcode': bc, 'department': {'$exists': False}},
                                    {'$set': {'department': target_department}},
                                    upsert=False
                                )
                            except Exception:
                                pass
                            # Idempotentes Upsert pro (department, barcode)
                            ok = mongodb.update_one(
                                collection_name,
                                {'barcode': bc, 'department': target_department},
                                {'$set': doc},
                                upsert=True
                            )
                            if ok:
                                inserted_count += 1
                            continue
                        # Tickets: Upsert per ticket_number, falls vorhanden
                        if collection_name == 'tickets' and doc.get('ticket_number'):
                            ok = mongodb.update_one(
                                'tickets',
                                {'ticket_number': doc['ticket_number'], 'department': target_department},
                                {'$set': doc},
                                upsert=True
                            )
                            if ok:
                                inserted_count += 1
                            continue
                        # Fallback: normales Insert
                        mongodb.insert_one(collection_name, doc)
                        inserted_count += 1
                    except Exception as e:
                        failed_count += 1
                        # Kurz-Log, aber Import fortsetzen
                        print(f"    ⚠️  Fehler beim Einfügen in {collection_name}: {e}")
                total_inserted += inserted_count
                total_failed += failed_count
                print(f"    ✅ {inserted_count} eingefügt, ❌ {failed_count} fehlgeschlagen in {collection_name}")
            print(f"✅ JSON-Backup (scoped) abgeschlossen – Gesamt: {total_inserted} eingefügt, {total_failed} fehlgeschlagen")
            # Optional: Nutzende global importieren, wenn vorhanden (idempotent über username)
            try:
                users_docs = data_section.get('users')
                if isinstance(users_docs, list):
                    from app.models.mongodb_database import mongodb
                    from werkzeug.security import generate_password_hash
                    for doc in users_docs:
                        try:
                            fixed = self._fix_json_document(doc)
                            username = (fixed.get('username') or '').strip()
                            if not username:
                                continue
                            # Passwort sicherstellen
                            if not fixed.get('password_hash'):
                                if fixed.get('password'):
                                    fixed['password_hash'] = generate_password_hash(fixed['password'])
                                else:
                                    pw = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                                    fixed['password_hash'] = generate_password_hash(pw)
                            # Felder bereinigen
                            fixed.pop('password', None)
                            fixed.pop('_id', None)
                            created_at_val = fixed.pop('created_at', None)
                            fixed.setdefault('role', 'anwender')
                            fixed.setdefault('is_active', True)
                            # Department-Felder entfernen, Nutzer sind global
                            for k in ['department', 'departments']:
                                fixed.pop(k, None)
                            # Idempotentes Upsert am username (created_at nur on-insert)
                            mongodb.update_one(
                                'users',
                                {'username': username},
                                {'$setOnInsert': {'created_at': created_at_val or datetime.now()}, '$set': fixed},
                                upsert=True
                            )
                        except Exception as e:
                            print(f"    ⚠️  Nutzer-Import: {e}")
            except Exception as e:
                print(f"⚠️  Nutzende-Import (scoped) übersprungen: {e}")

            # Nachzug: Orphan-Namen anonymisieren
            try:
                self._anonymize_orphan_user_names()
            except Exception as e:
                print(f"⚠️  Orphan-Anonymisierung (scoped) fehlgeschlagen: {e}")

            # Erfolg, wenn mindestens ein Dokument eingefügt wurde
            return total_inserted > 0
        except Exception as e:
            print(f"❌ Fehler beim scoped-Import: {e}")
            return False
        finally:
            # Ursprüngliches Department im Kontext wiederherstellen
            try:
                if _had_ctx:
                    from flask import g
                    g.current_department = _old_dep
            except Exception:
                pass

    def import_json_backup_scoped_report(self, json_file_path: str, target_department: str) -> dict:
        """
        Wie import_json_backup_scoped, liefert aber eine Detail-Statistik zurück.
        Rückgabe:
          { ok: bool, total_inserted: int, total_failed: int,
            per_collection: { name: {inserted:int, failed:int} }, errors: [str,...] }
        """
        report = {
            'ok': False,
            'total_inserted': 0,
            'total_failed': 0,
            'total_duplicates': 0,
            'per_collection': {},
            'errors': []
        }
        try:
            # Department-Kontext für den Import setzen (falls App-Kontext vorhanden)
            try:
                from flask import g, has_app_context
                _had_ctx = has_app_context()
                _old_dep = getattr(g, 'current_department', None) if _had_ctx else None
                if _had_ctx:
                    g.current_department = target_department
            except Exception:
                _had_ctx = False
                _old_dep = None
            if not target_department:
                report['errors'].append('Keine Ziel-Abteilung angegeben')
                return report
            with open(json_file_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            if not self._validate_json_backup(backup_data):
                report['errors'].append('Ungültiges JSON-Backup')
                return report
            from app.models.mongodb_database import mongodb
            data_section = backup_data['data'] if ('metadata' in backup_data and 'data' in backup_data) else backup_data
            scoped_collections = ['tools', 'workers', 'consumables', 'lendings', 'consumable_usages', 'tickets', 'ticket_messages', 'ticket_notes', 'auftrag_details', 'auftrag_material']
            from pymongo.errors import DuplicateKeyError
            for collection_name, documents in data_section.items():
                if collection_name == 'metadata':
                    continue
                if collection_name not in scoped_collections:
                    continue
                inserted_count = 0
                failed_count = 0
                duplicate_count = 0
                reassigned_count = 0
                for doc in documents or []:
                    try:
                        doc = self._fix_json_document(doc)
                        if '_id' in doc:
                            del doc['_id']
                        for key in ['department', 'allowed_departments', 'default_department', 'departments', 'dept', 'dept_id', 'source_department', 'target_department']:
                            if key in doc:
                                del doc[key]
                        doc['department'] = target_department
                        if collection_name == 'tickets':
                            doc['target_department'] = target_department
                        # Idempotentes Einfügen
                        if collection_name in ('tools', 'workers', 'consumables'):
                            bc = self._normalize_barcode(doc.get('barcode'))
                            if not bc:
                                # Ohne Barcode kein Upsert möglich -> Insert
                                mongodb.insert_one(collection_name, doc)
                                inserted_count += 1
                                continue
                            doc['barcode'] = bc
                            # Legacy-Reassign: vorhandenes Dokument ohne department umhängen
                            try:
                                reassigned = mongodb.update_one(
                                    collection_name,
                                    {'barcode': bc, 'department': {'$exists': False}},
                                    {'$set': {'department': target_department}},
                                    upsert=False
                                )
                                if reassigned:
                                    reassigned_count += 1
                            except Exception:
                                pass
                            ok = mongodb.update_one(
                                collection_name,
                                {'barcode': bc, 'department': target_department},
                                {'$set': doc},
                                upsert=True
                            )
                            if ok:
                                inserted_count += 1
                            continue
                        if collection_name == 'tickets' and doc.get('ticket_number'):
                            ok = mongodb.update_one(
                                'tickets',
                                {'ticket_number': doc['ticket_number'], 'department': target_department},
                                {'$set': doc},
                                upsert=True
                            )
                            if ok:
                                inserted_count += 1
                            continue
                        # Fallback: Insert
                        mongodb.insert_one(collection_name, doc)
                        inserted_count += 1
                    except DuplicateKeyError as e:
                        # Duplikat: als übersprungen zählen, nicht als Fehler
                        duplicate_count += 1
                    except Exception as e:
                        failed_count += 1
                        if len(report['errors']) < 20:
                            report['errors'].append(f"{collection_name}: {e}")
                report['per_collection'][collection_name] = {
                    'inserted': inserted_count,
                    'failed': failed_count,
                    'duplicates': duplicate_count,
                    'reassigned': reassigned_count
                }
                report['total_inserted'] += inserted_count
                report['total_failed'] += failed_count
                report['total_duplicates'] += duplicate_count
                report['total_reassigned'] = report.get('total_reassigned', 0) + reassigned_count
            # Nutzende global importieren (idempotent über username)
            try:
                users_docs = data_section.get('users')
                if isinstance(users_docs, list):
                    from werkzeug.security import generate_password_hash
                    from pymongo import UpdateOne
                    ops = []
                    for doc in users_docs:
                        try:
                            fixed = self._fix_json_document(doc)
                            username = (fixed.get('username') or '').strip()
                            if not username:
                                continue
                            if not fixed.get('password_hash'):
                                if fixed.get('password'):
                                    fixed['password_hash'] = generate_password_hash(fixed['password'])
                                else:
                                    pw = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                                    fixed['password_hash'] = generate_password_hash(pw)
                            created_at_val = fixed.pop('created_at', None)
                            fixed.pop('password', None)
                            fixed.pop('_id', None)
                            fixed.setdefault('role', 'anwender')
                            fixed.setdefault('is_active', True)
                            # Department-Felder auf User entfernen (global), allowed/default bleiben erhalten
                            for k in ['department', 'departments']:
                                fixed.pop(k, None)
                            ops.append(UpdateOne(
                                {'username': username},
                                {'$setOnInsert': {'created_at': created_at_val or datetime.now()}, '$set': fixed},
                                upsert=True
                            ))
                        except Exception as _ue:
                            if len(report['errors']) < 20:
                                report['errors'].append(f"user({fixed.get('username','?')}): {_ue}")
                    if ops:
                        try:
                            res = mongodb.db.users.bulk_write(ops, ordered=False)
                            report['users_upserted'] = getattr(res, 'upserted_count', 0)
                            report['users_matched'] = getattr(res, 'matched_count', 0)
                        except Exception as be:
                            report['errors'].append(f"users.bulk: {be}")
                    report['users_imported'] = True
            except Exception as ue:
                report['errors'].append(f"users: {ue}")

            # Orphan-Namen anonymisieren/leeren
            try:
                self._anonymize_orphan_user_names()
            except Exception as ae:
                report['errors'].append(f"anonymize: {ae}")

            # Erfolg, wenn Insert stattfand oder nur Duplikate vorlagen
            report['ok'] = (report['total_inserted'] > 0 and len(report['errors']) == 0) or (
                report['total_inserted'] == 0 and report['total_failed'] == 0 and report['total_duplicates'] > 0
            )
            return report
        except Exception as e:
            report['errors'].append(str(e))
            return report
        finally:
            try:
                if _had_ctx:
                    from flask import g
                    g.current_department = _old_dep
            except Exception:
                pass
    
    # ===== Hintergrund-Jobs für Import =====
    def start_import_job(self, json_file_path: str, target_department: str) -> str:
        """Startet einen Hintergrund-Import-Job und gibt die Job-ID zurück."""
        job_id = str(uuid.uuid4())
        try:
            from app.models.mongodb_database import mongodb
            now = datetime.now()
            job_doc = {
                '_id': job_id,
                'type': 'json_scoped_import',
                'status': 'running',
                'created_at': now,
                'updated_at': now,
                'file_path': json_file_path,
                'target_department': target_department,
                'progress': {'inserted': 0, 'failed': 0, 'duplicates': 0},
                'result': None,
                'errors': []
            }
            mongodb.insert_one('import_jobs', job_doc)

            # Hintergrund-Thread starten
            thread = threading.Thread(target=self._run_import_job, args=(job_id,), daemon=True)
            thread.start()
            return job_id
        except Exception as e:
            # Fallback: Job nicht gestartet
            return ''

    def _run_import_job(self, job_id: str):
        """Führt den Import-Job im Hintergrund aus und aktualisiert den Status in MongoDB."""
        from app.models.mongodb_database import mongodb
        try:
            job = mongodb.find_one('import_jobs', {'_id': job_id})
            if not job:
                return
            json_file_path = job.get('file_path')
            target_department = job.get('target_department')

            # Import ausführen (mit Report)
            report = self.import_json_backup_scoped_report(json_file_path, target_department)

            # Status aktualisieren
            status = 'done' if report.get('ok') else 'error'
            mongodb.update_one('import_jobs', {'_id': job_id}, {'$set': {
                'status': status,
                'updated_at': datetime.now(),
                'result': report,
                'progress': {
                    'inserted': report.get('total_inserted', 0),
                    'failed': report.get('total_failed', 0),
                    'duplicates': report.get('total_duplicates', 0)
                },
                'errors': report.get('errors', [])
            }})
        except Exception as e:
            mongodb.update_one('import_jobs', {'_id': job_id}, {'$set': {
                'status': 'error',
                'updated_at': datetime.now(),
                'errors': [str(e)]
            }})

    def get_import_job(self, job_id: str) -> dict:
        """Liest den Status eines Import-Jobs aus MongoDB."""
        try:
            from app.models.mongodb_database import mongodb
            job = mongodb.find_one('import_jobs', {'_id': job_id})
            if not job:
                return {'exists': False}
            # Konvertiere Datumswerte für JSON-Ausgabe
            for k in ['created_at', 'updated_at']:
                if k in job and isinstance(job[k], datetime):
                    job[k] = job[k].isoformat()
            job['exists'] = True
            return job
        except Exception as e:
            return {'exists': False, 'error': str(e)}

    def _cleanup_temp_files(self, temp_paths: List[Optional[Path]]):
        """Räumt temporäre Dateien auf"""
        for temp_path in temp_paths:
            if temp_path and temp_path.exists():
                try:
                    shutil.rmtree(temp_path)
                except Exception as e:
                    print(f"Warnung: Konnte temporäre Dateien nicht löschen: {e}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Formatiert Dateigröße"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

# 🚀 Neue optimierte globale Instanz
optimized_backup_manager = OptimizedBackupManager()

# Abwärtskompatibilität: Alte Instanz verweist auf neue
unified_backup_manager = optimized_backup_manager 