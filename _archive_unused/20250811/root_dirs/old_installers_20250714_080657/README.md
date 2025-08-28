# Archiv: Alte Installationsskripte

Diese Dateien wurden durch das neue `install_unified.sh` Skript ersetzt.

## Migration

### Alte Skripte → Neue Verwendung

| Alt | Neu |
|-----|-----|
| `./install.sh` | `./install_unified.sh` |
| `./install_production.sh` | `./install_unified.sh -f` |
| `./setup_instance.sh` | `./install_unified.sh -n [NAME]` |
| `./start_all.sh` | `./manage.sh start` |
| `./stop_all.sh` | `./manage.sh stop` |
| `./start_standard.sh` | `./manage.sh start` |
| `./stop_standard.sh` | `./manage.sh stop` |

## Features des neuen Skripts

- ✅ Variable Ports für App und Datenbank
- ✅ Automatische Port-Berechnung
- ✅ Mehrere Instances parallel
- ✅ Sichere Passwort-Generierung
- ✅ Update-Modus ohne Datenverlust
- ✅ Port-Konflikt-Prüfung
- ✅ Einheitliches Management

## Wiederherstellung

Falls Sie die alten Skripte benötigen:

```bash
# Alle Dateien wiederherstellen
cp -r old_installers_*/ .

# Oder einzelne Dateien
cp old_installers_*/install.sh .
cp old_installers_*/start_all.sh .
```

## Dokumentation

Siehe `README_UNIFIED_INSTALLER.md` für die vollständige Dokumentation des neuen Installers.
