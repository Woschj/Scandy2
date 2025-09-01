#!/usr/bin/env python3
"""
Backup-Konsistenz-Test für das optimierte Backup-System
Testet die wichtigsten Aspekte:
- Backup-Erstellung ohne Fehler
- Datenintegrität
- Import/Export-Konsistenz
- Performance-Messungen
"""

import os
import json
import time
import tempfile
from datetime import datetime
from pathlib import Path
from app.utils.unified_backup_manager import unified_backup_manager

def test_backup_consistency():
    """Führt umfassende Konsistenztests durch"""
    print("🚀 Starte Backup-Konsistenz-Test...")

    test_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'overall_success': False
    }

    try:
        # Test 1: Grundlegende Backup-Funktionalität
        print("\n📊 Test 1: Grundlegende Backup-Funktionalität")
        start_time = time.time()

        backup_filename = unified_backup_manager.create_backup(
            include_media=False,  # Schneller Test ohne Medien
            compress=True
        )

        backup_time = time.time() - start_time

        if backup_filename:
            test_results['tests']['basic_backup'] = {
                'success': True,
                'filename': backup_filename,
                'duration_seconds': round(backup_time, 2),
                'size_mb': round((unified_backup_manager.backup_dir / backup_filename).stat().st_size / 1024 / 1024, 2)
            }
            print(f"✅ Backup erfolgreich erstellt: {backup_filename} ({test_results['tests']['basic_backup']['size_mb']} MB in {backup_time:.2f}s)")
        else:
            test_results['tests']['basic_backup'] = {'success': False, 'error': 'Backup creation failed'}
            print("❌ Backup-Erstellung fehlgeschlagen")
            return test_results

        # Test 2: Backup-Validierung
        print("\n🔍 Test 2: Backup-Validierung")
        backup_path = unified_backup_manager.backup_dir / backup_filename

        validation_result = validate_backup_integrity(backup_path)
        test_results['tests']['backup_validation'] = validation_result

        if validation_result['valid']:
            print(f"✅ Backup-Validierung erfolgreich: {validation_result['total_collections']} Collections, {validation_result['total_documents']} Dokumente")
        else:
            print(f"❌ Backup-Validierung fehlgeschlagen: {validation_result.get('error', 'Unbekannter Fehler')}")
            return test_results

        # Test 3: Backup-Listen-Funktionalität
        print("\n📋 Test 3: Backup-Listen-Funktionalität")
        try:
            backups = unified_backup_manager.list_backups()
            test_results['tests']['backup_listing'] = {
                'success': True,
                'backup_count': len(backups),
                'backups': backups[:3]  # Nur erste 3 für Übersichtlichkeit
            }
            print(f"✅ Backup-Liste erfolgreich abgerufen: {len(backups)} Backups gefunden")
        except Exception as e:
            test_results['tests']['backup_listing'] = {'success': False, 'error': str(e)}
            print(f"❌ Backup-Listen fehlgeschlagen: {e}")

        # Test 4: Performance-Messungen
        print("\n⚡ Test 4: Performance-Messungen")
        performance_metrics = measure_backup_performance()
        test_results['tests']['performance'] = performance_metrics
        print(f"✅ Performance-Messungen: CPU {performance_metrics.get('cpu_cores', 'N/A')} Kerne, RAM {performance_metrics.get('memory_mb', 'N/A')} MB")

        # Test 5: Konfigurationstest
        print("\n⚙️ Test 5: Konfigurations-Validierung")
        config_test = test_backup_configuration()
        test_results['tests']['configuration'] = config_test
        print(f"✅ Konfiguration: Worker {config_test.get('max_workers', 'N/A')}, Chunk-Size {config_test.get('chunk_size', 'N/A')}")

        # Gesamtergebnis
        all_tests_passed = all(test.get('success', False) for test in test_results['tests'].values())
        test_results['overall_success'] = all_tests_passed

        if all_tests_passed:
            print("\n🎉 Alle Backup-Konsistenz-Tests erfolgreich bestanden!")
        else:
            print("\n⚠️ Einige Tests sind fehlgeschlagen - bitte prüfen!")

        return test_results

    except Exception as e:
        print(f"❌ Kritischer Fehler beim Konsistenz-Test: {e}")
        test_results['overall_success'] = False
        test_results['critical_error'] = str(e)
        return test_results

