#!/usr/bin/env python3
"""
Dynamisches Scandy-Start-Script
Erstellt automatisch Docker-Compose-Dateien mit freien Ports
"""

import os
import subprocess
import socket
import sys
from pathlib import Path

# Konfiguration der Abteilungen
DEPARTMENTS = {
    'btz': {
        'name': 'BTZ',
        'web_port': 5003,
        'mongodb_port': 27020
    },
    'werkstatt': {
        'name': 'Werkstatt', 
        'web_port': 5001,
        'mongodb_port': 27018
    },
    'verwaltung': {
        'name': 'Verwaltung',
        'web_port': 5002, 
        'mongodb_port': 27019
    }
}

def find_free_port(start_port):
    """Findet einen freien Port ab start_port"""
    port = start_port
    while port < start_port + 100:  # Max 100 Versuche
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    return None

def check_port_in_use(port):
    """Prüft ob ein Port bereits belegt ist"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return False
    except OSError:
        return True

def generate_docker_compose(department, config):
    """Erstellt eine Docker-Compose-Datei für eine Abteilung"""
    
    # Prüfe ob Ports frei sind, sonst finde freie Ports
    web_port = config['web_port']
    mongodb_port = config['mongodb_port']
    
    if check_port_in_use(web_port):
        print(f"⚠️  Port {web_port} ist belegt, suche freien Port...")
        web_port = find_free_port(web_port)
        if not web_port:
            print(f"❌ Kein freier Port für {department} gefunden!")
            return False
    
    if check_port_in_use(mongodb_port):
        print(f"⚠️  MongoDB Port {mongodb_port} ist belegt, suche freien Port...")
        mongodb_port = find_free_port(mongodb_port)
        if not mongodb_port:
            print(f"❌ Kein freier MongoDB-Port für {department} gefunden!")
            return False
    
    # Docker-Compose Template
    template = f"""version: '3.8'

services:
  # MongoDB für {config['name']}
  {department}-mongodb:
    image: mongo:6.0
    container_name: {department}-mongodb
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: {department}Password123
      MONGO_INITDB_DATABASE: {department}_scandy
    volumes:
      - {department}_mongodb_data:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    ports:
      - "{mongodb_port}:27017"
    networks:
      - {department}-network

  # Scandy-App für {config['name']}
  {department}-scandy:
    build: .
    container_name: {department}-scandy
    restart: unless-stopped
    environment:
      - MONGODB_URI=mongodb://admin:{department}Password123@{department}-mongodb:27017/{department}_scandy?authSource=admin
      - SECRET_KEY={department}SecretKey123456789
      - SYSTEM_NAME=Scandy {config['name']}
      - TICKET_SYSTEM_NAME=Aufgaben {config['name']}
      - TOOL_SYSTEM_NAME=Werkzeuge {config['name']}
      - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter {config['name']}
    volumes:
      - ./app:/app/app
      - ./data/{department}:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
    ports:
      - "{web_port}:5000"
    depends_on:
      - {department}-mongodb
    networks:
      - {department}-network

volumes:
  {department}_mongodb_data:

networks:
  {department}-network:
    driver: bridge
"""
    
    # Schreibe Docker-Compose-Datei
    filename = f"docker-compose.{department}.yml"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"✅ {config['name']}: Web-Port {web_port}, MongoDB-Port {mongodb_port}")
    return {
        'department': department,
        'name': config['name'],
        'web_port': web_port,
        'mongodb_port': mongodb_port,
        'filename': filename
    }

def start_department(department, config):
    """Startet eine Abteilung"""
    print(f"\n🚀 Starte {config['name']}...")
    
    # Erstelle Docker-Compose-Datei
    result = generate_docker_compose(department, config)
    if not result:
        return False
    
    # Starte Container
    try:
        subprocess.run([
            'docker-compose', '-f', result['filename'], 'up', '-d'
        ], check=True)
        print(f"✅ {config['name']} gestartet!")
        print(f"   Web: http://localhost:{result['web_port']}")
        print(f"   MongoDB: localhost:{result['mongodb_port']}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Fehler beim Starten von {config['name']}: {e}")
        return False

def main():
    """Hauptfunktion"""
    print("=" * 50)
    print("Scandy - Dynamisches Multi-Instance Setup")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # Einzelne Abteilung starten
        department = sys.argv[1].lower()
        if department in DEPARTMENTS:
            start_department(department, DEPARTMENTS[department])
        else:
            print(f"❌ Unbekannte Abteilung: {department}")
            print(f"Verfügbare Abteilungen: {', '.join(DEPARTMENTS.keys())}")
    else:
        # Alle Abteilungen starten
        print("Starte alle Abteilungen...")
        results = []
        
        for department, config in DEPARTMENTS.items():
            result = start_department(department, config)
            if result:
                results.append(result)
        
        print("\n" + "=" * 50)
        print("Zusammenfassung:")
        print("=" * 50)
        
        for result in results:
            print(f"✅ {result['name']}: http://localhost:{result['web_port']}")
        
        print(f"\nAlle {len(results)} Abteilungen gestartet!")

if __name__ == "__main__":
    main() 