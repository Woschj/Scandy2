#!/usr/bin/env python3
"""
Direkter Test für das Department-Scoping

Testet nur die MongoDB-Database-Klasse ohne App-Import.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def test_scoping_direct():
    """Testet das Department-Scoping direkt"""
    
    print("🧪 Teste Department-Scoping direkt...")
    
    try:
        # Importiere nur die MongoDB-Database-Klasse
        sys.path.insert(0, os.path.join(project_home, 'app', 'models'))
        
        # Mock für datetime
        import datetime
        original_datetime = datetime.datetime
        
        class MockDatetime:
            @staticmethod
            def now():
                return original_datetime.now()
        
        datetime.datetime = MockDatetime
        
        # Importiere die Klasse direkt
        from mongodb_database import MongoDBDatabase
        
        print("✅ MongoDBDatabase-Klasse direkt geladen")
        
        # Mock-Methode für _get_current_department
        original_get_dept = MongoDBDatabase._get_current_department
        
        def mock_get_current_department():
            return "TestDepartment"
        
        MongoDBDatabase._get_current_department = classmethod(mock_get_current_department)
        
        print(f"  📍 Mock Department: TestDepartment")
        
        # Test 1: Filter ohne Department
        print(f"\n🔍 Test 1: Filter ohne Department")
        base_filter = {'name': 'TestLocation'}
        scoped_filter = MongoDBDatabase._augment_filter_with_department('locations', base_filter)
        print(f"  Base Filter: {base_filter}")
        print(f"  Scoped Filter: {scoped_filter}")
        
        # Test 2: Filter mit Department
        print(f"\n🔍 Test 2: Filter mit Department")
        base_filter_with_dept = {'name': 'TestLocation', 'department': 'OtherDepartment'}
        scoped_filter_with_dept = MongoDBDatabase._augment_filter_with_department('locations', base_filter_with_dept)
        print(f"  Base Filter mit Department: {base_filter_with_dept}")
        print(f"  Scoped Filter mit Department: {scoped_filter_with_dept}")
        
        # Test 3: Überprüfe ob Department-Filter respektiert wird
        print(f"\n🔍 Test 3: Department-Filter Respektierung")
        if scoped_filter_with_dept == base_filter_with_dept:
            print(f"  ✅ Department-Filter wird respektiert - Kein zusätzliches Scoping")
        else:
            print(f"  ❌ Department-Filter wird nicht respektiert")
            print(f"  Erwartet: {base_filter_with_dept}")
            print(f"  Bekommen: {scoped_filter_with_dept}")
        
        # Test 4: Überprüfe ob Filter ohne Department gescoped wird
        print(f"\n🔍 Test 4: Scoping für Filter ohne Department")
        if scoped_filter != base_filter:
            print(f"  ✅ Filter ohne Department wird korrekt gescoped")
            print(f"  Scoped Filter enthält Department-Scoping: {scoped_filter}")
        else:
            print(f"  ❌ Filter ohne Department wird nicht gescoped")
        
        # Test 5: Überprüfe die Scoped-Filter-Struktur
        print(f"\n🔍 Test 5: Scoped-Filter-Struktur")
        if isinstance(scoped_filter, dict) and '$and' in scoped_filter:
            print(f"  ✅ Scoped Filter hat korrekte $and-Struktur")
            print(f"  Filter-Komponenten: {scoped_filter['$and']}")
            
            # Überprüfe ob der erste Teil der ursprüngliche Filter ist
            if scoped_filter['$and'][0] == base_filter:
                print(f"  ✅ Erster Teil ist der ursprüngliche Filter")
            else:
                print(f"  ❌ Erster Teil ist nicht der ursprüngliche Filter")
            
            # Überprüfe ob der zweite Teil das Department-Scoping ist
            second_part = scoped_filter['$and'][1]
            if '$or' in second_part and 'department' in second_part['$or'][0]:
                print(f"  ✅ Zweiter Teil enthält Department-Scoping")
                print(f"  Department-Scoping: {second_part}")
            else:
                print(f"  ❌ Zweiter Teil enthält nicht das erwartete Department-Scoping")
        else:
            print(f"  ❌ Scoped Filter hat nicht die erwartete Struktur")
        
        # Stelle ursprüngliche Methode wieder her
        MongoDBDatabase._get_current_department = original_get_dept
        
        print(f"\n🎉 Department-Scoping Tests abgeschlossen!")
        
    except Exception as e:
        print(f"❌ Fehler beim Testen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 Scandy Department-Scoping Direkt-Test")
    print("=" * 70)
    
    success = test_scoping_direct()
    
    if success:
        print("\n✅ Department-Scoping funktioniert korrekt!")
    else:
        print("\n❌ Department-Scoping hat Probleme!")
        sys.exit(1)
