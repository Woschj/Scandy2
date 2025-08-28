#!/usr/bin/env python3
"""
Datenbank-Gesundheitscheck für Scandy

Überprüft auf:
- Doppelte Einträge
- Einträge ohne Department
- Vermischte Daten zwischen Abteilungen
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def check_database_health():
    """Überprüft die Datenbank-Gesundheit"""
    
    print("🏥 Datenbank-Gesundheitscheck für Scandy...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # MongoDB-Verbindung
            from app.models.mongodb_database import mongodb
            print(f"  ✅ MongoDB-Verbindung hergestellt")
            
            # Collections überprüfen
            collections_to_check = ['locations', 'categories', 'ticket_categories', 'feature_settings']
            
            for collection_name in collections_to_check:
                print(f"\n🔍 Überprüfe Collection: {collection_name}")
                
                try:
                    # Alle Dokumente abrufen
                    all_docs = list(mongodb.get_collection(collection_name).find({}))
                    
                    if not all_docs:
                        print(f"  ℹ️  Collection ist leer")
                        continue
                    
                    # Department-Statistiken
                    dept_stats = defaultdict(int)
                    no_dept_count = 0
                    duplicate_names = defaultdict(list)
                    
                    for doc in all_docs:
                        dept = doc.get('department', 'KEIN_DEPARTMENT')
                        name = doc.get('name', 'KEIN_NAME')
                        
                        if dept == 'KEIN_DEPARTMENT':
                            no_dept_count += 1
                        else:
                            dept_stats[dept] += 1
                        
                        # Sammle Einträge mit gleichem Namen
                        duplicate_names[name].append({
                            'id': str(doc.get('_id')),
                            'department': dept,
                            'deleted': doc.get('deleted', False)
                        })
                    
                    # Zeige Statistiken
                    print(f"  📊 Gesamtanzahl Dokumente: {len(all_docs)}")
                    print(f"  📊 Dokumente ohne Department: {no_dept_count}")
                    
                    if dept_stats:
                        print(f"  📊 Dokumente pro Department:")
                        for dept, count in sorted(dept_stats.items()):
                            print(f"    - {dept}: {count}")
                    
                    # Überprüfe auf Duplikate
                    duplicates_found = False
                    for name, entries in duplicate_names.items():
                        if len(entries) > 1:
                            if not duplicates_found:
                                print(f"  ⚠️  Duplikate gefunden:")
                                duplicates_found = True
                            
                            print(f"    - Name: '{name}' ({len(entries)} Einträge):")
                            for entry in entries:
                                status = "GELÖSCHT" if entry['deleted'] else "AKTIV"
                                print(f"      * ID: {entry['id']}, Department: {entry['department']}, Status: {status}")
                    
                    if not duplicates_found:
                        print(f"  ✅ Keine Duplikate gefunden")
                    
                    # Überprüfe auf gelöschte Einträge
                    deleted_count = sum(1 for doc in all_docs if doc.get('deleted', False))
                    if deleted_count > 0:
                        print(f"  🗑️  Gelöschte Einträge: {deleted_count}")
                    
                except Exception as e:
                    print(f"  ❌ Fehler bei Collection {collection_name}: {e}")
            
            print("\n🎉 Datenbank-Gesundheitscheck abgeschlossen!")
            
    except Exception as e:
        print(f"❌ Fehler beim Gesundheitscheck: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def suggest_cleanup():
    """Schlägt Bereinigungsmaßnahmen vor"""
    
    print("\n🧹 Vorgeschlagene Bereinigungsmaßnahmen:")
    print("1. Alle Einträge ohne Department löschen oder einem Standard-Department zuordnen")
    print("2. Doppelte Einträge bereinigen (nur einen pro Name/Department behalten)")
    print("3. Gelöschte Einträge physisch aus der Datenbank entfernen")
    print("4. Department-Scoping korrekt konfigurieren")
    print("5. Neue Einträge werden automatisch dem aktuellen Department zugeordnet")

if __name__ == '__main__':
    print("=" * 70)
    print("🏥 Scandy Datenbank-Gesundheitscheck")
    print("=" * 70)
    
    success = check_database_health()
    
    if success:
        suggest_cleanup()
        print("\n✅ Gesundheitscheck erfolgreich abgeschlossen!")
    else:
        print("\n❌ Gesundheitscheck fehlgeschlagen!")
        sys.exit(1)
