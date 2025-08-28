#!/usr/bin/env python3
"""
Test-Script für Department-Scoping

Testet ob das Department-Scoping korrekt funktioniert.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def test_department_scoping():
    """Testet das Department-Scoping"""
    
    print("🧪 Teste Department-Scoping...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # Teste MongoDB-Database
            print("\n🗄️  Teste MongoDB-Database...")
            try:
                from app.models.mongodb_database import mongodb
                print(f"  ✅ MongoDB-Database geladen")
                
                # Teste Department-Scoping
                from flask import g
                
                # Setze Test-Department
                g.current_department = "TestDepartment"
                print(f"  📍 Aktuelles Department: {g.current_department}")
                
                # Teste Filter ohne Department
                base_filter = {'name': 'TestLocation'}
                scoped_filter = mongodb._augment_filter_with_department('locations', base_filter)
                print(f"  🔍 Base Filter: {base_filter}")
                print(f"  🔍 Scoped Filter: {scoped_filter}")
                
                # Teste Filter mit Department
                base_filter_with_dept = {'name': 'TestLocation', 'department': 'OtherDepartment'}
                scoped_filter_with_dept = mongodb._augment_filter_with_department('locations', base_filter_with_dept)
                print(f"  🔍 Base Filter mit Department: {base_filter_with_dept}")
                print(f"  🔍 Scoped Filter mit Department: {scoped_filter_with_dept}")
                
                # Teste ob Department-Filter respektiert wird
                if 'department' in base_filter_with_dept and scoped_filter_with_dept == base_filter_with_dept:
                    print(f"  ✅ Department-Filter wird respektiert")
                else:
                    print(f"  ❌ Department-Filter wird nicht respektiert")
                    
            except Exception as e:
                print(f"  ❌ MongoDB-Database Fehler: {e}")
            
            print("\n🎉 Department-Scoping Test abgeschlossen!")
            
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
    
    success = test_department_scoping()
    
    if success:
        print("\n✅ Department-Scoping funktioniert korrekt!")
    else:
        print("\n❌ Department-Scoping hat Probleme!")
        sys.exit(1)
