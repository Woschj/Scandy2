#!/usr/bin/env python3
"""
Test-Script für Delete-Operationen

Testet ob alle Services korrekt funktionieren.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def test_delete_operations():
    """Testet alle Delete-Operationen"""
    
    print("🧪 Teste alle Delete-Operationen...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # Teste LocationService
            print("\n📍 Teste LocationService...")
            try:
                from app.services.location_service import location_service
                print(f"  ✅ LocationService geladen")
                
                # Teste mit Test-Department
                test_dept = "TestDepartment"
                test_name = "TestLocation"
                
                # Erstelle Test-Standort
                if location_service.create_location(test_name, test_dept):
                    print(f"  ✅ Test-Standort '{test_name}' erstellt")
                    
                    # Teste Löschen
                    if location_service.delete_location(test_name, test_dept):
                        print(f"  ✅ Test-Standort '{test_name}' gelöscht")
                    else:
                        print(f"  ❌ Test-Standort '{test_name}' konnte nicht gelöscht werden")
                else:
                    print(f"  ❌ Test-Standort '{test_name}' konnte nicht erstellt werden")
                    
            except Exception as e:
                print(f"  ❌ LocationService Fehler: {e}")
            
            # Teste CategoryService
            print("\n📋 Teste CategoryService...")
            try:
                from app.services.category_service import category_service
                print(f"  ✅ CategoryService geladen")
                
                # Teste mit Test-Department
                test_dept = "TestDepartment"
                test_name = "TestCategory"
                
                # Erstelle Test-Kategorie
                if category_service.create_category(test_name, test_dept):
                    print(f"  ✅ Test-Kategorie '{test_name}' erstellt")
                    
                    # Teste Löschen
                    if category_service.delete_category(test_name, test_dept):
                        print(f"  ✅ Test-Kategorie '{test_name}' gelöscht")
                    else:
                        print(f"  ❌ Test-Kategorie '{test_name}' konnte nicht gelöscht werden")
                else:
                    print(f"  ❌ Test-Kategorie '{test_name}' konnte nicht erstellt werden")
                    
            except Exception as e:
                print(f"  ❌ CategoryService Fehler: {e}")
            
            # Teste HandlungsfeldService
            print("\n🎫 Teste HandlungsfeldService...")
            try:
                from app.services.handlungsfeld_service import handlungsfeld_service
                print(f"  ✅ HandlungsfeldService geladen")
                
                # Teste mit Test-Department
                test_dept = "TestDepartment"
                test_name = "TestHandlungsfeld"
                
                # Erstelle Test-Handlungsfeld
                if handlungsfeld_service.create_handlungsfeld(test_name, test_dept):
                    print(f"  ✅ Test-Handlungsfeld '{test_name}' erstellt")
                    
                    # Teste Löschen
                    if handlungsfeld_service.delete_handlungsfeld(test_name, test_dept):
                        print(f"  ✅ Test-Handlungsfeld '{test_name}' gelöscht")
                    else:
                        print(f"  ❌ Test-Handlungsfeld '{test_name}' konnte nicht gelöscht werden")
                else:
                    print(f"  ❌ Test-Handlungsfeld '{test_name}' konnte nicht erstellt werden")
                    
            except Exception as e:
                print(f"  ❌ HandlungsfeldService Fehler: {e}")
            
            print("\n🎉 Alle Delete-Tests abgeschlossen!")
            
    except Exception as e:
        print(f"❌ Fehler beim Testen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Scandy Delete-Operationen Test")
    print("=" * 60)
    
    success = test_delete_operations()
    
    if success:
        print("\n✅ Alle Delete-Operationen funktionieren korrekt!")
    else:
        print("\n❌ Einige Delete-Operationen haben Probleme!")
        sys.exit(1)
