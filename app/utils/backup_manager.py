import os
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from app.models.mongodb_database import mongodb

class BackupManager:
    """Vollständiger Backup-Manager für MongoDB"""
    
    def __init__(self):
        self.backup_dir = Path(__file__).parent.parent.parent / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
    
    def _fix_id_for_restore(self, doc):
        """
        Wandelt das _id-Feld in einen echten ObjectId um, wenn möglich.
        Wichtig für Backup-Wiederherstellung, da JSON-Export IDs als String speichert.
        Unterstützt auch andere Datentyp-Konvertierungen für alte Backups.
        """
        if not isinstance(doc, dict):
            return doc
            
        # _id Konvertierung
        if '_id' in doc:
            # Falls _id ein String ist und wie eine ObjectId aussieht
            if isinstance(doc['_id'], str) and len(doc['_id']) == 24:
                try:
                    doc['_id'] = ObjectId(doc['_id'])
                except Exception:
                    # Falls es keine gültige ObjectId ist, entferne das Feld
                    # MongoDB wird automatisch eine neue ObjectId generieren
                    del doc['_id']
            # Falls _id bereits eine ObjectId ist, belasse es
            elif isinstance(doc['_id'], ObjectId):
                pass
            # Falls _id ein anderer Typ ist, entferne es
            else:
                del doc['_id']
        
        # Datetime-Felder konvertieren (für alte Backups)
        datetime_fields = ['created_at', 'updated_at', 'modified_at', 'deleted_at', 'date', 'timestamp']
        for field in datetime_fields:
            if field in doc and isinstance(doc[field], str):
                try:
                    # Versuche verschiedene Datetime-Formate
                    for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S']:
                        try:
                            doc[field] = datetime.strptime(doc[field], fmt)
                            break
                        except ValueError:
                            continue
                except:
                    pass  # Belasse als String wenn Konvertierung fehlschlägt
        
        return doc
    
    def _deserialize_from_backup(self, obj):
        """
        Deserialisiert Objekte aus Backup mit Datentyp-Wiederherstellung
        Unterstützt sowohl neue (mit __type__) als auch alte Backup-Formate
        ERWEITERT für bessere Kompatibilität mit älteren Versionen
        """
        if isinstance(obj, dict):
            # Neues Format mit __type__ Markierungen
            if '__type__' in obj:
                if obj['__type__'] == 'datetime':
                    try:
                        return datetime.fromisoformat(obj['value'])
                    except ValueError:
                        return datetime.now()
                elif obj['__type__'] == 'ObjectId':
                    try:
                        return ObjectId(obj['value'])
                    except:
                        return obj['value']  # Fallback zu String
                else:
                    return obj['value']
            else:
                # Altes Format - konvertiere bekannte Felder
                result = {}
                for k, v in obj.items():
                    # _id Felder als ObjectId konvertieren
                    if k == '_id' and isinstance(v, str) and len(v) == 24:
                        try:
                            result[k] = ObjectId(v)
                        except:
                            result[k] = v  # Fallback zu String
                    # Datetime-Felder konvertieren - ERWEITERTE LISTE für ältere Versionen
                    elif k in ['created_at', 'updated_at', 'modified_at', 'deleted_at', 'date', 'timestamp', 
                              'lent_at', 'returned_at', 'due_date', 'resolved_at', 'used_at', 'start_date', 
                              'end_date', 'created', 'modified', 'last_updated', 'time', 'datetime',
                              'created_date', 'updated_date', 'modified_date', 'deleted_date',
                              'lent_date', 'returned_date', 'due_date', 'resolved_date', 'used_date'] and isinstance(v, str):
                        try:
                            # ERWEITERTE Liste von Datetime-Formaten für ältere Versionen
                            formats = [
                                '%Y-%m-%d %H:%M:%S.%f',  # 2025-06-27 14:13:12.387000
                                '%Y-%m-%d %H:%M:%S',     # 2025-06-27 14:13:12
                                '%Y-%m-%d',              # 2025-06-27
                                '%Y-%m-%dT%H:%M:%S.%f',  # 2025-06-27T14:13:12.387000
                                '%Y-%m-%dT%H:%M:%S',     # 2025-06-27T14:13:12
                                '%Y-%m-%dT%H:%M:%S.%fZ', # ISO mit Z
                                '%Y-%m-%dT%H:%M:%SZ',    # ISO mit Z
                                '%d.%m.%Y %H:%M:%S',     # 27.06.2025 14:13:12 (deutsches Format)
                                '%d.%m.%Y',              # 27.06.2025
                                '%d/%m/%Y %H:%M:%S',     # 27/06/2025 14:13:12
                                '%d/%m/%Y',              # 27/06/2025
                                '%m/%d/%Y %H:%M:%S',     # 06/27/2025 14:13:12
                                '%m/%d/%Y',              # 06/27/2025
                                '%Y-%m-%d %H:%M',        # 2025-06-27 14:13
                                '%d.%m.%Y %H:%M',        # 27.06.2025 14:13
                                '%Y%m%d_%H%M%S',        # 20250627_141312
                                '%Y%m%d',                # 20250627
                            ]
                            
                            for fmt in formats:
                                try:
                                    result[k] = datetime.strptime(v, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                # Fallback: Versuche ISO-Format
                                try:
                                    result[k] = datetime.fromisoformat(v.replace('Z', '+00:00'))
                                except ValueError:
                                    # Letzter Fallback: Versuche Unix-Timestamp
                                    try:
                                        timestamp = float(v)
                                        result[k] = datetime.fromtimestamp(timestamp)
                                    except (ValueError, TypeError):
                                        result[k] = v  # Fallback zu String
                        except:
                            result[k] = v
                    # Boolean-Felder konvertieren (für ältere Versionen)
                    elif k in ['deleted', 'active', 'enabled', 'disabled', 'is_active', 'is_deleted', 
                              'is_enabled', 'is_disabled', 'available', 'unavailable', 'in_use', 
                              'borrowed', 'returned', 'completed', 'pending', 'resolved', 'open'] and isinstance(v, str):
                        # Konvertiere String-Booleans zu echten Booleans
                        if v.lower() in ['true', '1', 'yes', 'ja', 'on', 'enabled', 'active']:
                            result[k] = True
                        elif v.lower() in ['false', '0', 'no', 'nein', 'off', 'disabled', 'inactive']:
                            result[k] = False
                        else:
                            result[k] = v  # Fallback zu String
                    # Numerische Felder konvertieren (für ältere Versionen)
                    elif k in ['quantity', 'min_quantity', 'max_quantity', 'amount', 'count', 'total', 
                              'price', 'cost', 'value', 'number', 'id', 'user_id', 'tool_id', 
                              'worker_id', 'consumable_id', 'ticket_id', 'job_id'] and isinstance(v, str):
                        try:
                            # Versuche zu int konvertieren
                            if '.' in v:
                                result[k] = float(v)
                            else:
                                result[k] = int(v)
                        except (ValueError, TypeError):
                            result[k] = v  # Fallback zu String
                    else:
                        result[k] = self._deserialize_from_backup(v)
                return result
        elif isinstance(obj, list):
            return [self._deserialize_from_backup(item) for item in obj]
        else:
            return obj

    def _detect_old_backup_format(self, backup_data):
        """
        Erkennt das Format eines alten Backups und gibt Informationen zurück
        """
        try:
            format_info = {
                'is_old_format': False,
                'version_estimate': 'unknown',
                'collections_found': [],
                'total_documents': 0,
                'has_metadata': False,
                'has_datatype_preservation': False,
                'format_type': 'unknown'
            }
            
            # Prüfe ob es das neue Format ist
            if isinstance(backup_data, dict) and 'metadata' in backup_data and 'data' in backup_data:
                format_info['has_metadata'] = True
                format_info['has_datatype_preservation'] = backup_data['metadata'].get('datatype_preservation', False)
                format_info['format_type'] = 'new'
                
                if format_info['has_datatype_preservation']:
                    format_info['version_estimate'] = '2.0+'
                else:
                    format_info['version_estimate'] = '1.0-1.9'
                
                data_section = backup_data['data']
            else:
                # Altes Format
                format_info['is_old_format'] = True
                format_info['format_type'] = 'old'
                data_section = backup_data
            
            # Analysiere Collections
            if isinstance(data_section, dict):
                format_info['collections_found'] = list(data_section.keys())
                format_info['total_documents'] = sum(len(docs) for docs in data_section.values() if isinstance(docs, list))
                
                # Schätze Version basierend auf vorhandenen Collections
                if 'jobs' in data_section:
                    format_info['version_estimate'] = '1.5+'
                elif 'tickets' in data_section:
                    format_info['version_estimate'] = '1.0+'
                else:
                    format_info['version_estimate'] = 'pre-1.0'
            
            return format_info
            
        except Exception as e:
            print(f"Fehler beim Erkennen des Backup-Formats: {e}")
            return {
                'is_old_format': True,
                'version_estimate': 'unknown',
                'collections_found': [],
                'total_documents': 0,
                'has_metadata': False,
                'has_datatype_preservation': False,
                'format_type': 'unknown'
            }

    def _validate_backup_data(self, backup_data):
        """
        Validiert Backup-Daten vor der Wiederherstellung
        ERWEITERT für bessere Kompatibilität mit älteren Versionen
        """
        if not isinstance(backup_data, dict):
            return False, "Backup-Daten sind kein gültiges Dictionary"
        
        # Prüfe ob es das neue Format ist
        if 'data' in backup_data:
            data_section = backup_data['data']
            # Einfache Format-Erkennung ohne rekursive Aufrufe
            has_metadata = True
            has_datatype_preservation = backup_data.get('metadata', {}).get('datatype_preservation', False)
            is_old_format = False
        else:
            # Altes Format
            data_section = backup_data
            has_metadata = False
            has_datatype_preservation = False
            is_old_format = True
        
        # Schätze Version basierend auf vorhandenen Collections
        if 'jobs' in data_section:
            version_estimate = '1.5+'
        elif 'tickets' in data_section:
            version_estimate = '1.0+'
        else:
            version_estimate = 'pre-1.0'
        
        # ERWEITERTE Validierung für verschiedene Backup-Versionen
        if is_old_format or version_estimate == 'pre-1.0':
            # Sehr alte Backups - minimale Anforderungen
            required_collections = ['tools', 'workers']
            optional_collections = ['consumables', 'settings', 'lendings', 'tickets', 'jobs']
        elif version_estimate == '1.0+':
            # Version 1.0+ Backups
            required_collections = ['tools', 'workers', 'consumables', 'settings']
            optional_collections = ['lendings', 'tickets', 'jobs']
        elif version_estimate == '1.5+':
            # Version 1.5+ Backups
            required_collections = ['tools', 'workers', 'consumables', 'settings', 'tickets']
            optional_collections = ['lendings', 'jobs']
        else:
            # Neue Backups (2.0+)
            required_collections = ['tools', 'workers', 'consumables', 'settings', 'tickets', 'jobs']
            optional_collections = ['lendings']
        
        # Prüfe erforderliche Collections
        missing_required = [coll for coll in required_collections if coll not in data_section]
        if missing_required:
            return False, f"Fehlende erforderliche Collections im Backup: {missing_required}"
        
        # Prüfe ob überhaupt Daten vorhanden sind
        total_docs = sum(len(docs) for docs in data_section.values() if isinstance(docs, list))
        if total_docs == 0:
            return False, "Backup enthält keine Dokumente"
        
        # Erstelle detaillierte Validierungsnachricht
        found_collections = [coll for coll in required_collections + optional_collections if coll in data_section]
        validation_message = f"Backup ist gültig ({version_estimate} Format)"
        validation_message += f" mit {total_docs} Dokumenten in {len(found_collections)} Collections"
        
        if is_old_format:
            validation_message += " (altes Format - Konvertierung wird empfohlen)"
        
        return True, validation_message
        
    def _serialize_for_backup(self, obj):
        """
        Serialisiert Python-Objekte für JSON-Export mit Datentyp-Erhaltung
        """
        if isinstance(obj, datetime):
            return {
                '__type__': 'datetime',
                'value': obj.isoformat()
            }
        elif isinstance(obj, ObjectId):
            return {
                '__type__': 'ObjectId',
                'value': str(obj)
            }
        elif isinstance(obj, dict):
            return {k: self._serialize_for_backup(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_backup(item) for item in obj]
        else:
            return obj

    def create_backup(self):
        """Erstellt ein Backup aller Collections mit Datentyp-Erhaltung"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"scandy_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            # Alle Collections sichern
            collections_to_backup = [
                'tools', 'workers', 'consumables', 'lendings', 'consumable_usages', 
                'settings', 'tickets', 'timesheets', 'auftrag_details', 
                'auftrag_material', 'email_config', 'email_settings', 'system_logs', 'jobs'
            ]  # 'users' ausgeschlossen
            backup_data = {}
            
            for collection in collections_to_backup:
                try:
                    documents = list(mongodb.find(collection, {}))
                    # Serialisiere Dokumente mit Datentyp-Erhaltung
                    serialized_docs = [self._serialize_for_backup(doc) for doc in documents]
                    backup_data[collection] = serialized_docs
                except Exception as e:
                    print(f"Fehler beim Sichern von {collection}: {e}")
                    backup_data[collection] = []
            
            # Backup-Datei mit Metadaten speichern
            backup_with_metadata = {
                'metadata': {
                    'version': '2.0',
                    'created_at': datetime.now().isoformat(),
                    'datatype_preservation': True,
                    'collections': list(backup_data.keys())
                },
                'data': backup_data
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_with_metadata, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"Backup erstellt: {backup_filename} mit {sum(len(docs) for docs in backup_data.values())} Dokumenten")
            print("Datentyp-Erhaltung aktiviert")
            
            # Alte Backups aufräumen
            self._cleanup_old_backups()
            
            return backup_filename
            
        except Exception as e:
            print(f"Fehler beim Erstellen des Backups: {e}")
            return None
    
    def restore_backup(self, file):
        """Stellt ein Backup aus einer hochgeladenen Datei wieder her"""
        temp_path = None
        try:
            # Prüfe ob die Datei leer ist
            file.seek(0, 2)  # Gehe zum Ende der Datei
            file_size = file.tell()
            file.seek(0)  # Zurück zum Anfang
            
            if file_size == 0:
                print("Fehler: Hochgeladene Datei ist leer")
                return False
            
            # Temporäre Datei speichern
            temp_path = self.backup_dir / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file.save(temp_path)
            
            # Prüfe ob die Datei erfolgreich gespeichert wurde
            if not temp_path.exists():
                print("Fehler: Temporäre Datei konnte nicht gespeichert werden")
                return False
            
            # Prüfe Dateigröße nochmal
            actual_file_size = temp_path.stat().st_size
            if actual_file_size == 0:
                print("Fehler: Gespeicherte Datei ist leer")
                temp_path.unlink()
                return False
            
            print(f"Temporäre Datei gespeichert: {temp_path}, Größe: {actual_file_size} bytes")
            
            # Backup wiederherstellen
            success = self._restore_from_file(temp_path)
            
            return success
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des Backups: {e}")
            return False
        finally:
            # Temporäre Datei löschen
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    print(f"Fehler beim Löschen der temporären Datei: {e}")
    
    def restore_backup_by_filename(self, filename):
        """Stellt ein Backup anhand des Dateinamens wieder her"""
        try:
            backup_path = self.backup_dir / filename
            if not backup_path.exists():
                print(f"Backup-Datei nicht gefunden: {filename}")
                return False
            
            return self._restore_from_file(backup_path)
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des Backups: {e}")
            return False
    
    def _restore_from_file(self, backup_path):
        """Stellt ein Backup aus einer Datei wieder her mit verbesserter Datentyp-Behandlung"""
        try:
            # Prüfe Dateigröße
            file_size = backup_path.stat().st_size
            if file_size == 0:
                print("Fehler: Backup-Datei ist leer")
                return False
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # ERWEITERTE Backup-Format-Erkennung (ohne rekursive Aufrufe)
            if 'data' in backup_data:
                # Neues Format mit Metadata
                has_metadata = True
                has_datatype_preservation = backup_data.get('metadata', {}).get('datatype_preservation', False)
                data_section = backup_data['data']
                format_type = 'new'
                print("Erkennung: Neues Backup-Format mit Datentyp-Informationen")
            else:
                # Altes Format
                has_metadata = False
                has_datatype_preservation = False
                data_section = backup_data
                format_type = 'old'
                print("Erkennung: Altes Backup-Format - Erweiterte Konvertierung erforderlich")
            
            # Schätze Version basierend auf vorhandenen Collections
            if 'jobs' in data_section:
                version_estimate = '1.5+'
            elif 'tickets' in data_section:
                version_estimate = '1.0+'
            else:
                version_estimate = 'pre-1.0'
            
            collections_found = list(data_section.keys())
            total_documents = sum(len(docs) for docs in data_section.values() if isinstance(docs, list))
            
            print(f"Backup-Format erkannt: {format_type} ({version_estimate})")
            print(f"Collections gefunden: {collections_found}")
            print(f"Gesamte Dokumente: {total_documents}")
            
            # Backup-Daten validieren mit erweiterter Unterstützung für alte Formate
            is_valid, validation_message = self._validate_backup_data({'data': data_section})
            if not is_valid:
                print(f"Backup-Validierung fehlgeschlagen: {validation_message}")
                return False
            
            print(f"Backup-Validierung erfolgreich: {validation_message}")
            
            # ERWEITERTE Wiederherstellung mit besserer Fehlerbehandlung
            restore_stats = {
                'total_collections': 0,
                'successful_collections': 0,
                'failed_collections': 0,
                'total_documents': 0,
                'conversion_errors': 0,
                'format_warnings': []
            }
            
            # Collections wiederherstellen
            for collection, documents in data_section.items():
                # Benutzer niemals aus Backups wiederherstellen
                if collection == 'users':
                    print("Überspringe 'users'-Collection beim Restore (Sicherheitsvorgabe)")
                    continue
                restore_stats['total_collections'] += 1
                
                try:
                    # Collection leeren
                    mongodb.db[collection].delete_many({})
                    
                    # Dokumente wiederherstellen mit erweiterter Datentyp-Wiederherstellung
                    if documents:
                        restored_documents = []
                        conversion_stats = {
                            'total': 0, 
                            'id_converted': 0, 
                            'datetime_converted': 0, 
                            'boolean_converted': 0,
                            'numeric_converted': 0,
                            'errors': 0
                        }
                        
                        for doc in documents:
                            try:
                                # ERWEITERTE Deserialisierung mit Datentyp-Wiederherstellung
                                restored_doc = self._deserialize_from_backup(doc)
                                # IDs korrigieren
                                fixed_doc = self._fix_id_for_restore(restored_doc)
                                
                                # Stelle sicher, dass _id korrekt ist
                                if '_id' in fixed_doc:
                                    if isinstance(fixed_doc['_id'], str) and len(fixed_doc['_id']) == 24:
                                        try:
                                            fixed_doc['_id'] = ObjectId(fixed_doc['_id'])
                                        except:
                                            # Falls keine gültige ObjectId, entferne das Feld
                                            del fixed_doc['_id']
                                    elif not isinstance(fixed_doc['_id'], ObjectId):
                                        # Falls kein ObjectId, entferne das Feld
                                        del fixed_doc['_id']
                                
                                restored_documents.append(fixed_doc)
                                conversion_stats['total'] += 1
                                
                                # ERWEITERTE Statistiken sammeln
                                if '_id' in fixed_doc and isinstance(fixed_doc['_id'], ObjectId):
                                    conversion_stats['id_converted'] += 1
                                
                                # Datetime-Konvertierungen zählen
                                datetime_fields = ['created_at', 'updated_at', 'modified_at', 'deleted_at', 'date', 'timestamp',
                                                 'lent_at', 'returned_at', 'due_date', 'resolved_at', 'used_at', 'start_date', 'end_date']
                                for field in datetime_fields:
                                    if field in fixed_doc and isinstance(fixed_doc[field], datetime):
                                        conversion_stats['datetime_converted'] += 1
                                        break
                                
                                # Boolean-Konvertierungen zählen
                                boolean_fields = ['deleted', 'active', 'enabled', 'disabled', 'is_active', 'is_deleted']
                                for field in boolean_fields:
                                    if field in fixed_doc and isinstance(fixed_doc[field], bool):
                                        conversion_stats['boolean_converted'] += 1
                                        break
                                
                                # Numerische Konvertierungen zählen
                                numeric_fields = ['quantity', 'min_quantity', 'max_quantity', 'amount', 'count', 'total']
                                for field in numeric_fields:
                                    if field in fixed_doc and isinstance(fixed_doc[field], (int, float)):
                                        conversion_stats['numeric_converted'] += 1
                                        break
                                        
                            except Exception as e:
                                print(f"Fehler bei Dokument-Konvertierung in {collection}: {e}")
                                conversion_stats['errors'] += 1
                                restore_stats['conversion_errors'] += 1
                                # Versuche das ursprüngliche Dokument zu verwenden
                                restored_documents.append(doc)
                        
                        # Dokumente in die Datenbank einfügen
                        mongodb.db[collection].insert_many(restored_documents)
                        restore_stats['successful_collections'] += 1
                        restore_stats['total_documents'] += len(restored_documents)
                        
                        print(f"✅ Collection {collection}: {len(restored_documents)} Dokumente wiederhergestellt")
                        print(f"  - Konvertierungen: {conversion_stats['id_converted']} IDs, {conversion_stats['datetime_converted']} Datetimes")
                        print(f"  - Zusätzlich: {conversion_stats['boolean_converted']} Booleans, {conversion_stats['numeric_converted']} Numerische")
                        if conversion_stats['errors'] > 0:
                            print(f"  - ⚠️  Fehler: {conversion_stats['errors']}")
                        
                except Exception as e:
                    print(f"❌ Fehler beim Wiederherstellen von {collection}: {e}")
                    restore_stats['failed_collections'] += 1
                    
                    # Bei Fehler: Versuche ohne ID-Korrektur (Fallback für sehr alte Backups)
                    try:
                        mongodb.db[collection].insert_many(documents)
                        print(f"🔄 Collection {collection}: {len(documents)} Dokumente ohne ID-Korrektur wiederhergestellt (Fallback)")
                        restore_stats['successful_collections'] += 1
                        restore_stats['total_documents'] += len(documents)
                        restore_stats['format_warnings'].append(f"{collection}: Fallback-Modus verwendet")
                    except Exception as e2:
                        print(f"💥 Kritischer Fehler bei {collection}: {e2}")
                        restore_stats['failed_collections'] += 1
            
            # Nach der Wiederherstellung: Kategorien-Inkonsistenz beheben
            self._fix_category_inconsistency()
            
            # Verbrauchsgüter-Inkonsistenzen beheben
            self._fix_consumable_inconsistencies()
            
            # Automatische Dashboard-Fixes nach Backup-Import
            try:
                from app.services.admin_debug_service import AdminDebugService
                fixes = AdminDebugService.fix_dashboard_comprehensive()
                print(f"Umfassende Dashboard-Reparatur nach Backup angewendet: {fixes}")
                
            except Exception as e:
                print(f"Fehler bei automatischen Dashboard-Fixes: {e}")
            
            # ERWEITERTE Wiederherstellungs-Zusammenfassung
            print(f"\n📊 Backup-Wiederherstellung abgeschlossen:")
            print(f"   - Format: {format_type} ({version_estimate})")
            print(f"   - Collections: {restore_stats['successful_collections']}/{restore_stats['total_collections']} erfolgreich")
            print(f"   - Dokumente: {restore_stats['total_documents']} wiederhergestellt")
            print(f"   - Konvertierungsfehler: {restore_stats['conversion_errors']}")
            
            if restore_stats['failed_collections'] > 0:
                print(f"   - ⚠️  Fehlgeschlagene Collections: {restore_stats['failed_collections']}")
            
            if restore_stats['format_warnings']:
                print(f"   - ⚠️  Format-Warnungen: {len(restore_stats['format_warnings'])}")
                for warning in restore_stats['format_warnings']:
                    print(f"     • {warning}")
            
            if format_type == 'old':
                print(f"   - 💡 Empfehlung: Konvertieren Sie das Backup in das neue Format für bessere Kompatibilität")
            
            return True
            
        except Exception as e:
            print(f"Fehler beim Wiederherstellen aus Datei: {e}")
            return False
    
    def _fix_category_inconsistency(self):
        """Behebt Inkonsistenzen zwischen Kategorien in den Settings und den tatsächlich verwendeten Kategorien"""
        try:
            print("Behebe Kategorien-Inkonsistenz...")
            
            # Sammle alle verwendeten Kategorien aus den Daten
            used_categories = set()
            
            # Aus Werkzeugen
            tools = list(mongodb.find('tools', {}))
            for tool in tools:
                if tool.get('category'):
                    used_categories.add(tool['category'])
            
            # Aus Verbrauchsgütern
            consumables = list(mongodb.find('consumables', {}))
            for consumable in consumables:
                if consumable.get('category'):
                    used_categories.add(consumable['category'])
            
            # Aus Mitarbeitern (Abteilungen)
            workers = list(mongodb.find('workers', {}))
            for worker in workers:
                if worker.get('department'):
                    used_categories.add(worker['department'])
            
            # Aktualisiere die Settings mit allen verwendeten Kategorien
            if used_categories:
                categories_list = list(used_categories)
                mongodb.update_one('settings', 
                                 {'key': 'categories'}, 
                                 {'$set': {'value': categories_list}}, 
                                 upsert=True)
                print(f"Kategorien aktualisiert: {categories_list}")
            
            # Sammle alle verwendeten Standorte
            used_locations = set()
            for tool in tools:
                if tool.get('location'):
                    used_locations.add(tool['location'])
            for consumable in consumables:
                if consumable.get('location'):
                    used_locations.add(consumable['location'])
            
            # Aktualisiere die Standorte-Settings
            if used_locations:
                locations_list = list(used_locations)
                mongodb.update_one('settings', 
                                 {'key': 'locations'}, 
                                 {'$set': {'value': locations_list}}, 
                                 upsert=True)
                print(f"Standorte aktualisiert: {locations_list}")
            
            # Sammle alle verwendeten Abteilungen
            used_departments = set()
            for worker in workers:
                if worker.get('department'):
                    used_departments.add(worker['department'])
            
            # Aktualisiere die Abteilungen-Settings
            if used_departments:
                departments_list = list(used_departments)
                mongodb.update_one('settings', 
                                 {'key': 'departments'}, 
                                 {'$set': {'value': departments_list}}, 
                                 upsert=True)
                print(f"Abteilungen aktualisiert: {departments_list}")
            
            print("Kategorien-Inkonsistenz behoben!")
            
        except Exception as e:
            print(f"Fehler beim Beheben der Kategorien-Inkonsistenz: {e}")

    def _fix_consumable_inconsistencies(self):
        """Behebt Inkonsistenzen bei Verbrauchsgütern nach Backup-Import"""
        try:
            print("Behebe Verbrauchsgüter-Inkonsistenzen...")
            
            # 1. Prüfe und korrigiere negative Bestände
            consumables = list(mongodb.find('consumables', {'deleted': {'$ne': True}}))
            fixed_negative = 0
            
            for consumable in consumables:
                quantity = consumable.get('quantity', 0)
                
                # Konvertiere zu int falls nötig
                if isinstance(quantity, str):
                    try:
                        quantity = int(quantity)
                    except (ValueError, TypeError):
                        quantity = 0
                
                # Korrigiere negative Bestände
                if quantity < 0:
                    mongodb.update_one('consumables', 
                                     {'_id': consumable['_id']}, 
                                     {'$set': {'quantity': 0}})
                    print(f"  ✅ {consumable.get('name', 'Unbekannt')}: Negativen Bestand korrigiert ({quantity} → 0)")
                    fixed_negative += 1
            
            # 2. Prüfe und korrigiere fehlende min_quantity Felder
            fixed_min_quantity = 0
            for consumable in consumables:
                if 'min_quantity' not in consumable:
                    mongodb.update_one('consumables', 
                                     {'_id': consumable['_id']}, 
                                     {'$set': {'min_quantity': 5}})  # Standard-Wert
                    print(f"  ✅ {consumable.get('name', 'Unbekannt')}: min_quantity hinzugefügt (5)")
                    fixed_min_quantity += 1
            
            # 3. Prüfe und korrigiere Datetime-Felder
            fixed_datetime = 0
            for consumable in consumables:
                updated = False
                update_data = {}
                
                # created_at korrigieren
                created_at = consumable.get('created_at')
                if isinstance(created_at, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        update_data['created_at'] = created_at_dt
                        updated = True
                    except:
                        pass
                
                # updated_at korrigieren
                updated_at = consumable.get('updated_at')
                if isinstance(updated_at, str):
                    try:
                        updated_at_dt = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        update_data['updated_at'] = updated_at_dt
                        updated = True
                    except:
                        pass
                
                if updated:
                    mongodb.update_one('consumables', 
                                     {'_id': consumable['_id']}, 
                                     {'$set': update_data})
                    fixed_datetime += 1
            
            # 4. Prüfe und korrigiere consumable_usages Inkonsistenzen
            usages = list(mongodb.find('consumable_usages', {}))
            fixed_usages = 0
            
            for usage in usages:
                updated = False
                update_data = {}
                
                # used_at korrigieren
                used_at = usage.get('used_at')
                if isinstance(used_at, str):
                    try:
                        used_at_dt = datetime.fromisoformat(used_at.replace('Z', '+00:00'))
                        update_data['used_at'] = used_at_dt
                        updated = True
                    except:
                        pass
                
                # created_at korrigieren
                created_at = usage.get('created_at')
                if isinstance(created_at, str):
                    try:
                        created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        update_data['created_at'] = created_at_dt
                        updated = True
                    except:
                        pass
                
                if updated:
                    mongodb.update_one('consumable_usages', 
                                     {'_id': usage['_id']}, 
                                     {'$set': update_data})
                    fixed_usages += 1
            
            print(f"Verbrauchsgüter-Inkonsistenzen behoben:")
            print(f"  - Negative Bestände korrigiert: {fixed_negative}")
            print(f"  - min_quantity Felder hinzugefügt: {fixed_min_quantity}")
            print(f"  - Datetime-Felder korrigiert: {fixed_datetime}")
            print(f"  - Verbrauchseinträge korrigiert: {fixed_usages}")
            
        except Exception as e:
            print(f"Fehler beim Beheben der Verbrauchsgüter-Inkonsistenzen: {e}")
    
    def get_backup_path(self, filename):
        """Gibt den Pfad zu einer Backup-Datei zurück"""
        return self.backup_dir / filename
    
    def delete_backup(self, filename):
        """Löscht eine Backup-Datei"""
        try:
            backup_path = self.backup_dir / filename
            if backup_path.exists():
                backup_path.unlink()
                return True
            return False
        except Exception as e:
            print(f"Fehler beim Löschen des Backups: {e}")
            return False
    
    def test_backup(self, filename):
        """
        Testet ein Backup ohne es wiederherzustellen.
        Gibt Informationen über das Backup zurück.
        """
        try:
            backup_path = self.backup_dir / filename
            if not backup_path.exists():
                return False, "Backup-Datei nicht gefunden"
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Backup validieren
            is_valid, validation_message = self._validate_backup_data(backup_data)
            
            if not is_valid:
                return False, validation_message
            
            # Detaillierte Informationen sammeln
            collection_info = {}
            for collection, documents in backup_data.items():
                collection_info[collection] = {
                    'count': len(documents),
                    'sample_ids': [str(doc.get('_id', 'N/A'))[:10] + '...' for doc in documents[:3]]
                }
            
            return True, {
                'validation_message': validation_message,
                'collections': collection_info,
                'file_size': backup_path.stat().st_size,
                'file_modified': datetime.fromtimestamp(backup_path.stat().st_mtime)
            }
            
        except Exception as e:
            return False, f"Fehler beim Testen des Backups: {str(e)}"
    
    def test_old_backup_format(self, backup_filename):
        """
        Testet ein altes Backup-Format ohne Wiederherstellung
        Gibt detaillierte Informationen über Kompatibilität und Probleme zurück
        """
        try:
            backup_path = self.backup_dir / backup_filename
            if not backup_path.exists():
                return False, "Backup-Datei nicht gefunden"
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # ERWEITERTE Format-Analyse
            format_info = self._detect_old_backup_format(backup_data)
            
            # Backup validieren
            is_valid, validation_message = self._validate_backup_data(backup_data)
            
            # Detaillierte Analyse der Collections
            collection_analysis = {}
            if format_info['has_metadata']:
                data_section = backup_data['data']
            else:
                data_section = backup_data
            
            for collection_name, documents in data_section.items():
                if isinstance(documents, list):
                    analysis = {
                        'count': len(documents),
                        'sample_documents': [],
                        'field_types': {},
                        'potential_issues': []
                    }
                    
                    # Analysiere die ersten 3 Dokumente als Beispiel
                    for i, doc in enumerate(documents[:3]):
                        if isinstance(doc, dict):
                            sample_doc = {}
                            for field, value in doc.items():
                                sample_doc[field] = {
                                    'type': type(value).__name__,
                                    'value': str(value)[:50] + '...' if len(str(value)) > 50 else str(value)
                                }
                                
                                # Prüfe auf potenzielle Probleme
                                if field == '_id' and isinstance(value, str) and len(value) != 24:
                                    analysis['potential_issues'].append(f"Ungültige ObjectId in Dokument {i+1}")
                                elif field in ['created_at', 'updated_at', 'date'] and isinstance(value, str):
                                    try:
                                        datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                                    except ValueError:
                                        analysis['potential_issues'].append(f"Ungültiges Datetime-Format in {field} (Dokument {i+1})")
                            
                            analysis['sample_documents'].append(sample_doc)
                    
                    collection_analysis[collection_name] = analysis
            
            # Erstelle detaillierten Bericht
            report = {
                'filename': backup_filename,
                'file_size': backup_path.stat().st_size,
                'format_info': format_info,
                'is_valid': is_valid,
                'validation_message': validation_message,
                'collection_analysis': collection_analysis,
                'compatibility_score': 0,
                'recommendations': []
            }
            
            # Berechne Kompatibilitäts-Score
            compatibility_score = 100
            
            if format_info['is_old_format']:
                compatibility_score -= 20
                report['recommendations'].append("Backup ist im alten Format - Konvertierung empfohlen")
            
            if not is_valid:
                compatibility_score -= 30
                report['recommendations'].append("Backup-Validierung fehlgeschlagen")
            
            # Prüfe auf potenzielle Probleme
            total_issues = sum(len(analysis['potential_issues']) for analysis in collection_analysis.values())
            if total_issues > 0:
                compatibility_score -= min(total_issues * 5, 30)
                report['recommendations'].append(f"{total_issues} potenzielle Datentyp-Probleme gefunden")
            
            # Prüfe auf fehlende wichtige Collections
            important_collections = ['tools', 'workers', 'consumables']
            missing_important = [coll for coll in important_collections if coll not in collection_analysis]
            if missing_important:
                compatibility_score -= 15
                report['recommendations'].append(f"Fehlende wichtige Collections: {missing_important}")
            
            report['compatibility_score'] = max(compatibility_score, 0)
            
            # Füge Empfehlungen basierend auf Score hinzu
            if report['compatibility_score'] >= 80:
                report['recommendations'].append("Backup sollte problemlos wiederhergestellt werden können")
            elif report['compatibility_score'] >= 60:
                report['recommendations'].append("Backup kann wiederhergestellt werden, aber mit Einschränkungen")
            elif report['compatibility_score'] >= 40:
                report['recommendations'].append("Backup kann versucht werden wiederherzustellen, aber mit erheblichen Problemen")
            else:
                report['recommendations'].append("Backup ist wahrscheinlich nicht kompatibel - Konvertierung erforderlich")
            
            return True, report
            
        except Exception as e:
            return False, f"Fehler beim Testen des Backup-Formats: {str(e)}"

    def analyze_backup_compatibility(self, backup_filename):
        """
        Analysiert die Kompatibilität eines Backups mit der aktuellen Version
        """
        try:
            success, result = self.test_old_backup_format(backup_filename)
            if not success:
                return False, result
            
            report = result
            
            print(f"\n🔍 Backup-Kompatibilitätsanalyse: {backup_filename}")
            print(f"   - Format: {report['format_info']['format_type']} ({report['format_info']['version_estimate']})")
            print(f"   - Größe: {report['file_size'] / 1024:.1f} KB")
            print(f"   - Gültigkeit: {'✅' if report['is_valid'] else '❌'}")
            print(f"   - Kompatibilitäts-Score: {report['compatibility_score']}/100")
            
            print(f"\n📊 Collections-Analyse:")
            for collection, analysis in report['collection_analysis'].items():
                print(f"   - {collection}: {analysis['count']} Dokumente")
                if analysis['potential_issues']:
                    print(f"     ⚠️  Probleme: {len(analysis['potential_issues'])}")
            
            print(f"\n💡 Empfehlungen:")
            for recommendation in report['recommendations']:
                print(f"   - {recommendation}")
            
            return True, report
            
        except Exception as e:
            return False, f"Fehler bei der Kompatibilitätsanalyse: {str(e)}"
    
    def _cleanup_old_backups(self, keep_days=7):
        """Löscht Backups älter als 'keep_days' Tage"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            # Finde alle Backup-Dateien (JSON und Native)
            json_backups = list(self.backup_dir.glob('scandy_backup_*.json'))
            native_backups = list(self.backup_dir.glob('scandy_native_backup_*'))
            
            # Alle Backups zusammen
            all_backups = native_backups + json_backups
            
            deleted_count = 0
            total_size_freed = 0
            
            for backup in all_backups:
                try:
                    # Prüfe Erstellungsdatum
                    backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
                    
                    if backup_time < cutoff_date:
                        # Backup ist zu alt
                        if backup.is_dir():
                            # Natives Backup löschen
                            import shutil
                            size = self._get_dir_size(backup)
                            shutil.rmtree(backup)
                            deleted_count += 1
                            total_size_freed += size
                            print(f"Altes BSON-Backup gelöscht: {backup.name} (vom {backup_time.strftime('%Y-%m-%d %H:%M')})")
                        else:
                            # JSON-Backup löschen
                            size = backup.stat().st_size
                            backup.unlink()
                            deleted_count += 1
                            total_size_freed += size
                            print(f"Altes JSON-Backup gelöscht: {backup.name} (vom {backup_time.strftime('%Y-%m-%d %H:%M')})")
                            
                except Exception as e:
                    print(f"Fehler beim Löschen von {backup.name}: {e}")
            
            if deleted_count > 0:
                total_size_mb = total_size_freed / (1024 * 1024)
                print(f"✅ Backup-Bereinigung abgeschlossen:")
                print(f"   Gelöschte Backups: {deleted_count}")
                print(f"   Freigegebener Speicherplatz: {total_size_mb:.1f} MB")
                print(f"   Behaltene Backups: {len(all_backups) - deleted_count}")
            else:
                print(f"✅ Keine alten Backups gefunden (alle Backups sind neuer als {keep_days} Tage)")
                    
        except Exception as e:
            print(f"Fehler beim Aufräumen alter Backups: {e}")

    def create_native_backup(self):
        """
        Erstellt ein natives MongoDB-Backup mit mongodump
        Behält alle Datentypen perfekt bei
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dirname = f"scandy_native_backup_{timestamp}"
            backup_path = self.backup_dir / backup_dirname
            
            # Erstelle Backup-Verzeichnis
            backup_path.mkdir(exist_ok=True)
            
            # MongoDB-Verbindungsdaten aus der Konfiguration holen
            from app import create_app
            app = create_app()
            
            # Hole MongoDB-Verbindungsdaten aus der App-Konfiguration
            mongo_uri = app.config.get('MONGODB_URI')
            if not mongo_uri:
                # Fallback auf Standard-URI
                mongo_uri = 'mongodb://localhost:27017/scandy'
            
            # Extrahiere Datenbankname aus URI
            if '/' in mongo_uri:
                db_name = mongo_uri.split('/')[-1]
            else:
                db_name = 'scandy'
            
            # mongodump Befehl ausführen
            cmd = [
                '/usr/bin/mongodump',
                '--uri', mongo_uri,
                '--out', str(backup_path),
                '--gzip'  # Komprimierung für kleinere Dateien
            ]
            
            print(f"Erstelle natives MongoDB-Backup...")
            print(f"URI: {mongo_uri}")
            print(f"Datenbank: {db_name}")
            print(f"Backup-Pfad: {backup_path}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Natives Backup erstellt: {backup_dirname}")
                backup_size = self._get_dir_size_formatted(backup_path)
                print(f"Backup-Größe: {backup_size}")
                
                # Alte Backups aufräumen
                self._cleanup_old_backups()
                
                return backup_dirname
            else:
                print(f"❌ Fehler beim Erstellen des nativen Backups:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Fehler beim Erstellen des nativen Backups: {e}")
            return None
    
    def restore_native_backup(self, backup_filename):
        """
        Stellt ein natives MongoDB-Backup mit mongorestore wieder her
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                print(f"Backup nicht gefunden: {backup_path}")
                return False
            
            # MongoDB-Verbindungsdaten aus der Konfiguration holen
            from app import create_app
            app = create_app()
            mongo_uri = app.config.get('MONGODB_URI')
            if not mongo_uri:
                # Fallback auf Standard-URI
                mongo_uri = 'mongodb://localhost:27017/scandy'
            
            # Extrahiere Datenbankname aus URI
            if '/' in mongo_uri:
                db_name = mongo_uri.split('/')[-1]
            else:
                db_name = 'scandy'
            
            # Finde die BSON-Dateien im Backup
            bson_dir = backup_path / db_name
            if not bson_dir.exists():
                print(f"BSON-Dateien nicht gefunden in: {bson_dir}")
                return False
            
            print(f"Stelle natives Backup wieder her: {backup_filename}")
            print(f"URI: {mongo_uri}")
            print(f"Datenbank: {db_name}")
            
            # mongorestore Befehl ausführen
            cmd = [
                '/usr/bin/mongorestore',
                '--uri', mongo_uri,
                '--gzip',  # Komprimierung
                '--drop',  # Bestehende Collections löschen
                str(bson_dir)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print(f"✅ Natives Backup erfolgreich wiederhergestellt")
                return True
            else:
                print(f"❌ Fehler beim Wiederherstellen des nativen Backups:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des nativen Backups: {e}")
            return False

    def _python_restore_mongodb(self, mongo_uri: str, bson_dir):
        """Fallback: Stellt Collections aus BSON/BSON.GZ per PyMongo wieder her."""
        try:
            import gzip
            from pymongo import MongoClient
            from bson import decode_file_iter
            from pathlib import Path

            bson_dir = Path(bson_dir)
            client = MongoClient(mongo_uri)
            db_name = client.get_default_database().name if client.get_default_database() else 'scandy'
            db = client.get_database(db_name)

            files = []
            for p in bson_dir.iterdir():
                name = p.name
                if name.endswith('.metadata.json'):
                    continue
                if name.endswith('.bson') or name.endswith('.bson.gz'):
                    files.append(p)

            if not files:
                print(f"❌ Keine BSON-Dateien in {bson_dir} gefunden")
                return False

            for fpath in sorted(files):
                cname = fpath.name
                if cname.endswith('.bson.gz'):
                    coll = cname[:-8]
                elif cname.endswith('.bson'):
                    coll = cname[:-5]
                else:
                    continue
                if coll == 'users':
                    print(f"↷ Überspringe Collection 'users'")
                    continue
                print(f"→ Stelle Collection: {coll}")
                try:
                    db[coll].drop()
                except Exception:
                    pass
                opener = gzip.open if fpath.suffix == '.gz' or fpath.name.endswith('.gz') else open
                inserted = 0
                batch = []
                batch_size = 1000
                with opener(fpath, 'rb') as fh:
                    for doc in decode_file_iter(fh):
                        batch.append(doc)
                        if len(batch) >= batch_size:
                            db[coll].insert_many(batch, ordered=False)
                            inserted += len(batch)
                            batch.clear()
                    if batch:
                        db[coll].insert_many(batch, ordered=False)
                        inserted += len(batch)
                print(f"  ✓ {inserted} Dokumente in {coll} eingefügt")
            print("✅ MongoDB per Python-Fallback wiederhergestellt")
            return True
        except Exception as e:
            print(f"❌ Python-Fallback fehlgeschlagen: {e}")
            return False

    def restore_native_backup_from_upload(self, uploaded_file):
        """
        Stellt ein natives MongoDB-Backup aus einer hochgeladenen ZIP-Datei wieder her
        """
        try:
            import tempfile
            import zipfile
            import shutil
            
            # MongoDB-Verbindungsdaten aus der Konfiguration holen
            from app import create_app
            app = create_app()
            mongo_uri = app.config.get('MONGODB_URI')
            if not mongo_uri:
                # Fallback auf Standard-URI
                mongo_uri = 'mongodb://localhost:27017/scandy'
            
            # Extrahiere Datenbankname aus URI
            if '/' in mongo_uri:
                db_name = mongo_uri.split('/')[-1]
            else:
                db_name = 'scandy'
            
            # Erstelle temporäres Verzeichnis für das Backup
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Speichere die hochgeladene Datei temporär
                uploaded_file.save(temp_path / uploaded_file.filename)
                zip_path = temp_path / uploaded_file.filename
                
                # Entpacke die ZIP-Datei
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Finde die BSON-Dateien
                bson_dir = temp_path / db_name
                if not bson_dir.exists():
                    print(f"BSON-Dateien nicht gefunden in: {bson_dir}")
                    return False
                
                print(f"Stelle natives Backup aus Upload wieder her: {uploaded_file.filename}")
                print(f"URI: {mongo_uri}")
                print(f"Datenbank: {db_name}")
                
                # mongorestore Befehl ausführen – Binärdatei robust ermitteln
                mongorestore_bin = os.environ.get('MONGORESTORE_BIN')
                def _is_exec(p: str) -> bool:
                    try:
                        return p and os.path.isfile(p) and os.access(p, os.X_OK)
                    except Exception:
                        return False
                if not _is_exec(mongorestore_bin or ''):
                    try:
                        from shutil import which
                        w = which('mongorestore')
                        if w and _is_exec(w):
                            mongorestore_bin = w
                    except Exception:
                        mongorestore_bin = None
                if not _is_exec(mongorestore_bin or ''):
                    # Gängige Pfade testen
                    common_paths = [
                        '/usr/bin/mongorestore',
                        '/usr/local/bin/mongorestore',
                        '/snap/bin/mongorestore',
                        '/opt/homebrew/bin/mongorestore',
                        '/opt/local/bin/mongorestore'
                    ]
                    mongorestore_bin = next((p for p in common_paths if _is_exec(p)), None)
                if _is_exec(mongorestore_bin or ''):
                    cmd = [
                        mongorestore_bin,
                        '--uri', mongo_uri,
                        '--gzip',  # Komprimierung
                        '--drop',  # Bestehende Collections löschen
                        str(bson_dir)
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        print(f"✅ Natives Backup aus Upload erfolgreich wiederhergestellt")
                        return True
                    else:
                        print(f"❌ Fehler beim Wiederherstellen des nativen Backups aus Upload:")
                        print(f"STDOUT: {result.stdout}")
                        print(f"STDERR: {result.stderr}")
                        # Fallback auf Python-Restore
                        return self._python_restore_mongodb(mongo_uri, bson_dir)
                else:
                    print("⚠️ mongorestore nicht gefunden – versuche Python-Fallback")
                    return self._python_restore_mongodb(mongo_uri, bson_dir)
                    
        except Exception as e:
            print(f"Fehler beim Wiederherstellen des nativen Backups aus Upload: {e}")
            return False
    
    def _get_dir_size(self, path):
        """Berechnet die Größe eines Verzeichnisses in Bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception:
            pass
        return total_size
    
    def _get_dir_size_formatted(self, path):
        """Berechnet die Größe eines Verzeichnisses und formatiert sie"""
        total_size = self._get_dir_size(path)
        return self._format_size(total_size)
    
    def _format_size(self, size_bytes):
        """Formatiert Bytes in lesbare Größe"""
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def list_native_backups(self):
        """Listet alle nativen MongoDB-Backups auf"""
        try:
            backups = []
            
            for item in self.backup_dir.iterdir():
                if item.is_dir() and item.name.startswith('scandy_native_backup_'):
                    stat = item.stat()
                    size_bytes = self._get_dir_size(item)
                    size_formatted = self._get_dir_size_formatted(item)
                    backups.append({
                        'name': item.name,
                        'type': 'native',
                        'size': size_bytes,  # Rohe Größe in Bytes für Frontend
                        'size_formatted': size_formatted,  # Formatierte Größe für Anzeige
                        'size_mb': round(size_bytes / (1024 * 1024), 2),  # Größe in MB
                        'created': stat.st_mtime,
                        'modified': datetime.fromtimestamp(stat.st_mtime),
                        'modified_str': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M:%S')
                    })
            
            # Sortiere nach Änderungsdatum (neueste zuerst)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            return backups
            
        except Exception as e:
            print(f"Fehler beim Auflisten der nativen Backups: {e}")
            return []
    
    def create_hybrid_backup(self):
        """
        Erstellt ein hybrides Backup: Native MongoDB + JSON für Kompatibilität
        """
        try:
            # Erstelle natives Backup
            native_backup = self.create_native_backup()
            if not native_backup:
                return None
            
            # Erstelle zusätzlich JSON-Backup für Kompatibilität
            json_backup = self.create_backup()
            
            print(f"✅ Hybrides Backup erstellt:")
            print(f"  - Native: {native_backup}")
            print(f"  - JSON: {json_backup}")
            
            return {
                'native': native_backup,
                'json': json_backup
            }
            
        except Exception as e:
            print(f"Fehler beim Erstellen des hybriden Backups: {e}")
            return None

    def convert_old_backup(self, old_backup_filename):
        """
        Konvertiert ein altes Backup in das neue Format mit Datentyp-Erhaltung
        """
        try:
            old_backup_path = self.backup_dir / old_backup_filename
            
            if not old_backup_path.exists():
                print(f"Altes Backup nicht gefunden: {old_backup_path}")
                return None
            
            print(f"Konvertiere altes Backup: {old_backup_filename}")
            
            # Lade altes Backup
            with open(old_backup_path, 'r', encoding='utf-8') as f:
                old_backup_data = json.load(f)
            
            # Prüfe Backup-Format
            if 'metadata' in old_backup_data and old_backup_data['metadata'].get('datatype_preservation'):
                print("Backup ist bereits im neuen Format")
                return old_backup_filename
            
            # Erstelle neues Backup-Format
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_backup_filename = f"converted_backup_{timestamp}.json"
            new_backup_path = self.backup_dir / new_backup_filename
            
            # Konvertiere Daten mit Datentyp-Erhaltung
            converted_data = {
                'metadata': {
                    'version': '2.0',
                    'created_at': datetime.now().isoformat(),
                    'datatype_preservation': True,
                    'original_backup': old_backup_filename,
                    'converted_at': datetime.now().isoformat(),
                    'collections': list(old_backup_data.keys()) if isinstance(old_backup_data, dict) else []
                },
                'data': {}
            }
            
            # Konvertiere jede Collection
            total_documents = 0
            for collection_name, documents in old_backup_data.items():
                if isinstance(documents, list):
                    converted_docs = []
                    for doc in documents:
                        # Konvertiere Dokument mit Datentyp-Erhaltung
                        converted_doc = self._fix_id_for_restore(doc)
                        converted_docs.append(converted_doc)
                    
                    converted_data['data'][collection_name] = converted_docs
                    total_documents += len(converted_docs)
                    print(f"  ✅ Collection '{collection_name}': {len(converted_docs)} Dokumente konvertiert")
            
            # Speichere konvertiertes Backup
            with open(new_backup_path, 'w', encoding='utf-8') as f:
                json.dump(converted_data, f, ensure_ascii=False, indent=2)
            
            backup_size = new_backup_path.stat().st_size
            backup_size_kb = backup_size / 1024
            
            print(f"✅ Backup erfolgreich konvertiert: {new_backup_filename}")
            print(f"📊 Konvertierungs-Statistiken:")
            print(f"   - Collections: {len(converted_data['data'])}")
            print(f"   - Dokumente: {total_documents}")
            print(f"   - Größe: {backup_size_kb:.1f} KB")
            
            return new_backup_filename
                
        except Exception as e:
            print(f"Fehler beim Konvertieren des Backups: {e}")
            return None

    def list_old_backups(self):
        """
        Listet alle Backups auf, die noch im alten Format sind
        """
        try:
            old_backups = []
            
            for backup_file in self.backup_dir.glob('*.json'):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                    
                    # Prüfe ob Backup im alten Format ist
                    if 'metadata' not in backup_data or not backup_data['metadata'].get('datatype_preservation'):
                        old_backups.append({
                            'filename': backup_file.name,
                            'size': backup_file.stat().st_size,
                            'created': backup_file.stat().st_mtime,
                            'collections': list(backup_data.keys()) if isinstance(backup_data, dict) else []
                        })
                        
                except Exception as e:
                    print(f"Fehler beim Lesen von {backup_file.name}: {e}")
            
            return old_backups
            
        except Exception as e:
            print(f"Fehler beim Auflisten alter Backups: {e}")
            return []

    def convert_all_old_backups(self):
        """
        Konvertiert alle alten Backups automatisch
        """
        try:
            old_backups = self.list_old_backups()
            
            if not old_backups:
                print("Keine alten Backups gefunden")
                return []
            
            print(f"Gefunden: {len(old_backups)} alte Backups")
            converted_backups = []
            
            for old_backup in old_backups:
                print(f"\nKonvertiere: {old_backup['filename']}")
                converted_filename = self.convert_old_backup(old_backup['filename'])
                
                if converted_filename:
                    converted_backups.append({
                        'original': old_backup['filename'],
                        'converted': converted_filename
                    })
                    print(f"✅ Konvertiert: {old_backup['filename']} → {converted_filename}")
                else:
                    print(f"❌ Fehler bei: {old_backup['filename']}")
            
            print(f"\n📊 Konvertierung abgeschlossen:")
            print(f"   - Erfolgreich konvertiert: {len(converted_backups)}")
            print(f"   - Fehler: {len(old_backups) - len(converted_backups)}")
            
            return converted_backups
            
        except Exception as e:
            print(f"Fehler bei der Massenkonvertierung: {e}")
            return []

# Globale Instanz
backup_manager = BackupManager() 