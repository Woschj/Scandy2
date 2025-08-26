#!/usr/bin/env python3
"""
Skript zur Bereinigung doppelter Backups
Entfernt Backups die zur gleichen Minute erstellt wurden
"""

import os
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def cleanup_duplicate_backups():
    """Bereinigt doppelte Backups basierend auf Zeitstempel"""
    
    # Backup-Verzeichnis
    backup_dir = Path("backups")
    if not backup_dir.exists():
        print("Backup-Verzeichnis nicht gefunden")
        return
    
    # Alle Backup-Dateien finden
    backup_files = list(backup_dir.glob("scandy_backup_*.json"))
    
    if not backup_files:
        print("Keine Backup-Dateien gefunden")
        return
    
    # Gruppiere Backups nach Minute (YYYYMMDD_HHMM)
    backups_by_minute = defaultdict(list)
    
    for backup_file in backup_files:
        try:
            # Extrahiere Zeitstempel aus Dateiname
            filename = backup_file.name
            if filename.startswith("scandy_backup_") and filename.endswith(".json"):
                timestamp_str = filename[14:-5]  # Entferne "scandy_backup_" und ".json"
                
                # Parse Zeitstempel
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                minute_key = timestamp.strftime("%Y%m%d_%H%M")
                
                backups_by_minute[minute_key].append({
                    'file': backup_file,
                    'timestamp': timestamp,
                    'size': backup_file.stat().st_size
                })
        except Exception as e:
            print(f"Fehler beim Parsen von {backup_file.name}: {e}")
    
    # Finde und lösche doppelte Backups
    deleted_count = 0
    total_size_freed = 0
    
    for minute_key, backups in backups_by_minute.items():
        if len(backups) > 1:
            print(f"\nMehrere Backups für {minute_key}:")
            
            # Sortiere nach Größe (größte zuerst) und behalte nur das größte
            backups.sort(key=lambda x: x['size'], reverse=True)
            
            # Behalte das größte Backup, lösche die anderen
            for backup in backups[1:]:
                try:
                    size_mb = backup['size'] / (1024 * 1024)
                    print(f"  Lösche: {backup['file'].name} ({size_mb:.1f} MB)")
                    
                    backup['file'].unlink()
                    deleted_count += 1
                    total_size_freed += backup['size']
                    
                except Exception as e:
                    print(f"  Fehler beim Löschen von {backup['file'].name}: {e}")
            
            print(f"  Behalten: {backups[0]['file'].name} ({(backups[0]['size'] / (1024 * 1024)):.1f} MB)")
    
    if deleted_count > 0:
        total_size_mb = total_size_freed / (1024 * 1024)
        print(f"\nBereinigung abgeschlossen:")
        print(f"  Gelöschte Backups: {deleted_count}")
        print(f"  Freigegebener Speicherplatz: {total_size_mb:.1f} MB")
    else:
        print("\nKeine doppelten Backups gefunden")

if __name__ == "__main__":
    print("Bereinige doppelte Backups...")
    cleanup_duplicate_backups()
    print("Fertig!") 