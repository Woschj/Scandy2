#!/usr/bin/env python3
"""
Dynamisches Scandy-Stop-Script
Stoppt alle dynamisch erstellten Container
"""

import subprocess
import sys
import glob
import os

def stop_all_departments():
    """Stoppt alle Abteilungen"""
    print("=" * 50)
    print("Scandy - Stoppe alle Abteilungen")
    print("=" * 50)
    
    # Finde alle Docker-Compose-Dateien
    compose_files = glob.glob("docker-compose.*.yml")
    
    if not compose_files:
        print("❌ Keine Docker-Compose-Dateien gefunden!")
        return
    
    print(f"Gefundene Abteilungen: {len(compose_files)}")
    
    for compose_file in compose_files:
        department = compose_file.replace("docker-compose.", "").replace(".yml", "")
        print(f"\n🛑 Stoppe {department}...")
        
        try:
            subprocess.run([
                'docker-compose', '-f', compose_file, 'down'
            ], check=True)
            print(f"✅ {department} gestoppt!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Fehler beim Stoppen von {department}: {e}")
    
    print("\n" + "=" * 50)
    print("Alle Abteilungen gestoppt!")
    print("=" * 50)

def stop_department(department):
    """Stoppt eine spezifische Abteilung"""
    compose_file = f"docker-compose.{department}.yml"
    
    if not os.path.exists(compose_file):
        print(f"❌ Docker-Compose-Datei für {department} nicht gefunden!")
        return
    
    print(f"🛑 Stoppe {department}...")
    
    try:
        subprocess.run([
            'docker-compose', '-f', compose_file, 'down'
        ], check=True)
        print(f"✅ {department} gestoppt!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler beim Stoppen von {department}: {e}")

def main():
    """Hauptfunktion"""
    if len(sys.argv) > 1:
        # Einzelne Abteilung stoppen
        department = sys.argv[1].lower()
        stop_department(department)
    else:
        # Alle Abteilungen stoppen
        stop_all_departments()

if __name__ == "__main__":
    main() 