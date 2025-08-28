#!/usr/bin/env python3
"""
Datenbank-Bereinigung für Scandy

Bereinigt:
- Doppelte Einträge
- Einträge ohne Department
- Gelöschte Einträge
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def cleanup_database():
    """Bereinigt die Datenbank"""
    
    print("🧹 Datenbank-Bereinigung für Scandy...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # MongoDB-Verbindung
            from app.models.mongodb_database import mongodb
            print(f"  ✅ MongoDB-Verbindung hergestellt")
            
            # Collections bereinigen
            collections_to_cleanup = ['locations', 'categories', 'ticket_categories']
            
            for collection_name in collections_to_cleanup:
                print(f"\n🧹 Bereinige Collection: {collection_name}")
                
                try:
                    collection = mongodb.get_collection(collection_name)
                    
                    # 1. Alle Dokumente abrufen
                    all_docs = list(collection.find({}))
                    
                    if not all_docs:
                        print(f"  ℹ️  Collection ist leer")
                        continue
                    
                    print(f"  📊 Gefundene Dokumente: {len(all_docs)}")
                    
                    # 2. Einträge ohne Department einem Standard-Department zuordnen
                    no_dept_docs = [doc for doc in all_docs if 'department' not in doc]
                    if no_dept_docs:
                        print(f"  🔧 Ordne {len(no_dept_docs)} Einträge ohne Department zu...")
                        
                        # Standard-Department finden oder erstellen
                        standard_dept = "Standard"
                        
                        for doc in no_dept_docs:
                            collection.update_one(
                                {'_id': doc['_id']},
                                {'$set': {'department': standard_dept}}
                            )
                        
                        print(f"  ✅ {len(no_dept_docs)} Einträge dem Department '{standard_dept}' zugeordnet")
                    
                    # 3. Doppelte Einträge bereinigen
                    name_dept_map = defaultdict(list)
                    all_docs = list(collection.find({}))  # Aktualisierte Daten
                    
                    for doc in all_docs:
                        name = doc.get('name', '')
                        dept = doc.get('department', '')
                        key = f"{name}_{dept}"
                        name_dept_map[key].append(doc)
                    
                    duplicates_removed = 0
                    for key, docs in name_dept_map.items():
                        if len(docs) > 1:
                            # Behalte den ersten Eintrag, lösche die anderen
                            docs_to_remove = docs[1:]
                            for doc in docs_to_remove:
                                collection.delete_one({'_id': doc['_id']})
                                duplicates_removed += 1
                    
                    if duplicates_removed > 0:
                        print(f"  🗑️  {duplicates_removed} doppelte Einträge entfernt")
                    else:
                        print(f"  ✅ Keine Duplikate gefunden")
                    
                    # 4. Gelöschte Einträge physisch entfernen
                    deleted_docs = list(collection.find({'deleted': True}))
                    if deleted_docs:
                        print(f"  🗑️  Entferne {len(deleted_docs)} gelöschte Einträge...")
                        
                        for doc in deleted_docs:
                            collection.delete_one({'_id': doc['_id']})
                        
                        print(f"  ✅ {len(deleted_docs)} gelöschte Einträge entfernt")
                    
                    # 5. Finale Statistiken
                    final_count = collection.count_documents({})
                    print(f"  📊 Finale Anzahl Dokumente: {final_count}")
                    
                except Exception as e:
                    print(f"  ❌ Fehler bei Collection {collection_name}: {e}")
            
            print("\n🎉 Datenbank-Bereinigung abgeschlossen!")
            
    except Exception as e:
        print(f"❌ Fehler bei der Bereinigung: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def verify_cleanup():
    """Überprüft ob die Bereinigung erfolgreich war"""
    
    print("\n🔍 Überprüfe Bereinigung...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models.mongodb_database import mongodb
            
            collections_to_check = ['locations', 'categories', 'ticket_categories']
            
            for collection_name in collections_to_check:
                collection = mongodb.get_collection(collection_name)
                count = collection.count_documents({})
                print(f"  📊 {collection_name}: {count} Dokumente")
                
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

if __name__ == '__main__':
    print("=" * 70)
    print("🧹 Scandy Datenbank-Bereinigung")
    print("=" * 70)
    
    print("\n⚠️  WARNUNG: Diese Aktion wird Daten aus der Datenbank entfernen!")
    print("⚠️  Stelle sicher, dass du ein Backup hast!")
    
    response = input("\nMöchtest du fortfahren? (ja/nein): ").lower().strip()
    
    if response in ['ja', 'j', 'yes', 'y']:
        success = cleanup_database()
        
        if success:
            verify_cleanup()
            print("\n✅ Bereinigung erfolgreich abgeschlossen!")
        else:
            print("\n❌ Bereinigung fehlgeschlagen!")
            sys.exit(1)
    else:
        print("❌ Bereinigung abgebrochen!")
        sys.exit(0)
