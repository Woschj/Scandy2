#!/usr/bin/env python3
"""
Repariert Rollenrechte-Einträge in der MongoDB-Settings-Collection.

Ziel:
- Für JEDES Department einen konsistenten Eintrag settings[key='role_permissions'] anlegen/aktualisieren
- Matrix auf sichere Defaults zurücksetzen, damit Benutzer wieder sehen/anlegen dürfen

Ausführung:
  python3 repair_role_permissions.py

Optional: Trockenlauf
  DRY_RUN=1 python3 repair_role_permissions.py
"""
import os
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    DRY_RUN = os.environ.get("DRY_RUN", "0") not in ("0", "false", "False", "")

    from app.models.mongodb_database import MongoDB
    from app.utils.permissions import normalize_permissions

    mdb = MongoDB()

    # Departments aus settings lesen (globaler Key, nicht gescoped)
    depts_setting = mdb.find_one('settings', {'key': 'departments'})
    departments = []
    if depts_setting and isinstance(depts_setting.get('value'), list):
        departments = [d for d in depts_setting['value'] if isinstance(d, str) and d.strip()]
    if not departments:
        departments = ['Standard']

    # Gewünschte Matrix gemäß Vorgabe:
    # - Admin: Vollzugriff inkl. Systemverwaltung (global)
    # - Mitarbeiter: Vollzugriff innerhalb der Abteilung, keine Settings
    # - Benutzer: Vollzugriff innerhalb der Abteilung, keine Settings
    # - Teilnehmer: Tickets (view/create) + Jobbörse (view)
    desired_matrix_raw = {
        "admin": {
            "tools": ["view", "create", "edit", "delete", "export"],
            "consumables": ["view", "create", "edit", "delete", "export"],
            "workers": ["view", "create", "edit", "delete"],
            "tickets": ["view", "create", "edit", "assign", "delete", "export"],
            "jobs": ["view", "create", "edit", "delete"],
            "settings": ["manage"],
        },
        "mitarbeiter": {
            "tools": ["view", "create", "edit", "delete", "export"],
            "consumables": ["view", "create", "edit", "delete", "export"],
            "workers": ["view", "create", "edit", "delete"],
            "tickets": ["view", "create", "edit", "assign", "delete", "export"],
            "jobs": ["view", "create", "edit", "delete"],
            # kein settings
        },
        "benutzer": {
            "tools": ["view", "create", "edit", "delete", "export"],
            "consumables": ["view", "create", "edit", "delete", "export"],
            "workers": ["view", "create", "edit", "delete"],
            "tickets": ["view", "create", "edit", "assign", "delete", "export"],
            "jobs": ["view", "create", "edit", "delete"],
            # kein settings
        },
        "teilnehmer": {
            "tickets": ["view", "create"],
            "jobs": ["view"],
        },
    }

    # Auf erlaubte Aktionen normalisieren (filtert unzulässige weg)
    desired_matrix = normalize_permissions(desired_matrix_raw)

    print("=" * 80)
    print("Scandy – Reparatur Rollenrechte (pro Department)")
    print("Departments:", ", ".join(departments))
    print("Dry-Run:", DRY_RUN)
    print("=" * 80)

    total_upserts = 0

    # Zuerst globalen Fallback (ohne department) setzen, damit immer eine valide Matrix vorhanden ist
    if not DRY_RUN:
        ok_global = mdb.update_one(
            'settings',
            {'key': 'role_permissions'},
            {'$set': {'key': 'role_permissions', 'value': desired_matrix}},
            upsert=True,
        )
        if ok_global:
            print("[OK  ] Globaler Fallback für role_permissions gesetzt")
        else:
            print("[Warn] Globaler Fallback konnte nicht gesetzt werden")
    for dept in departments:
        # Bestehenden Eintrag (falls vorhanden) nur informativ laden
        existing = mdb.find_one('settings', {'key': 'role_permissions', 'department': dept})
        if existing:
            print(f"[Info] Vorhanden in '{dept}': wird überschrieben (Reset auf Defaults)")
        else:
            print(f"[Neu ] Anlegen für '{dept}'")

        if not DRY_RUN:
            ok = mdb.update_one(
                'settings',
                {'key': 'role_permissions', 'department': dept},
                {'$set': {'key': 'role_permissions', 'value': desired_matrix, 'department': dept}},
                upsert=True,
            )
            if ok:
                total_upserts += 1
            else:
                print(f"[Warn] Update fehlgeschlagen für Department '{dept}'")

    print("-" * 80)
    print(f"Fertig. Aktualisierte/angelegte Department-Einträge: {total_upserts}")
    print("Hinweis: Danach Web-App neu laden und ggf. Abteilung wechseln.")


if __name__ == "__main__":
    main()


