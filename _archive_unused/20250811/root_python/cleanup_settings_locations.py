#!/usr/bin/env python3
"""
Entfernt alte Standorte aus der settings Collection

Das Problem: Standorte werden aus der locations Collection gelöscht,
aber bleiben in der settings Collection als Fallback.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def cleanup_settings_locations():
    """Entfernt alte Standorte aus der settings Collection"""
    
    print("🧹 Entferne alte Standorte aus der settings Collection...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # MongoDB-Verbindung
            from app.models.mongodb_database import mongodb
            print(f"  ✅ MongoDB-Verbindung hergestellt")
            
            # Überprüfe settings Collection
            settings_collection = mongodb.get_collection('settings')
            
            # Suche nach dem 'locations' Schlüssel
            locations_setting = settings_collection.find_one({'key': 'locations'})
            
            if locations_setting:
                print(f"  🔍 Gefunden: 'locations' Eintrag in settings")
                print(f"  📊 Wert: {locations_setting.get('value', 'N/A')}")
                
                # Lösche den 'locations' Eintrag
                result = settings_collection.delete_one({'key': 'locations'})
                
                if result.deleted_count > 0:
                    print(f"  ✅ 'locations' Eintrag aus settings entfernt")
                else:
                    print(f"  ❌ Fehler beim Entfernen des 'locations' Eintrags")
            else:
                print(f"  ℹ️  Kein 'locations' Eintrag in settings gefunden")
            
            # Überprüfe auch andere mögliche Standort-Schlüssel
            other_location_keys = ['location', 'standorte', 'locations_global']
            
            for key in other_location_keys:
                setting = settings_collection.find_one({'key': key})
                if setting:
                    print(f"  🔍 Gefunden: '{key}' Eintrag in settings")
                    print(f"  📊 Wert: {setting.get('value', 'N/A')}")
                    
                    # Lösche den Eintrag
                    result = settings_collection.delete_one({'key': key})
                    
                    if result.deleted_count > 0:
                        print(f"  ✅ '{key}' Eintrag aus settings entfernt")
                    else:
                        print(f"  ❌ Fehler beim Entfernen des '{key}' Eintrags")
            
            # Überprüfe auch 'categories' und 'ticket_categories' falls gewünscht
            print(f"\n🔍 Überprüfe auch andere mögliche Legacy-Einträge...")
            
            legacy_keys = ['categories', 'ticket_categories']
            
            for key in legacy_keys:
                setting = settings_collection.find_one({'key': key})
                if setting:
                    print(f"  ⚠️  Gefunden: '{key}' Eintrag in settings")
                    print(f"  📊 Wert: {setting.get('value', 'N/A')}")
                    print(f"  💡 Hinweis: Dieser Eintrag könnte auch Legacy-Daten enthalten")
            
            # Finale Anzahl settings
            final_count = settings_collection.count_documents({})
            print(f"\n📊 Finale Anzahl Einträge in settings: {final_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Fehler bei der Bereinigung: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_cleanup():
    """Überprüft ob die Bereinigung erfolgreich war"""
    
    print("\n🔍 Überprüfe Bereinigung...")
    
    try:
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.models.mongodb_database import mongodb
            
            # Überprüfe settings Collection
            settings_collection = mongodb.get_collection('settings')
            locations_setting = settings_collection.find_one({'key': 'locations'})
            
            if not locations_setting:
                print(f"  ✅ 'locations' Eintrag erfolgreich aus settings entfernt")
            else:
                print(f"  ❌ 'locations' Eintrag ist noch in settings vorhanden")
            
            # Überprüfe locations Collection
            locations_collection = mongodb.get_collection('locations')
            locations_count = locations_collection.count_documents({})
            print(f"  📊 Standorte in locations Collection: {locations_count}")
            
            # Teste get_locations_from_settings
            try:
                from app.utils.database_helpers import get_locations_from_settings
                locations_from_settings = get_locations_from_settings()
                print(f"  📊 Standorte aus get_locations_from_settings: {len(locations_from_settings)}")
                
                if not locations_from_settings:
                    print(f"  ✅ get_locations_from_settings gibt keine Standorte zurück")
                else:
                    print(f"  ⚠️  get_locations_from_settings gibt noch Standorte zurück: {locations_from_settings}")
            except Exception as e:
                print(f"  ❌ Fehler beim Testen von get_locations_from_settings: {e}")
    
    except Exception as e:
        print(f"  ❌ Fehler bei der Überprüfung: {e}")

if __name__ == '__main__':
    print("=" * 70)
    print("🧹 Scandy Settings Standorte Bereinigung")
    print("=" * 70)
    
    print("\n⚠️  WARNUNG: Diese Aktion entfernt Legacy-Standorte aus der settings Collection!")
    print("⚠️  Stelle sicher, dass du ein Backup hast!")
    
    response = input("\nMöchtest du fortfahren? (ja/nein): ").lower().strip()
    
    if response in ['ja', 'j', 'yes', 'y']:
        success = cleanup_settings_locations()
        
        if success:
            verify_cleanup()
            print("\n✅ Bereinigung erfolgreich abgeschlossen!")
        else:
            print("\n❌ Bereinigung fehlgeschlagen!")
            sys.exit(1)
    else:
        print("❌ Bereinigung abgebrochen!")
        sys.exit(0)
