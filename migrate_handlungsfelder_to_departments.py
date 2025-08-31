#!/usr/bin/env python3
"""
Migration-Script für Handlungsfelder

Dieses Script migriert bestehende globale Handlungsfelder
zu department-scoped Handlungsfeldern.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import create_app
from app.models.mongodb_database import mongodb
from app.services.handlungsfeld_service import handlungsfeld_service

def migrate_handlungsfelder_to_departments():
    """Migriert bestehende Handlungsfelder zu Departments"""
    
    print("🔄 Starte Handlungsfeld-Migration zu Departments...")
    
    try:
        # App-Context erstellen
        app = create_app()
        
        with app.app_context():
            # 1. Lade alle bestehenden Handlungsfelder aus settings
            print("📋 Lade bestehende Handlungsfelder...")
            categories_setting = mongodb.find_one('settings', {'key': 'categories'})
            existing_categories = []
            
            if categories_setting and 'value' in categories_setting:
                if isinstance(categories_setting['value'], list):
                    existing_categories = categories_setting['value']
                elif isinstance(categories_setting['value'], dict):
                    # Department-spezifische Kategorien
                    for dept, cats in categories_setting['value'].items():
                        if isinstance(cats, list):
                            existing_categories.extend(cats)
            
            if not existing_categories:
                print("ℹ️  Keine bestehenden Handlungsfelder gefunden.")
                return
            
            print(f"  Gefundene Handlungsfelder: {', '.join(existing_categories)}")
            
            # 2. Lade alle verfügbaren Departments
            print("\n🏢 Lade verfügbare Departments...")
            depts_setting = mongodb.find_one('settings', {'key': 'departments'})
            departments = depts_setting.get('value', []) if depts_setting else []
            
            if not departments:
                print("❌ Keine Departments gefunden! Erstelle Standard-Department...")
                departments = ['Standard']
                mongodb.update_one('settings', 
                                 {'key': 'departments'}, 
                                 {'$set': {'value': departments}}, 
                                 upsert=True)
            
            print(f"  Gefundene Departments: {', '.join(departments)}")
            
            # 3. Migriere Handlungsfelder zu jedem Department
            print("\n🚀 Migriere Handlungsfelder zu Departments...")
            migrated_count = 0
            
            for department in departments:
                if not isinstance(department, str) or not department.strip():
                    continue
                    
                print(f"\n  📍 Department: {department}")
                
                for category in existing_categories:
                    if not isinstance(category, str) or not category.strip():
                        continue
                        
                    try:
                        # Handlungsfeld für Department erstellen
                        if handlungsfeld_service.create_handlungsfeld(category.strip(), department):
                            print(f"    ✅ {category}: erstellt")
                            migrated_count += 1
                        else:
                            print(f"    ⚠️  {category}: bereits vorhanden")
                    except Exception as e:
                        print(f"    ❌ {category}: {e}")
            
            # 4. Erstelle ticket_categories Collection-Index
            print("\n📊 Erstelle Collection-Index...")
            try:
                from pymongo import ASCENDING
                mongodb.get_collection('ticket_categories').create_index([
                    ('department', ASCENDING),
                    ('name', ASCENDING)
                ], unique=True)
                print("  ✅ Index erstellt")
            except Exception as e:
                print(f"  ❌ Fehler beim Index-Erstellen: {e}")
            
            print(f"\n🎉 Migration abgeschlossen!")
            print(f"  - {migrated_count} Handlungsfelder migriert")
            print(f"  - {len(departments)} Departments verarbeitet")
            print(f"  - Neue Collection: ticket_categories")
            
            # 5. Zeige aktuelle Department-Handlungsfelder
            print("\n📋 Aktuelle Department-Handlungsfelder:")
            all_handlungsfelder = handlungsfeld_service.get_all_department_handlungsfelder()
            for dept, categories in all_handlungsfelder.items():
                print(f"\n  🏢 {dept}:")
                for category in categories:
                    print(f"    ✅ {category}")
            
    except Exception as e:
        print(f"❌ Fehler bei der Migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 Scandy Handlungsfeld-Migration zu Departments")
    print("=" * 60)
    
    success = migrate_handlungsfelder_to_departments()
    
    if success:
        print("\n✅ Migration erfolgreich abgeschlossen!")
        print("\n💡 Nächste Schritte:")
        print("  1. Starte die Scandy-App neu")
        print("  2. Gehe zu Admin -> Nutzendeverwaltung")
        print("  3. Handlungsfelder sind jetzt pro Abteilung konfigurierbar")
    else:
        print("\n❌ Migration fehlgeschlagen!")
        sys.exit(1)
