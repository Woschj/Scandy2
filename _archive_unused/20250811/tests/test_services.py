#!/usr/bin/env python3
"""
Test-Script für die neuen Services

Testet alle neuen department-scoped Services.
"""

import os
import sys
from pathlib import Path

# Füge den Projektpfad hinzu
project_home = str(Path(__file__).parent)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

def test_services():
    """Testet alle Services"""
    
    print("🧪 Teste alle Services...")
    
    try:
        # App-Context erstellen
        from app import create_app
        app = create_app()
        
        with app.app_context():
            print("✅ App-Context erstellt")
            
            # Teste CategoryService
            print("\n📋 Teste CategoryService...")
            try:
                from app.services.category_service import category_service
                print(f"  ✅ CategoryService geladen")
                
                # Teste mit Test-Department
                test_dept = "TestDepartment"
                categories = category_service.get_categories_for_department(test_dept)
                print(f"  ✅ Kategorien für {test_dept}: {len(categories)} gefunden")
                
            except Exception as e:
                print(f"  ❌ CategoryService Fehler: {e}")
            
            # Teste LocationService
            print("\n📍 Teste LocationService...")
            try:
                from app.services.location_service import location_service
                print(f"  ✅ LocationService geladen")
                
                # Teste mit Test-Department
                test_dept = "TestDepartment"
                locations = location_service.get_locations_for_department(test_dept)
                print(f"  ✅ Standorte für {test_dept}: {len(locations)} gefunden")
                
            except Exception as e:
                print(f"  ❌ LocationService Fehler: {e}")
            
            # Teste HandlungsfeldService
            print("\n🎫 Teste HandlungsfeldService...")
            try:
                from app.services.handlungsfeld_service import handlungsfeld_service
                print(f"  ✅ HandlungsfeldService geladen")
                
                # Teste mit Test-Department
                test_dept = "TestDepartment"
                handlungsfelder = handlungsfeld_service.get_handlungsfelder_for_department(test_dept)
                print(f"  ✅ Handlungsfelder für {test_dept}: {len(handlungsfelder)} gefunden")
                
            except Exception as e:
                print(f"  ❌ HandlungsfeldService Fehler: {e}")
            
            # Teste FeatureSystem
            print("\n⚙️  Teste FeatureSystem...")
            try:
                from app.models.feature_system import feature_system
                print(f"  ✅ FeatureSystem geladen")
                
                # Teste mit Test-Department
                test_dept = "TestDepartment"
                features = feature_system.get_feature_settings(test_dept)
                print(f"  ✅ Features für {test_dept}: {len(features)} gefunden")
                
            except Exception as e:
                print(f"  ❌ FeatureSystem Fehler: {e}")
            
            print("\n🎉 Alle Service-Tests abgeschlossen!")
            
    except Exception as e:
        print(f"❌ Fehler beim Testen: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Scandy Service-Test")
    print("=" * 60)
    
    success = test_services()
    
    if success:
        print("\n✅ Alle Services funktionieren korrekt!")
    else:
        print("\n❌ Einige Services haben Probleme!")
        sys.exit(1)
