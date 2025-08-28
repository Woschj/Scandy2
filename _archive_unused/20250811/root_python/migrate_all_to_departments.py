#!/usr/bin/env python3
"""
Umfassendes Migration-Script für alle Bereiche

Dieses Script migriert alle bestehenden globalen Einstellungen
zu department-scoped Collections.
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

def migrate_all_to_departments():
    """Migriert alle Bereiche zu Departments"""
    
    print("🔄 Starte umfassende Migration zu Departments...")
    
    try:
        # App-Context erstellen
        app = create_app()
        
        with app.app_context():
            # 1. Lade alle verfügbaren Departments
            print("🏢 Lade verfügbare Departments...")
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
            
            # 2. Migriere Kategorien
            print("\n📋 Migriere Kategorien...")
            migrate_categories(departments)
            
            # 3. Migriere Standorte
            print("\n📍 Migriere Standorte...")
            migrate_locations(departments)
            
            # 4. Migriere Ticket-Kategorien
            print("\n🎫 Migriere Ticket-Kategorien...")
            migrate_ticket_categories(departments)
            
            # 5. Erstelle Collection-Indizes
            print("\n📊 Erstelle Collection-Indizes...")
            create_collection_indexes()
            
            print("\n🎉 Migration abgeschlossen!")
            
    except Exception as e:
        print(f"❌ Fehler bei der Migration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def migrate_categories(departments):
    """Migriert Kategorien zu Departments"""
    try:
        # Lade bestehende Kategorien
        categories_setting = mongodb.find_one('settings', {'key': 'categories'})
        existing_categories = []
        
        if categories_setting and 'value' in categories_setting:
            if isinstance(categories_setting['value'], list):
                existing_categories = categories_setting['value']
            elif isinstance(categories_setting['value'], dict):
                for dept, cats in categories_setting['value'].items():
                    if isinstance(cats, list):
                        existing_categories.extend(cats)
        
        if not existing_categories:
            print("  ℹ️  Keine bestehenden Kategorien gefunden.")
            return
        
        print(f"  Gefundene Kategorien: {', '.join(existing_categories)}")
        
        # Migriere zu jedem Department
        migrated_count = 0
        for department in departments:
            if not isinstance(department, str) or not department.strip():
                continue
                
            print(f"    📍 Department: {department}")
            
            for category in existing_categories:
                if not isinstance(category, str) or not category.strip():
                    continue
                    
                try:
                    # Prüfe ob bereits existiert
                    existing = mongodb.find_one('categories', {
                        'name': category.strip(),
                        'department': department,
                        'deleted': {'$ne': True}
                    })
                    
                    if not existing:
                        # Erstelle neue Kategorie
                        from datetime import datetime
                        category_data = {
                            'name': category.strip(),
                            'department': department,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now(),
                            'deleted': False
                        }
                        
                        from datetime import datetime
                        mongodb.insert_one('categories', category_data)
                        print(f"      ✅ {category}: erstellt")
                        migrated_count += 1
                    else:
                        print(f"      ⚠️  {category}: bereits vorhanden")
                        
                except Exception as e:
                    print(f"      ❌ {category}: {e}")
        
        print(f"  {migrated_count} Kategorien migriert")
        
    except Exception as e:
        print(f"  ❌ Fehler bei Kategorien-Migration: {e}")

def migrate_locations(departments):
    """Migriert Standorte zu Departments"""
    try:
        # Lade bestehende Standorte
        locations_setting = mongodb.find_one('settings', {'key': 'locations'})
        existing_locations = []
        
        if locations_setting and 'value' in locations_setting:
            if isinstance(locations_setting['value'], list):
                existing_locations = locations_setting['value']
            elif isinstance(locations_setting['value'], dict):
                for dept, locs in locations_setting['value'].items():
                    if isinstance(locs, list):
                        existing_locations.extend(locs)
        
        if not existing_locations:
            print("  ℹ️  Keine bestehenden Standorte gefunden.")
            return
        
        print(f"  Gefundene Standorte: {', '.join(existing_locations)}")
        
        # Migriere zu jedem Department
        migrated_count = 0
        for department in departments:
            if not isinstance(department, str) or not department.strip():
                continue
                
            print(f"    📍 Department: {department}")
            
            for location in existing_locations:
                if not isinstance(location, str) or not location.strip():
                    continue
                    
                try:
                    # Prüfe ob bereits existiert
                    existing = mongodb.find_one('locations', {
                        'name': location.strip(),
                        'department': department,
                        'deleted': {'$ne': True}
                    })
                    
                    if not existing:
                        # Erstelle neuen Standort
                        from datetime import datetime
                        location_data = {
                            'name': location.strip(),
                            'department': department,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now(),
                            'deleted': False
                        }
                        
                        mongodb.insert_one('locations', location_data)
                        print(f"      ✅ {location}: erstellt")
                        migrated_count += 1
                    else:
                        print(f"      ⚠️  {location}: bereits vorhanden")
                        
                except Exception as e:
                    print(f"      ❌ {location}: {e}")
        
        print(f"  {migrated_count} Standorte migriert")
        
    except Exception as e:
        print(f"  ❌ Fehler bei Standorte-Migration: {e}")

def migrate_ticket_categories(departments):
    """Migriert Ticket-Kategorien zu Departments"""
    try:
        # Lade bestehende Ticket-Kategorien
        categories_setting = mongodb.find_one('settings', {'key': 'categories'})
        existing_categories = []
        
        if categories_setting and 'value' in categories_setting:
            if isinstance(categories_setting['value'], list):
                existing_categories = categories_setting['value']
            elif isinstance(categories_setting['value'], dict):
                for dept, cats in categories_setting['value'].items():
                    if isinstance(cats, list):
                        existing_categories.extend(cats)
        
        if not existing_categories:
            print("  ℹ️  Keine bestehenden Ticket-Kategorien gefunden.")
            return
        
        print(f"  Gefundene Ticket-Kategorien: {', '.join(existing_categories)}")
        
        # Migriere zu jedem Department
        migrated_count = 0
        for department in departments:
            if not isinstance(department, str) or not department.strip():
                continue
                
            print(f"    📍 Department: {department}")
            
            for category in existing_categories:
                if not isinstance(category, str) or not category.strip():
                    continue
                    
                try:
                    # Prüfe ob bereits existiert
                    existing = mongodb.find_one('ticket_categories', {
                        'name': category.strip(),
                        'department': department,
                        'deleted': {'$ne': True}
                    })
                    
                    if not existing:
                        # Erstelle neue Ticket-Kategorie
                        from datetime import datetime
                        category_data = {
                            'name': category.strip(),
                            'department': department,
                            'created_at': datetime.now(),
                            'updated_at': datetime.now(),
                            'deleted': False
                        }
                        
                        mongodb.insert_one('ticket_categories', category_data)
                        print(f"      ✅ {category}: erstellt")
                        migrated_count += 1
                    else:
                        print(f"      ⚠️  {category}: bereits vorhanden")
                        
                except Exception as e:
                    print(f"      ❌ {category}: {e}")
        
        print(f"  {migrated_count} Ticket-Kategorien migriert")
        
    except Exception as e:
        print(f"  ❌ Fehler bei Ticket-Kategorien-Migration: {e}")

def create_collection_indexes():
    """Erstellt Collection-Indizes"""
    try:
        from pymongo import ASCENDING
        
        # Kategorien-Index
        try:
            mongodb.get_collection('categories').create_index([
                ('department', ASCENDING),
                ('name', ASCENDING)
            ], unique=True)
            print("  ✅ Kategorien-Index erstellt")
        except Exception as e:
            print(f"  ❌ Fehler beim Kategorien-Index: {e}")
        
        # Standorte-Index
        try:
            mongodb.get_collection('locations').create_index([
                ('department', ASCENDING),
                ('name', ASCENDING)
            ], unique=True)
            print("  ✅ Standorte-Index erstellt")
        except Exception as e:
            print(f"  ❌ Fehler beim Standorte-Index: {e}")
        
        # Ticket-Kategorien-Index
        try:
            mongodb.get_collection('ticket_categories').create_index([
                ('department', ASCENDING),
                ('name', ASCENDING)
            ], unique=True)
            print("  ✅ Ticket-Kategorien-Index erstellt")
        except Exception as e:
            print(f"  ❌ Fehler beim Ticket-Kategorien-Index: {e}")
        
        # Feature-Settings-Index
        try:
            mongodb.get_collection('feature_settings').create_index([
                ('department', ASCENDING),
                ('feature_name', ASCENDING)
            ], unique=True)
            print("  ✅ Feature-Settings-Index erstellt")
        except Exception as e:
            print(f"  ❌ Fehler beim Feature-Settings-Index: {e}")
        
    except Exception as e:
        print(f"  ❌ Fehler beim Index-Erstellen: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 Scandy Umfassende Migration zu Departments")
    print("=" * 60)
    
    success = migrate_all_to_departments()
    
    if success:
        print("\n✅ Migration erfolgreich abgeschlossen!")
        print("\n💡 Nächste Schritte:")
        print("  1. Starte die Scandy-App neu")
        print("  2. Alle Bereiche sind jetzt pro Abteilung konfigurierbar")
        print("  3. Features, Handlungsfelder, Kategorien und Standorte sind gescoped")
    else:
        print("\n❌ Migration fehlgeschlagen!")
        sys.exit(1)