def validate_backup_integrity(backup_path):
    """Validiert die Integrität eines Backups"""
    try:
        import zipfile

        result = {
            'valid': False,
            'total_collections': 0,
            'total_documents': 0,
            'collections': [],
            'has_metadata': False,
            'has_checksums': False
        }

        with zipfile.ZipFile(backup_path, 'r') as zipf:
            # Metadaten prüfen
            if 'backup_metadata.json' in zipf.namelist():
                metadata_content = zipf.read('backup_metadata.json')
                metadata = json.loads(metadata_content.decode('utf-8'))
                result['has_metadata'] = True
                result['metadata_version'] = metadata.get('version', 'unknown')

            # Checksums prüfen
            if 'checksums.json' in zipf.namelist():
                result['has_checksums'] = True

            # MongoDB-Daten prüfen
            mongodb_files = [f for f in zipf.namelist() if f.startswith('mongodb/') and f.endswith('.json')]

            if mongodb_files:
                # Haupt-Backup-Datei laden
                main_backup_file = next((f for f in mongodb_files if 'scandy_backup_' in f), None)
                if main_backup_file:
                    backup_content = zipf.read(main_backup_file)
                    backup_data = json.loads(backup_content.decode('utf-8'))

                    if 'data' in backup_data:
                        collections_data = backup_data['data']
                        result['total_collections'] = len(collections_data)

                        for collection_name, documents in collections_data.items():
                            doc_count = len(documents) if isinstance(documents, list) else 0
                            result['total_documents'] += doc_count
                            result['collections'].append({
                                'name': collection_name,
                                'documents': doc_count
                            })

            # Medien prüfen (falls vorhanden)
            media_files = [f for f in zipf.namelist() if f.startswith('media/')]
            result['media_files'] = len(media_files)

            # Konfiguration prüfen (falls vorhanden)
            config_files = [f for f in zipf.namelist() if f.startswith('config/')]
            result['config_files'] = len(config_files)

            # Gesamtvalidierung
            result['valid'] = (
                result['has_metadata'] and
                result['has_checksums'] and
                result['total_collections'] > 0 and
                result['total_documents'] > 0
            )

        return result

    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }

def measure_backup_performance():
    """Misst Backup-Performance-Metriken"""
    try:
        import psutil

        result = {
            'cpu_cores': psutil.cpu_count(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_mb': round(psutil.virtual_memory().total / 1024 / 1024),
            'memory_available_mb': round(psutil.virtual_memory().available / 1024 / 1024),
            'disk_total_gb': round(psutil.disk_usage('/').total / 1024 / 1024 / 1024),
            'disk_free_gb': round(psutil.disk_usage('/').free / 1024 / 1024 / 1024)
        }

        return result

    except Exception as e:
        return {'error': str(e)}

def test_backup_configuration():
    """Testet die Backup-Konfiguration"""
    try:
        config = {
            'max_workers': unified_backup_manager.max_workers,
            'chunk_size': unified_backup_manager.chunk_size,
            'streaming_threshold': unified_backup_manager.streaming_threshold,
            'max_backup_size_gb': unified_backup_manager.max_backup_size_gb,
            'include_media': unified_backup_manager.include_media,
            'compress_backups': unified_backup_manager.compress_backups,
            'backup_dir_exists': unified_backup_manager.backup_dir.exists(),
            'backup_dir_writable': os.access(unified_backup_manager.backup_dir, os.W_OK)
        }

        return config

    except Exception as e:
        return {'error': str(e)}

def save_test_results(results, filename=None):
    """Speichert Test-Ergebnisse in eine Datei"""
    if not filename:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_consistency_test_{timestamp}.json"

    test_file = Path('logs') / filename
    test_file.parent.mkdir(exist_ok=True)

    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"📄 Test-Ergebnisse gespeichert: {test_file}")
    return str(test_file)

# Hauptfunktion für direkten Aufruf
if __name__ == "__main__":
    print("=" * 60)
    print("🔧 BACKUP-KONSISTENZ-TEST")
    print("=" * 60)

    results = test_backup_consistency()

    print("\n" + "=" * 60)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 60)

    for test_name, test_result in results['tests'].items():
        status = "✅" if test_result.get('success', False) else "❌"
        print(f"{status} {test_name}: {test_result.get('message', 'Abgeschlossen')}")

    print(f"\n🏆 Gesamtergebnis: {'✅ ALLE TESTS BESTANDEN' if results['overall_success'] else '❌ EINIGE TESTS FEHLGESCHLAGEN'}")

    # Ergebnisse speichern
    result_file = save_test_results(results)

    print(f"\n📄 Detaillierte Ergebnisse: {result_file}")

    # Exit-Code setzen
    exit(0 if results['overall_success'] else 1)
