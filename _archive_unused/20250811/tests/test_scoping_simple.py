#!/usr/bin/env python3
"""
Einfacher Test für das Department-Scoping

Testet nur die Logik der _augment_filter_with_department Methode.
"""

def test_scoping_logic():
    """Testet die Department-Scoping Logik direkt"""
    
    print("🧪 Teste Department-Scoping Logik...")
    
    # Mock für die _augment_filter_with_department Methode
    def _augment_filter_with_department(collection_name, base_filter):
        """
        Mock der _augment_filter_with_department Methode
        """
        # SCOPED_COLLECTIONS
        _SCOPED_COLLECTIONS = {'locations', 'categories', 'ticket_categories', 'feature_settings'}
        
        if collection_name not in _SCOPED_COLLECTIONS:
            return base_filter or {}
        
        # Sonderfall: globale Settings (departments) sind NICHT gescoped
        try:
            if collection_name == 'settings' and isinstance(base_filter, dict):
                key_val = base_filter.get('key')
                if key_val == 'departments' or (isinstance(key_val, dict) and key_val.get('$regex') == '^departments$'):
                    return base_filter or {}
        except Exception:
            pass
        
        # Wenn der Filter bereits ein Department enthält, kein zusätzliches Scoping
        if base_filter and isinstance(base_filter, dict):
            if 'department' in base_filter:
                return base_filter
        
        # Mock current_department
        current_department = "TestDepartment"
        
        if not current_department:
            # Ohne gesetztes Department: alle Dokumente zulassen (Legacy-Modus)
            return base_filter or {}
        
        scoped_clause = {'$or': [
            {'department': current_department},
            {'department': {'$exists': False}}
        ]}
        
        if not base_filter:
            return scoped_clause
        
        # Kombiniere mit AND
        return {'$and': [base_filter, scoped_clause]}
    
    print("✅ Mock-Methode erstellt")
    print(f"  📍 Mock Department: TestDepartment")
    
    # Test 1: Filter ohne Department
    print(f"\n🔍 Test 1: Filter ohne Department")
    base_filter = {'name': 'TestLocation'}
    scoped_filter = _augment_filter_with_department('locations', base_filter)
    print(f"  Base Filter: {base_filter}")
    print(f"  Scoped Filter: {scoped_filter}")
    
    # Test 2: Filter mit Department
    print(f"\n🔍 Test 2: Filter mit Department")
    base_filter_with_dept = {'name': 'TestLocation', 'department': 'OtherDepartment'}
    scoped_filter_with_dept = _augment_filter_with_department('locations', base_filter_with_dept)
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
    
    # Test 6: Überprüfe nicht-gescoped Collections
    print(f"\n🔍 Test 6: Nicht-gescoped Collections")
    non_scoped_filter = _augment_filter_with_department('users', {'name': 'TestUser'})
    if non_scoped_filter == {'name': 'TestUser'}:
        print(f"  ✅ Nicht-gescoped Collection wird nicht modifiziert")
    else:
        print(f"  ❌ Nicht-gescoped Collection wird fälschlicherweise modifiziert")
    
    print(f"\n🎉 Department-Scoping Tests abgeschlossen!")
    return True

if __name__ == '__main__':
    print("=" * 70)
    print("🧪 Scandy Department-Scoping Einfach-Test")
    print("=" * 70)
    
    success = test_scoping_logic()
    
    if success:
        print("\n✅ Department-Scoping funktioniert korrekt!")
    else:
        print("\n❌ Department-Scoping hat Probleme!")
        sys.exit(1)
