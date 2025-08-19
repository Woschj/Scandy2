#!/usr/bin/env python3
"""
Setzt für alle vorhandenen Datensätze in den Collections tools, consumables und workers
das Feld "department" auf den gewünschten Namen (Standard: "Medien und Digitales").

Verwendung:
  - Standard-Department:
      python3 assign_department.py
  - Eigenes Department per Argument:
      python3 assign_department.py "IT"

Hinweis:
  - Das Skript ergänzt das Department in settings (key="departments"), falls es dort noch fehlt.
  - Es werden nur Dokumente geändert, die noch kein sinnvolles Feld "department" haben
    (nicht vorhanden, leerer String oder None).
"""

import sys
from pathlib import Path


def main():
    # Projektpfad zur Python-Path hinzufügen, damit "app" importiert werden kann
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Department-Name aus Argumenten lesen oder Standard verwenden
    target_department = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "Medien und Digitales"
    if not target_department:
        target_department = "Medien und Digitales"

    print("=" * 80)
    print("Scandy – Department-Zuweisung für Bestandsdaten")
    print("=" * 80)
    print(f"Ziel-Department: {target_department}")

    try:
        from app.models.mongodb_database import MongoDB
        mdb = MongoDB()

        # 1) Department in settings ergänzen
        print("\n[1/3] Stelle sicher, dass das Department in settings vorhanden ist …")
        depts_setting = mdb.find_one('settings', {'key': 'departments'})
        departments = []
        if depts_setting and isinstance(depts_setting.get('value'), list):
            departments = [d for d in depts_setting['value'] if isinstance(d, str) and d.strip()]
        if target_department not in departments:
            departments.append(target_department)
            mdb.update_one('settings', {'key': 'departments'}, {'$set': {'value': departments}}, upsert=True)
            print(f"  -> Department '{target_department}' zu settings hinzugefügt")
        else:
            print(f"  -> Department '{target_department}' bereits in settings vorhanden")

        # 2) Dokumente ohne Department ermitteln und setzen
        print("\n[2/3] Weise fehlende Departments zu …")
        missing_filter = {'$or': [
            {'department': {'$exists': False}},
            {'department': None},
            {'department': ''}
        ]}

        collections = ['tools', 'consumables', 'workers']
        total_modified = 0
        for coll in collections:
            try:
                count_missing = mdb.count_documents(coll, missing_filter)
                if count_missing > 0:
                    modified = mdb.update_many(coll, missing_filter, {'$set': {'department': target_department}})
                    total_modified += modified
                    print(f"  {coll}: {count_missing} Dokument(e) ohne Department -> {modified} gesetzt")
                else:
                    print(f"  {coll}: Keine Dokumente ohne Department gefunden")
            except Exception as ce:
                print(f"  {coll}: Fehler beim Aktualisieren: {ce}")

        # 3) Ergebnis
        print("\n[3/3] Zusammenfassung")
        print(f"  Insgesamt gesetzte Dokumente: {total_modified}")
        print("\nFertig. Bitte Scandy neu starten, falls noch nicht geschehen.")

    except Exception as e:
        print(f"Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


