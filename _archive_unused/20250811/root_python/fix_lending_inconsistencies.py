#!/usr/bin/env python3
"""
Fix-Skript für Ausleih-Inkonsistenzen
"""

import os
import sys
from datetime import datetime

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importiere nach dem Pfad-Setup
from pymongo import MongoClient
import os

def get_mongodb_connection():
    """Erstellt eine MongoDB-Verbindung"""
    # MongoDB-Verbindungsdaten aus Umgebungsvariablen
    mongo_host = os.environ.get('MONGO_HOST', 'localhost')
    mongo_port = int(os.environ.get('MONGO_PORT', 27017))
    mongo_db = os.environ.get('MONGO_DB', 'scandy')
    mongo_user = os.environ.get('MONGO_USER', '')
    mongo_password = os.environ.get('MONGO_PASSWORD', '')
    
    # Verbindung erstellen
    if mongo_user and mongo_password:
        connection_string = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}"
    else:
        connection_string = f"mongodb://{mongo_host}:{mongo_port}/{mongo_db}"
    
    client = MongoClient(connection_string)
    db = client[mongo_db]
    return db

def fix_lending_inconsistencies():
    """Behebt Inkonsistenzen in den Ausleihdaten"""
    print("=== Fix: Ausleih-Inkonsistenzen beheben ===")
    
    db = get_mongodb_connection()
    
    # 1. Alle aktiven Ausleihen anzeigen
    print("\n1. Aktuelle aktive Ausleihen:")
    active_lendings = list(db.lendings.find({'returned_at': None}))
    for lending in active_lendings:
        print(f"  - Tool: {lending.get('tool_barcode')}, Worker: {lending.get('worker_barcode')}, Lent: {lending.get('lent_at')}")
    
    # 2. Alle Werkzeuge mit Status anzeigen
    print("\n2. Werkzeuge mit Status:")
    tools = list(db.tools.find({'deleted': {'$ne': True}}))
    for tool in tools:
        print(f"  - {tool.get('name')} ({tool.get('barcode')}): Status = {tool.get('status')}")
    
    # 3. Inkonsistenzen finden und beheben
    print("\n3. Inkonsistenzen beheben:")
    fixed_count = 0
    
    for tool in tools:
        barcode = tool.get('barcode')
        status = tool.get('status')
        
        # Prüfe aktive Ausleihe
        active_lending = db.lendings.find_one({
            'tool_barcode': barcode,
            'returned_at': None
        })
        
        if active_lending and status != 'ausgeliehen':
            # Werkzeug ist ausgeliehen aber Status ist falsch
            db.tools.update_one(
                {'barcode': barcode}, 
                {'$set': {'status': 'ausgeliehen'}}
            )
            print(f"  ✅ {tool.get('name')}: Status auf 'ausgeliehen' korrigiert")
            fixed_count += 1
        elif not active_lending and status == 'ausgeliehen':
            # Werkzeug ist nicht ausgeliehen aber Status ist falsch
            db.tools.update_one(
                {'barcode': barcode}, 
                {'$set': {'status': 'verfügbar'}}
            )
            print(f"  ✅ {tool.get('name')}: Status auf 'verfügbar' korrigiert")
            fixed_count += 1
    
    print(f"\nInsgesamt {fixed_count} Werkzeug-Status korrigiert")
    
    # 4. Verwaiste Ausleihen bereinigen
    print("\n4. Verwaiste Ausleihen bereinigen:")
    orphaned_lendings = list(db.lendings.find({
        'returned_at': None,
        'tool_barcode': {'$exists': True}
    }))
    
    cleaned_count = 0
    for lending in orphaned_lendings:
        tool_barcode = lending.get('tool_barcode')
        tool = db.tools.find_one({'barcode': tool_barcode, 'deleted': {'$ne': True}})
        
        if not tool:
            # Werkzeug existiert nicht mehr, Ausleihe löschen
            db.lendings.delete_one({'_id': lending['_id']})
            print(f"  ✅ Verwaiste Ausleihe für nicht existierendes Werkzeug {tool_barcode} gelöscht")
            cleaned_count += 1
    
    print(f"Insgesamt {cleaned_count} verwaiste Ausleihen bereinigt")
    
    # 5. Finale Prüfung
    print("\n5. Finale Prüfung:")
    final_active_lendings = list(db.lendings.find({'returned_at': None}))
    print(f"Aktive Ausleihen nach Fix: {len(final_active_lendings)}")
    
    for lending in final_active_lendings:
        tool = db.tools.find_one({'barcode': lending.get('tool_barcode')})
        worker = db.workers.find_one({'barcode': lending.get('worker_barcode')})
        tool_name = tool.get('name') if tool else 'Unbekannt'
        worker_name = f"{worker.get('firstname', '')} {worker.get('lastname', '')}" if worker else 'Unbekannt'
        print(f"  - {tool_name} -> {worker_name}")

if __name__ == "__main__":
    try:
        fix_lending_inconsistencies()
        print("\n=== Fix abgeschlossen ===")
    except Exception as e:
        print(f"Fehler beim Fix: {e}")
        import traceback
        traceback.print_exc() 