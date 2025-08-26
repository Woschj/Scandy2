#!/usr/bin/env python3
"""
Fix-Script für alle Services

Korrigiert alle get_current_time() Aufrufe in den Services.
"""

import os
import sys
from pathlib import Path

def fix_services():
    """Korrigiert alle Services"""
    
    print("🔧 Korrigiere alle Services...")
    
    # Services die korrigiert werden müssen
    services = [
        'app/services/location_service.py',
        'app/services/category_service.py', 
        'app/services/handlungsfeld_service.py',
        'app/models/feature_system.py'
    ]
    
    for service_file in services:
        if os.path.exists(service_file):
            print(f"\n📝 Korrigiere {service_file}...")
            
            try:
                # Lese Datei
                with open(service_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ersetze alle get_current_time() Aufrufe
                if 'mongodb.get_current_time()' in content:
                    # Füge datetime Import hinzu falls nicht vorhanden
                    if 'from datetime import datetime' not in content:
                        content = content.replace(
                            'from typing import List, Dict, Any, Optional',
                            'from typing import List, Dict, Any, Optional\nfrom datetime import datetime'
                        )
                    
                    # Ersetze get_current_time() Aufrufe
                    content = content.replace('mongodb.get_current_time()', 'datetime.now()')
                    
                    # Schreibe Datei zurück
                    with open(service_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"  ✅ {service_file} korrigiert")
                else:
                    print(f"  ℹ️  {service_file} benötigt keine Korrektur")
                    
            except Exception as e:
                print(f"  ❌ Fehler bei {service_file}: {e}")
        else:
            print(f"  ⚠️  {service_file} nicht gefunden")
    
    print("\n🎉 Alle Services korrigiert!")

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 Scandy Service-Fix")
    print("=" * 60)
    
    fix_services()
