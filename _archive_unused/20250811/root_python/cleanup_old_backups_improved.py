#!/usr/bin/env python3
"""
Verbessertes Script zur Bereinigung alter Backups
Findet automatisch das Backup-Verzeichnis und löscht Backups älter als 7 Tage
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime, timedelta

def find_backup_directory():
    """Findet das Backup-Verzeichnis automatisch"""
    
    # Mögliche Backup-Verzeichnisse
    possible_backup_dirs = [
        Path("backups"),
        Path("/opt/scandy/backups"),
        Path("/opt/scandy/app/backups"),
        Path("app/backups"),
        Path("../backups"),
        Path("../../backups"),
        Path("/home/scandy/Scandy2/backups"),
        Path("/root/Scandy2/backups"),
        Path("/Scandy2/backups"),
        Path("/scandy2/backups")
    ]
    
    # Prüfe auch relative Pfade vom aktuellen Verzeichnis
    current_dir = Path.cwd()
    for i in range(5):  # Gehe bis zu 5 Verzeichnisse nach oben
        possible_backup_dirs.append(current_dir / "backups")
        possible_backup_dirs.append(current_dir / "app" / "backups")
        current_dir = current_dir.parent
    
    # Suche nach Backup-Verzeichnis
    for dir_path in possible_backup_dirs:
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ Backup-Verzeichnis gefunden: {dir_path.absolute()}")
            return dir_path
    
    # Suche mit find-Befehl als Fallback
    try:
        import subprocess
        result = subprocess.run(['find', '/', '-name', 'backups', '-type', 'd', '-path', '*scandy*'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line and 'scandy' in line.lower():
                    backup_dir = Path(line)
                    if backup_dir.exists():
                        print(f"✅ Backup-Verzeichnis gefunden (via find): {backup_dir.absolute()}")
                        return backup_dir
    except Exception as e:
        print(f"Find-Befehl fehlgeschlagen: {e}")
    
    print("❌ Backup-Verzeichnis nicht gefunden!")
    print("Gesuchte Pfade:")
    for dir_path in possible_backup_dirs:
        print(f"  - {dir_path.absolute()}")
    return None

def cleanup_old_backups(keep_days=7):
    """Löscht Backups älter als 'keep_days' Tage"""
    
    # Finde Backup-Verzeichnis
    backup_dir = find_backup_directory()
    if not backup_dir:
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
    print("🧹 Bereinige alte Backups (Verbesserte Version)...")
    print("=" * 60)
    print(f"Aktuelles Verzeichnis: {Path.cwd().absolute()}")
    
    # Prüfe ob Argument für Tage angegeben wurde
    keep_days = 7
    if len(sys.argv) > 1:
        try:
            keep_days = int(sys.argv[1])
        except ValueError:
            print("Ungültige Anzahl Tage. Verwende Standard: 7 Tage")
    
    cleanup_old_backups(keep_days) 