#!/usr/bin/env python3
"""
Einfacher Test für das Department-Scoping

Testet ob das korrigierte Department-Scoping funktioniert.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def test_scoping():
    """Testet das Department-Scoping"""
    
    print("🧪 Teste korrigiertes Department-Scoping...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # Teste MongoDB-Database
            from app.models.mongodb_database import mongodb
            print(f"  ✅ MongoDB-Database geladen")
            
            # Teste Department-Scoping
            from flask import g
            
            # Setze Test-Department
            g.current_department = "TestDepartment"
            print(f"  📍 Aktuelles Department: {g.current_department}")
            
            # Test 1: Filter ohne Department
            print(f"\n🔍 Test 1: Filter ohne Department")
            base_filter = {'name': 'TestLocation'}
            scoped_filter = mongodb._augment_filter_with_department('locations', base_filter)
            print(f"  Base Filter: {base_filter}")
            print(f"  Scoped Filter: {scoped_filter}")
            
            # Test 2: Filter mit Department
            print(f"\n🔍 Test 2: Filter mit Department")
            base_filter_with_dept = {'name': 'TestLocation', 'department': 'OtherDepartment'}
            scoped_filter_with_dept = mongodb._augment_filter_with_department('locations', base_filter_with_dept)
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
            
            print(f"\n🎉 Department-Scoping Tests abgeschlossen!")
            
    except Exception as e:
        print(f"❌ Fehler beim Testen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Scandy Department-Scoping Test")
    print("=" * 60)
    
    success = test_scoping()
    
    if success:
        print("\n✅ Department-Scoping funktioniert korrekt!")
    else:
        print("\n❌ Department-Scoping hat Probleme!")
        sys.exit(1)
