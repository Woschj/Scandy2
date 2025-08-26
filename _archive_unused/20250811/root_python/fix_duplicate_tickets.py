#!/usr/bin/env python3
"""
Skript zur Bereinigung doppelter Tickets nach Backup-Wiederherstellung
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
    # MongoDB-Verbindungsdaten aus Umgebungsvariablen oder Standard
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/scandy")
    db_name = os.environ.get("MONGO_INITDB_DATABASE", "scandy")
    
    client = MongoClient(mongo_uri)
    db = client[db_name]
    return db

def fix_duplicate_tickets():
    """Bereinigt doppelte Tickets nach Backup-Wiederherstellung"""
    
    print("🔍 Prüfe auf doppelte Tickets...")
    
    db = get_mongodb_connection()
    
    # Alle Tickets abrufen
    tickets = list(db.tickets.find({}))
    print(f"Gefundene Tickets: {len(tickets)}")
    
    # Tickets nach Titel gruppieren
    tickets_by_title = {}
    for ticket in tickets:
        title = ticket.get('title', 'Unbekannt')
        if title not in tickets_by_title:
            tickets_by_title[title] = []
        tickets_by_title[title].append(ticket)
    
    # Doppelte Tickets identifizieren
    duplicates_found = False
    tickets_to_delete = []
    
    for title, ticket_list in tickets_by_title.items():
        if len(ticket_list) > 1:
            print(f"\n⚠️  Doppelte Tickets gefunden für '{title}':")
            duplicates_found = True
            
            # Sortiere nach ID-Typ (ObjectId zuerst, dann String-IDs)
            sorted_tickets = sorted(ticket_list, key=lambda t: (
                not isinstance(t.get('_id'), ObjectId),  # ObjectId zuerst
                str(t.get('_id', ''))  # Dann alphabetisch
            ))
            
            # Behalte das erste Ticket (ObjectId), lösche die anderen
            keep_ticket = sorted_tickets[0]
            delete_tickets = sorted_tickets[1:]
            
            print(f"  ✅ Behalte: {keep_ticket.get('_id')} ({type(keep_ticket.get('_id')).__name__})")
            
            for ticket in delete_tickets:
                print(f"  ❌ Lösche: {ticket.get('_id')} ({type(ticket.get('_id')).__name__})")
                tickets_to_delete.append(ticket.get('_id'))
    
    if not duplicates_found:
        print("✅ Keine doppelten Tickets gefunden!")
        return
    
    # Bestätigung für Löschung
    if tickets_to_delete:
        print(f"\n🗑️  {len(tickets_to_delete)} doppelte Tickets werden gelöscht...")
        
        # Lösche doppelte Tickets
        for ticket_id in tickets_to_delete:
            try:
                # Versuche sowohl ObjectId als auch String-ID
                if isinstance(ticket_id, str) and len(ticket_id) == 24:
                    try:
                        obj_id = ObjectId(ticket_id)
                        result = db.tickets.delete_one({'_id': obj_id})
                    except:
                        result = db.tickets.delete_one({'_id': ticket_id})
                else:
                    result = db.tickets.delete_one({'_id': ticket_id})
                
                if result.deleted_count > 0:
                    print(f"  ✅ Ticket {ticket_id} gelöscht")
                else:
                    print(f"  ❌ Fehler beim Löschen von Ticket {ticket_id}")
                    
            except Exception as e:
                print(f"  ❌ Fehler beim Löschen von Ticket {ticket_id}: {e}")
        
        # Finale Prüfung
        remaining_tickets = list(db.tickets.find({}))
        print(f"\n✅ Bereinigung abgeschlossen! Verbleibende Tickets: {len(remaining_tickets)}")
        
        # Zeige verbleibende Tickets
        for ticket in remaining_tickets:
            print(f"  - {ticket.get('title', 'Unbekannt')} (ID: {ticket.get('_id')})")

def check_ticket_consistency():
    """Prüft die Konsistenz der Tickets"""
    
    print("\n🔍 Prüfe Ticket-Konsistenz...")
    
    db = get_mongodb_connection()
    tickets = list(db.tickets.find({}))
    
    # Prüfe ID-Typen
    objectid_count = 0
    stringid_count = 0
    other_count = 0
    
    for ticket in tickets:
        ticket_id = ticket.get('_id')
        if isinstance(ticket_id, ObjectId):
            objectid_count += 1
        elif isinstance(ticket_id, str):
            stringid_count += 1
        else:
            other_count += 1
    
    print(f"ObjectId-Tickets: {objectid_count}")
    print(f"String-ID-Tickets: {stringid_count}")
    print(f"Andere ID-Typen: {other_count}")
    
    # Prüfe auf doppelte Titel
    titles = [t.get('title', '') for t in tickets]
    unique_titles = set(titles)
    
    if len(titles) != len(unique_titles):
        print("⚠️  Doppelte Titel gefunden!")
        from collections import Counter
        title_counts = Counter(titles)
        for title, count in title_counts.items():
            if count > 1:
                print(f"  - '{title}': {count}x")
    else:
        print("✅ Keine doppelten Titel gefunden")

if __name__ == "__main__":
    print("=== Ticket-Duplikat-Bereinigung ===")
    print(f"Datum: {datetime.now()}")
    print()
    
    # Prüfe Konsistenz
    check_ticket_consistency()
    
    print()
    
    # Bereinige Duplikate
    fix_duplicate_tickets()
    
    print("\n=== Bereinigung abgeschlossen ===") 