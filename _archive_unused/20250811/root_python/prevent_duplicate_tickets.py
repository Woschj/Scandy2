#!/usr/bin/env python3
"""
Skript zur Prävention von doppelten Tickets beim Backup-Restore
"""

import sys
import os
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# MongoDB-Verbindung direkt herstellen
def get_mongodb_connection():
    """Stellt direkte MongoDB-Verbindung her"""
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
    db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
    
    client = MongoClient(mongo_uri)
    db = client[db_name]
    return db

def check_for_duplicates_before_restore():
    """Prüft auf Duplikate vor einem Backup-Restore"""
    
    print("🔍 Prüfe auf potenzielle Duplikate vor Backup-Restore...")
    
    db = get_mongodb_connection()
    
    # Prüfe alle Collections auf doppelte IDs
    collections_to_check = ['tickets', 'tools', 'workers', 'consumables', 'jobs']
    
    for collection_name in collections_to_check:
        print(f"\n📋 Prüfe Collection: {collection_name}")
        
        documents = list(db[collection_name].find({}))
        print(f"  Dokumente gefunden: {len(documents)}")
        
        # Gruppiere nach Titel/Name
        docs_by_title = {}
        for doc in documents:
            title_field = 'title' if 'title' in doc else 'name'
            title = doc.get(title_field, 'Unbekannt')
            
            if title not in docs_by_title:
                docs_by_title[title] = []
            docs_by_title[title].append(doc)
        
        # Prüfe auf Duplikate
        duplicates_found = False
        for title, doc_list in docs_by_title.items():
            if len(doc_list) > 1:
                print(f"  ⚠️  Duplikate gefunden für '{title}': {len(doc_list)}x")
                duplicates_found = True
                
                # Zeige ID-Typen
                id_types = {}
                for doc in doc_list:
                    doc_id = doc.get('_id')
                    id_type = type(doc_id).__name__
                    if id_type not in id_types:
                        id_types[id_type] = 0
                    id_types[id_type] += 1
                
                for id_type, count in id_types.items():
                    print(f"    - {id_type}: {count}x")
        
        if not duplicates_found:
            print(f"  ✅ Keine Duplikate gefunden")
    
    return True

def create_restore_safety_check():
    """Erstellt eine Sicherheitsprüfung für Backup-Restores"""
    
    print("\n🛡️  Erstelle Sicherheitsprüfung für Backup-Restores...")
    
    db = get_mongodb_connection()
    
    # Erstelle eine Sicherheitskopie vor dem Restore
    safety_data = {}
    collections_to_backup = ['tickets', 'tools', 'workers', 'consumables', 'jobs']
    
    for collection_name in collections_to_backup:
        documents = list(db[collection_name].find({}))
        safety_data[collection_name] = {
            'count': len(documents),
            'ids': [str(doc.get('_id', '')) for doc in documents],
            'titles': [doc.get('title', doc.get('name', 'Unbekannt')) for doc in documents]
        }
    
    # Speichere Sicherheitsdaten
    safety_file = f"restore_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(safety_file, 'w') as f:
        json.dump(safety_data, f, indent=2)
    
    print(f"✅ Sicherheitsdaten gespeichert in: {safety_file}")
    
    return safety_file

def verify_restore_safety(safety_file):
    """Verifiziert die Sicherheit nach einem Restore"""
    
    print(f"\n🔍 Verifiziere Restore-Sicherheit mit {safety_file}...")
    
    if not os.path.exists(safety_file):
        print(f"❌ Sicherheitsdatei nicht gefunden: {safety_file}")
        return False
    
    # Lade Sicherheitsdaten
    with open(safety_file, 'r') as f:
        safety_data = json.load(f)
    
    db = get_mongodb_connection()
    
    # Prüfe jede Collection
    for collection_name, safety_info in safety_data.items():
        print(f"\n📋 Prüfe Collection: {collection_name}")
        
        current_docs = list(db[collection_name].find({}))
        current_count = len(current_docs)
        safety_count = safety_info['count']
        
        print(f"  Vor Restore: {safety_count} Dokumente")
        print(f"  Nach Restore: {current_count} Dokumente")
        
        if current_count > safety_count:
            print(f"  ⚠️  Mehr Dokumente nach Restore! (+{current_count - safety_count})")
            
            # Prüfe auf Duplikate
            current_titles = [doc.get('title', doc.get('name', 'Unbekannt')) for doc in current_docs]
            from collections import Counter
            title_counts = Counter(current_titles)
            
            duplicates = {title: count for title, count in title_counts.items() if count > 1}
            if duplicates:
                print(f"  ❌ Duplikate gefunden:")
                for title, count in duplicates.items():
                    print(f"    - '{title}': {count}x")
        else:
            print(f"  ✅ Dokumenteanzahl in Ordnung")
    
    return True

if __name__ == "__main__":
    print("=== Backup-Restore Sicherheitsprüfung ===")
    print(f"Datum: {datetime.now()}")
    print()
    
    # Prüfe aktuelle Duplikate
    check_for_duplicates_before_restore()
    
    # Erstelle Sicherheitsprüfung
    safety_file = create_restore_safety_check()
    
    print(f"\n💡 Verwenden Sie dieses Skript vor jedem Backup-Restore:")
    print(f"python3 prevent_duplicate_tickets.py")
    print(f"\n💡 Nach dem Restore verifizieren Sie mit:")
    print(f"python3 verify_restore_safety.py {safety_file}")
    
    print("\n=== Sicherheitsprüfung abgeschlossen ===") 