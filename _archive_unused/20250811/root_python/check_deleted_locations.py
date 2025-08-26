#!/usr/bin/env python3
"""
Überprüft und bereinigt gelöschte Standorte

Das Problem: Standorte werden nur mit 'deleted: true' markiert, 
aber nicht physisch aus der Datenbank entfernt.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def check_deleted_locations():
    """Überprüft gelöschte Standorte"""
    
    print("🔍 Überprüfe gelöschte Standorte...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # MongoDB-Verbindung
            from app.models.mongodb_database import mongodb
            print(f"  ✅ MongoDB-Verbindung hergestellt")
            
            # Alle Standorte abrufen (auch gelöschte)
            all_locations = list(mongodb.get_collection('locations').find({}))
            
            if not all_locations:
                print("  ℹ️  Keine Standorte in der Datenbank gefunden")
                return
            
            print(f"  📊 Gesamtanzahl Standorte: {len(all_locations)}")
            
            # Standorte nach Status gruppieren
            active_locations = []
            deleted_locations = []
            no_deleted_flag = []
            
            for location in all_locations:
                name = location.get('name', '')
                department = location.get('department', 'KEIN_DEPARTMENT')
                deleted = location.get('deleted', False)
                
                if deleted:
                    deleted_locations.append({
                        'name': name,
                        'department': department,
                        'id': str(location.get('_id'))
                    })
                elif 'deleted' not in location:
                    no_deleted_flag.append({
                        'name': name,
                        'department': department,
                        'id': str(location.get('_id'))
                    })
                else:
                    active_locations.append({
                        'name': name,
                        'department': department,
                        'id': str(location.get('_id'))
                    })
            
            # Ergebnisse anzeigen
            print(f"\n📋 Aktive Standorte: {len(active_locations)}")
            for loc in active_locations:
                print(f"  ✅ {loc['name']} ({loc['department']})")
            
            print(f"\n🗑️  Gelöschte Standorte: {len(deleted_locations)}")
            for loc in deleted_locations:
                print(f"  ❌ {loc['name']} ({loc['department']}) - ID: {loc['id']}")
            
            print(f"\n⚠️  Standorte ohne deleted-Flag: {len(no_deleted_flag)}")
            for loc in no_deleted_flag:
                print(f"  ⚠️  {loc['name']} ({loc['department']}) - ID: {loc['id']}")
            
            # Überprüfe Duplikate
            print(f"\n🔍 Überprüfe auf Duplikate...")
            name_dept_count = {}
            
            for location in all_locations:
                name = location.get('name', '')
                department = location.get('department', 'KEIN_DEPARTMENT')
                key = f"{name}_{department}"
                
                if key not in name_dept_count:
                    name_dept_count[key] = []
                
                name_dept_count[key].append({
                    'id': str(location.get('_id')),
                    'deleted': location.get('deleted', False)
                })
            
            duplicates_found = False
            for key, locations in name_dept_count.items():
                if len(locations) > 1:
                    if not duplicates_found:
                        print(f"  ⚠️  Duplikate gefunden:")
                        duplicates_found = True
                    
                    name, dept = key.split('_', 1)
                    print(f"    - Name: '{name}' in {dept} ({len(locations)} Einträge):")
                    for loc in locations:
                        status = "GELÖSCHT" if loc['deleted'] else "AKTIV"
                        print(f"      * ID: {loc['id']}, Status: {status}")
            
            if not duplicates_found:
                print(f"  ✅ Keine Duplikate gefunden")
            
            return {
                'total': len(all_locations),
                'active': len(active_locations),
                'deleted': len(deleted_locations),
                'no_flag': len(no_deleted_flag),
                'duplicates': duplicates_found
            }
            
    except Exception as e:
        print(f"❌ Fehler beim Überprüfen: {e}")
        import traceback
        traceback.print_exc()
        return None

def cleanup_deleted_locations():
    """Bereinigt gelöschte Standorte"""
    
    print("\n🧹 Bereinige gelöschte Standorte...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models.mongodb_database import mongodb
            
            collection = mongodb.get_collection('locations')
            
            # 1. Alle gelöschten Standorte physisch entfernen
            deleted_result = collection.delete_many({'deleted': True})
            print(f"  🗑️  {deleted_result.deleted_count} gelöschte Standorte entfernt")
            
            # 2. Standorte ohne deleted-Flag mit deleted: false markieren
            no_flag_result = collection.update_many(
                {'deleted': {'$exists': False}},
                {'$set': {'deleted': False}}
            )
            print(f"  🔧 {no_flag_result.modified_count} Standorte ohne deleted-Flag korrigiert")
            
            # 3. Finale Anzahl
            final_count = collection.count_documents({})
            print(f"  📊 Finale Anzahl Standorte: {final_count}")
            
            return True
            
    except Exception as e:
        print(f"  ❌ Fehler bei der Bereinigung: {e}")
        return False

if __name__ == '__main__':
    print("=" * 70)
    print("🔍 Scandy Standorte Überprüfung & Bereinigung")
    print("=" * 70)
    
    # Überprüfung
    result = check_deleted_locations()
    
    if result:
        print(f"\n📊 Zusammenfassung:")
        print(f"  - Gesamt: {result['total']}")
        print(f"  - Aktiv: {result['active']}")
        print(f"  - Gelöscht: {result['deleted']}")
        print(f"  - Ohne Flag: {result['no_flag']}")
        print(f"  - Duplikate: {'Ja' if result['duplicates'] else 'Nein'}")
        
        # Bereinigung anbieten
        if result['deleted'] > 0 or result['no_flag'] > 0:
            print(f"\n🧹 Möchtest du die gelöschten Standorte bereinigen?")
            response = input("Bereinigung durchführen? (ja/nein): ").lower().strip()
            
            if response in ['ja', 'j', 'yes', 'y']:
                if cleanup_deleted_locations():
                    print(f"\n✅ Bereinigung erfolgreich!")
                else:
                    print(f"\n❌ Bereinigung fehlgeschlagen!")
            else:
                print(f"\n❌ Bereinigung abgebrochen!")
        else:
            print(f"\n✅ Keine Bereinigung nötig!")
    else:
        print(f"\n❌ Überprüfung fehlgeschlagen!")
        sys.exit(1)
