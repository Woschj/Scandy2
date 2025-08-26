#!/usr/bin/env python3
"""
Script zur Bereinigung alter Backups
Löscht Backups älter als 7 Tage
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_old_backups(keep_days=7):
    """Löscht Backups älter als 'keep_days' Tage"""
    
    # Backup-Verzeichnis - suche in verschiedenen möglichen Pfaden
    possible_backup_dirs = [
        Path("backups"),
        Path("/opt/scandy/backups"),
        Path("/opt/scandy/app/backups"),
        Path("app/backups"),
        Path("../backups"),
        Path("../../backups")
    ]
    
    backup_dir = None
    for dir_path in possible_backup_dirs:
        if dir_path.exists():
            backup_dir = dir_path
            break
    
    if not backup_dir:
        print("Backup-Verzeichnis nicht gefunden!")
        print("Gesuchte Pfade:")
        for dir_path in possible_backup_dirs:
            print(f"  - {dir_path.absolute()}")
        return
    
    cutoff_date = datetime.now() - timedelta(days=keep_days)
    print(f"Lösche Backups älter als {keep_days} Tage (vor {cutoff_date.strftime('%Y-%m-%d %H:%M')})")
    
    # Finde alle Backup-Dateien
    json_backups = list(backup_dir.glob("scandy_backup_*.json"))
    native_backups = list(backup_dir.glob("scandy_native_backup_*"))
    all_backups = json_backups + native_backups
    
    if not all_backups:
        print("Keine Backup-Dateien gefunden")
        return
    
    deleted_count = 0
    total_size_freed = 0
    
    for backup in all_backups:
        try:
            # Prüfe Erstellungsdatum
            backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            
            if backup_time < cutoff_date:
                # Backup ist zu alt
                if backup.is_dir():
                    # Natives Backup löschen
                    size = get_dir_size(backup)
                    shutil.rmtree(backup)
                    deleted_count += 1
                    total_size_freed += size
                    print(f"❌ Altes BSON-Backup gelöscht: {backup.name} (vom {backup_time.strftime('%Y-%m-%d %H:%M')})")
                else:
                    # JSON-Backup löschen
                    size = backup.stat().st_size
                    backup.unlink()
                    deleted_count += 1
                    total_size_freed += size
                    print(f"❌ Altes JSON-Backup gelöscht: {backup.name} (vom {backup_time.strftime('%Y-%m-%d %H:%M')})")
            else:
                # Backup ist noch aktuell
                if backup.is_dir():
                    size = get_dir_size(backup)
                    print(f"✅ Behalten: {backup.name} (vom {backup_time.strftime('%Y-%m-%d %H:%M')}) - {format_size(size)}")
                else:
                    size = backup.stat().st_size
                    print(f"✅ Behalten: {backup.name} (vom {backup_time.strftime('%Y-%m-%d %H:%M')}) - {format_size(size)}")
                    
        except Exception as e:
            print(f"Fehler beim Verarbeiten von {backup.name}: {e}")
    
    if deleted_count > 0:
        total_size_mb = total_size_freed / (1024 * 1024)
        print(f"\n🎉 Backup-Bereinigung abgeschlossen:")
        print(f"   Gelöschte Backups: {deleted_count}")
        print(f"   Freigegebener Speicherplatz: {total_size_mb:.1f} MB")
        print(f"   Behaltene Backups: {len(all_backups) - deleted_count}")
    else:
        print(f"\n✅ Keine alten Backups gefunden (alle Backups sind neuer als {keep_days} Tage)")

def get_dir_size(path):
    """Berechnet die Größe eines Verzeichnisses"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def format_size(size_bytes):
    """Formatiert Bytes in lesbare Größe"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

if __name__ == "__main__":
    print("🧹 Bereinige alte Backups...")
    print("=" * 50)
    
    # Prüfe ob Argument für Tage angegeben wurde
    import sys
    keep_days = 7
    if len(sys.argv) > 1:
        try:
            keep_days = int(sys.argv[1])
        except ValueError:
            print("Ungültige Anzahl Tage. Verwende Standard: 7 Tage")
    
    cleanup_old_backups(keep_days) 