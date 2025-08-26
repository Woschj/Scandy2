#!/usr/bin/env python3
"""
Migration-Script für Feature-Einstellungen

Dieses Script migriert bestehende globale Feature-Einstellungen
zu department-scoped Features.
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
from app.models.feature_system import feature_system

def migrate_features_to_departments():
    """Migriert bestehende Feature-Einstellungen zu Departments"""
    
    print("🔄 Starte Feature-Migration zu Departments...")
    
    try:
        # App-Context erstellen
        app = create_app()
        
        with app.app_context():
            # 1. Lade alle bestehenden Feature-Einstellungen
            print("📋 Lade bestehende Feature-Einstellungen...")
            existing_features = {}
            rows = mongodb.find('settings', {'key': {'$regex': '^feature_'}})
            
            for row in rows:
                feature_name = row['key'].replace('feature_', '')
                enabled = row.get('value', False)
                existing_features[feature_name] = enabled
                print(f"  - {feature_name}: {enabled}")
            
            if not existing_features:
                print("ℹ️  Keine bestehenden Feature-Einstellungen gefunden.")
                return
            
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
            
            # 3. Migriere Features zu jedem Department
            print("\n🚀 Migriere Features zu Departments...")
            migrated_count = 0
            
            for department in departments:
                if not isinstance(department, str) or not department.strip():
                    continue
                    
                print(f"\n  📍 Department: {department}")
                
                for feature_name, enabled in existing_features.items():
                    try:
                        # Feature für Department setzen
                        if feature_system.set_feature_setting(feature_name, enabled, department):
                            print(f"    ✅ {feature_name}: {enabled}")
                            migrated_count += 1
                        else:
                            print(f"    ❌ {feature_name}: Fehler beim Setzen")
                    except Exception as e:
                        print(f"    ❌ {feature_name}: {e}")
            
            # 4. Lösche alte globale Feature-Einstellungen
            print(f"\n🗑️  Lösche alte globale Feature-Einstellungen...")
            try:
                result = mongodb.delete_many('settings', {'key': {'$regex': '^feature_'}})
                print(f"  {result.deleted_count} alte Einstellungen gelöscht")
            except Exception as e:
                print(f"  ❌ Fehler beim Löschen: {e}")
            
            # 5. Erstelle feature_settings Collection-Index
            print("\n📊 Erstelle Collection-Index...")
            try:
                from pymongo import ASCENDING
                mongodb.get_collection('feature_settings').create_index([
                    ('department', ASCENDING),
                    ('feature_name', ASCENDING)
                ], unique=True)
                print("  ✅ Index erstellt")
            except Exception as e:
                print(f"  ❌ Fehler beim Index-Erstellen: {e}")
            
            print(f"\n🎉 Migration abgeschlossen!")
            print(f"  - {migrated_count} Features migriert")
            print(f"  - {len(departments)} Departments verarbeitet")
            print(f"  - Neue Collection: feature_settings")
            
            # 6. Zeige aktuelle Department-Features
            print("\n📋 Aktuelle Department-Features:")
            all_features = feature_system.get_all_department_features()
            for dept, features in all_features.items():
                print(f"\n  🏢 {dept}:")
                for feature_name, enabled in features.items():
                    status = "✅" if enabled else "❌"
                    print(f"    {status} {feature_name}")
            
    except Exception as e:
        print(f"❌ Fehler bei der Migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 Scandy Feature-Migration zu Departments")
    print("=" * 60)
    
    success = migrate_features_to_departments()
    
    if success:
        print("\n✅ Migration erfolgreich abgeschlossen!")
        print("\n💡 Nächste Schritte:")
        print("  1. Starte die Scandy-App neu")
        print("  2. Gehe zu Admin -> Feature-Einstellungen")
        print("  3. Features sind jetzt pro Abteilung konfigurierbar")
    else:
        print("\n❌ Migration fehlgeschlagen!")
        sys.exit(1)
