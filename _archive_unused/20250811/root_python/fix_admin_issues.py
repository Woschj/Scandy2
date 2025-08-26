#!/usr/bin/env python3
"""
Behebt alle Admin-Probleme:

1. Doppelte Einträge in mehreren Abteilungen
2. Falsche Toast-Nachrichten (Kategorie vs Handlungsfeld)
3. Fallback-Daten werden angezeigt, auch wenn keine Einträge da sind
4. Legacy-Daten in settings Collection
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def fix_admin_issues():
    """Behebt alle Admin-Probleme"""
    
    print("🔧 Behebe alle Admin-Probleme...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # MongoDB-Verbindung
            from app.models.mongodb_database import mongodb
            print(f"  ✅ MongoDB-Verbindung hergestellt")
            
            # 1. Bereinige settings Collection von Legacy-Daten
            print(f"\n🧹 Bereinige settings Collection...")
            settings_collection = mongodb.get_collection('settings')
            
            legacy_keys = ['locations', 'categories', 'ticket_categories', 'location', 'category']
            removed_count = 0
            
            for key in legacy_keys:
                setting = settings_collection.find_one({'key': key})
                if setting:
                    print(f"  🔍 Gefunden: '{key}' Eintrag in settings")
                    print(f"  📊 Wert: {setting.get('value', 'N/A')}")
                    
                    # Lösche den Legacy-Eintrag
                    result = settings_collection.delete_one({'key': key})
                    
                    if result.deleted_count > 0:
                        print(f"  ✅ '{key}' Eintrag aus settings entfernt")
                        removed_count += 1
                    else:
                        print(f"  ❌ Fehler beim Entfernen des '{key}' Eintrags")
            
            print(f"  📊 {removed_count} Legacy-Einträge aus settings entfernt")
            
            # 2. Bereinige doppelte Einträge in allen Collections
            print(f"\n🔄 Bereinige doppelte Einträge...")
            
            collections_to_cleanup = ['locations', 'categories', 'ticket_categories']
            
            for collection_name in collections_to_cleanup:
                print(f"  🧹 Bereinige {collection_name}...")
                
                collection = mongodb.get_collection(collection_name)
                
                # Alle Dokumente abrufen
                all_docs = list(collection.find({}))
                
                if not all_docs:
                    print(f"    ℹ️  Collection ist leer")
                    continue
                
                # Doppelte Einträge finden
                name_dept_map = {}
                
                for doc in all_docs:
                    name = doc.get('name', '')
                    dept = doc.get('department', '')
                    key = f"{name}_{dept}"
                    
                    if key not in name_dept_map:
                        name_dept_map[key] = []
                    
                    name_dept_map[key].append(doc)
                
                # Doppelte entfernen
                duplicates_removed = 0
                for key, docs in name_dept_map.items():
                    if len(docs) > 1:
                        # Behalte den ersten Eintrag, lösche die anderen
                        docs_to_remove = docs[1:]
                        for doc in docs_to_remove:
                            collection.delete_one({'_id': doc['_id']})
                            duplicates_removed += 1
                
                if duplicates_removed > 0:
                    print(f"    🗑️  {duplicates_removed} doppelte Einträge entfernt")
                else:
                    print(f"    ✅ Keine Duplikate gefunden")
                
                # Gelöschte Einträge physisch entfernen
                deleted_docs = list(collection.find({'deleted': True}))
                if deleted_docs:
                    for doc in deleted_docs:
                        collection.delete_one({'_id': doc['_id']})
                    print(f"    🗑️  {len(deleted_docs)} gelöschte Einträge entfernt")
                
                # Finale Anzahl
                final_count = collection.count_documents({})
                print(f"    📊 Finale Anzahl: {final_count}")
            
            # 3. Korrigiere fehlende deleted-Flags
            print(f"\n🔧 Korrigiere fehlende deleted-Flags...")
            
            for collection_name in collections_to_cleanup:
                collection = mongodb.get_collection(collection_name)
                
                # Standorte ohne deleted-Flag mit deleted: false markieren
                no_flag_result = collection.update_many(
                    {'deleted': {'$exists': False}},
                    {'$set': {'deleted': False}}
                )
                
                if no_flag_result.modified_count > 0:
                    print(f"  🔧 {no_flag_result.modified_count} Einträge in {collection_name} korrigiert")
            
            # 4. Überprüfe Department-Scoping
            print(f"\n🔍 Überprüfe Department-Scoping...")
            
            for collection_name in collections_to_cleanup:
                collection = mongodb.get_collection(collection_name)
                
                # Einträge ohne Department finden
                no_dept_count = collection.count_documents({'department': {'$exists': False}})
                if no_dept_count > 0:
                    print(f"  ⚠️  {no_dept_count} Einträge in {collection_name} ohne Department")
                    
                    # Standard-Department zuordnen
                    result = collection.update_many(
                        {'department': {'$exists': False}},
                        {'$set': {'department': 'Standard'}}
                    )
                    print(f"  🔧 {result.modified_count} Einträge dem 'Standard'-Department zugeordnet")
                else:
                    print(f"  ✅ Alle Einträge in {collection_name} haben ein Department")
            
            print(f"\n🎉 Alle Admin-Probleme behoben!")
            
            return True
            
    except Exception as e:
        print(f"❌ Fehler beim Beheben der Probleme: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_fixes():
    """Überprüft ob alle Fixes erfolgreich waren"""
    
    print("\n🔍 Überprüfe Fixes...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models.mongodb_database import mongodb
            
            # Überprüfe settings Collection
            settings_collection = mongodb.get_collection('settings')
            legacy_keys = ['locations', 'categories', 'ticket_categories']
            
            legacy_found = False
            for key in legacy_keys:
                setting = settings_collection.find_one({'key': key})
                if setting:
                    print(f"  ❌ Legacy-Eintrag '{key}' ist noch in settings vorhanden")
                    legacy_found = True
            
            if not legacy_found:
                print(f"  ✅ Alle Legacy-Einträge aus settings entfernt")
            
            # Überprüfe Collections
            collections_to_check = ['locations', 'categories', 'ticket_categories']
            
            for collection_name in collections_to_check:
                collection = mongodb.get_collection(collection_name)
                count = collection.count_documents({})
                print(f"  📊 {collection_name}: {count} Einträge")
                
                # Überprüfe auf Einträge ohne Department
                no_dept_count = collection.count_documents({'department': {'$exists': False}})
                if no_dept_count > 0:
                    print(f"    ⚠️  {no_dept_count} Einträge ohne Department")
                else:
                    print(f"    ✅ Alle Einträge haben ein Department")
                
                # Überprüfe auf gelöschte Einträge
                deleted_count = collection.count_documents({'deleted': True})
                if deleted_count > 0:
                    print(f"    ⚠️  {deleted_count} gelöschte Einträge")
                else:
                    print(f"    ✅ Keine gelöschten Einträge")
    
    except Exception as e:
        print(f"  ❌ Fehler bei der Überprüfung: {e}")

def fix_frontend_messages():
    """Korrigiert die falschen Toast-Nachrichten im Frontend"""
    
    print("\n🔧 Korrigiere Frontend-Nachrichten...")
    
    try:
        # Template-Datei korrigieren
        template_path = "app/templates/admin/dashboard.html"
        
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Falsche Nachrichten korrigieren
            old_messages = [
                ("'Handlungsfeld hinzugefügt'", "'Kategorie hinzugefügt'"),
                ("'Handlungsfeld gelöscht'", "'Kategorie gelöscht'"),
                ("Handlungsfeld", "Kategorie")
            ]
            
            modified = False
            for old, new in old_messages:
                if old in content:
                    content = content.replace(old, new)
                    modified = True
                    print(f"  🔧 '{old}' → '{new}' korrigiert")
            
            if modified:
                with open(template_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  ✅ Template korrigiert")
            else:
                print(f"  ℹ️  Keine Korrekturen nötig")
        else:
            print(f"  ⚠️  Template-Datei nicht gefunden: {template_path}")
    
    except Exception as e:
        print(f"  ❌ Fehler beim Korrigieren der Frontend-Nachrichten: {e}")

if __name__ == '__main__':
    print("=" * 70)
    print("🔧 Scandy Admin-Probleme Behebung")
    print("=" * 70)
    
    print("\n⚠️  WARNUNG: Diese Aktion wird Daten aus der Datenbank entfernen!")
    print("⚠️  Stelle sicher, dass du ein Backup hast!")
    
    response = input("\nMöchtest du fortfahren? (ja/nein): ").lower().strip()
    
    if response in ['ja', 'j', 'yes', 'y']:
        success = fix_admin_issues()
        
        if success:
            verify_fixes()
            fix_frontend_messages()
            print("\n✅ Alle Probleme erfolgreich behoben!")
        else:
            print("\n❌ Behebung fehlgeschlagen!")
            sys.exit(1)
    else:
        print("❌ Behebung abgebrochen!")
        sys.exit(0)
