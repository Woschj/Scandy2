# Scandy Unified Installer

## Übersicht

Das `install_unified.sh` Skript vereinheitlicht alle bisherigen Installationsskripte und ermöglicht die flexible Konfiguration von Ports und Instance-Namen.

## Features

- ✅ **Variable Ports** für Web-App, MongoDB und Mongo Express
- ✅ **Automatische Port-Berechnung** basierend auf Instance-Namen
- ✅ **Mehrere Instances** können parallel laufen
- ✅ **Sichere Passwort-Generierung** für jede Installation
- ✅ **Update-Modus** für App-Updates ohne Datenverlust
- ✅ **Port-Konflikt-Prüfung** vor Installation
- ✅ **Management-Skript** für einfache Verwaltung
- ✅ **Detaillierte Logging** und Fehlerbehandlung

## Verwendung

### Standard-Installation
```bash
./install_unified.sh
```
- Web-App: http://localhost:5000
- MongoDB: localhost:27017
- Mongo Express: http://localhost:8081

### Custom Ports
```bash
./install_unified.sh -p 8080 -m 27018 -e 8082
```
- Web-App: http://localhost:8080
- MongoDB: localhost:27018
- Mongo Express: http://localhost:8082

### Instance mit automatischer Port-Berechnung
```bash
./install_unified.sh -n verwaltung
```
- Web-App: http://localhost:5001 (5000 + 1)
- MongoDB: localhost:27018 (27017 + 1)
- Mongo Express: http://localhost:8082 (8081 + 1)

### Instance mit Nummer
```bash
./install_unified.sh -n instance2
```
- Web-App: http://localhost:5002 (5000 + 2)
- MongoDB: localhost:27019 (27017 + 2)
- Mongo Express: http://localhost:8083 (8081 + 2)

### Nur Update (keine Daten löschen)
```bash
./install_unified.sh -u
```

### Force-Installation (überschreibt bestehende)
```bash
./install_unified.sh -f
```

## Optionen

| Option | Langform | Beschreibung |
|--------|----------|--------------|
| `-h` | `--help` | Hilfe anzeigen |
| `-p PORT` | `--port PORT` | Web-App Port (Standard: 5000) |
| `-m PORT` | `--mongodb-port PORT` | MongoDB Port (Standard: 27017) |
| `-e PORT` | `--express-port PORT` | Mongo Express Port (Standard: 8081) |
| `-n NAME` | `--name NAME` | Instance-Name (Standard: scandy) |
| `-f` | `--force` | Bestehende Installation überschreiben |
| `-u` | `--update` | Nur App aktualisieren |
| `-s` | `--silent` | Weniger Ausgabe |

## Port-Berechnung

Wenn ein Instance-Name mit Nummer angegeben wird, werden die Ports automatisch berechnet:

- **Web-App**: 5000 + Instance-Nummer
- **MongoDB**: 27017 + Instance-Nummer  
- **Mongo Express**: 8081 + Instance-Nummer

### Beispiele:
- `verwaltung` → Nummer 1 → Ports: 5001, 27018, 8082
- `instance2` → Nummer 2 → Ports: 5002, 27019, 8083
- `produktion5` → Nummer 5 → Ports: 5005, 27022, 8086

## Management

Nach der Installation wird ein `manage.sh` Skript erstellt:

```bash
# Container starten
./manage.sh start

# Status prüfen
./manage.sh status

# Logs anzeigen
./manage.sh logs

# Update
./manage.sh update

# Backup erstellen
./manage.sh backup

# In Container wechseln
./manage.sh shell

# Container stoppen
./manage.sh stop

# Bereinigung (ALLE Daten löschen!)
./manage.sh clean
```

## Mehrere Instances

Sie können mehrere Instances parallel betreiben:

```bash
# Instance 1: Verwaltung
./install_unified.sh -n verwaltung

# Instance 2: Produktion  
./install_unified.sh -n produktion

# Instance 3: Test
./install_unified.sh -n test
```

Jede Instance hat:
- Eigene Container-Namen
- Eigene Ports
- Eigene Datenbank
- Eigene Volumes
- Eigene Netzwerke

## Sicherheit

- **Sichere Passwörter**: Jede Installation generiert automatisch sichere Passwörter
- **Port-Konflikt-Prüfung**: Verhindert Port-Konflikte zwischen Instances
- **Isolierte Netzwerke**: Jede Instance hat ihr eigenes Docker-Netzwerk
- **Separate Volumes**: Daten sind zwischen Instances isoliert

## Migration von alten Skripten

### Von `install.sh`
```bash
# Alt
./install.sh

# Neu
./install_unified.sh
```

### Von `setup_instance.sh`
```bash
# Alt
./setup_instance.sh
# Dann manuell: cd scandy-verwaltung && ./manage.sh start

# Neu
./install_unified.sh -n verwaltung
```

### Von `install_production.sh`
```bash
# Alt
./install_production.sh

# Neu
./install_unified.sh -f
```

## Troubleshooting

### Port bereits in Verwendung
```bash
# Prüfe welche Ports belegt sind
lsof -i :5000
lsof -i :27017
lsof -i :8081

# Verwende andere Ports
./install_unified.sh -p 8080 -m 27018 -e 8082
```

### Container startet nicht
```bash
# Logs anzeigen
./manage.sh logs

# Container-Status prüfen
./manage.sh status

# Neustart versuchen
./manage.sh restart
```

### Daten verloren
```bash
# Backup erstellen (vor Änderungen!)
./manage.sh backup

# Nur App updaten (Daten bleiben)
./install_unified.sh -u
```

## Standard-Zugangsdaten

Nach der Installation:

- **Web-App**: http://localhost:[WEB_PORT]
- **Admin**: admin / admin123
- **Teilnehmer**: teilnehmer / admin123
- **Mongo Express**: http://localhost:[MONGO_EXPRESS_PORT]
- **MongoDB**: admin / [generiertes Passwort aus .env]

## Dateien

Nach der Installation werden erstellt:

- `.env` - Umgebungsvariablen
- `docker-compose.yml` - Container-Konfiguration
- `manage.sh` - Management-Skript
- `data/` - Datenverzeichnisse
- `backups/` - Backup-Verzeichnis
- `logs/` - Log-Verzeichnis

## Nächste Schritte

1. **Passwörter ändern**: Bearbeite `.env` für Produktion
2. **Backup-Strategie**: Konfiguriere automatische Backups
3. **Monitoring**: Richte Logging und Monitoring ein
4. **SSL/TLS**: Konfiguriere HTTPS für Produktion 

## Migration wichtiger Sicherheitsänderungen (August 2025)

- Docker Compose liest jetzt Secrets und URIs aus `.env` (statt Klartext in `docker-compose.https.yml`).
  - Aktion: `.env` anhand `env.example` erstellen/aktualisieren und sichere Werte setzen:
    - `MONGO_INITDB_ROOT_PASSWORD`, `SECRET_KEY`, `ME_CONFIG_BASICAUTH_PASSWORD`
    - `MONGODB_URI=mongodb://admin:${MONGO_INITDB_ROOT_PASSWORD}@scandy-mongodb:27017/${MONGODB_DB}?authSource=admin`
- Notfall-Adminroute `/emergency-admin` ist standardmäßig deaktiviert.
  - Nur falls erforderlich und ausschließlich lokal: `ENABLE_EMERGENCY_ADMIN=true` setzen, danach wieder entfernen.
- Passwortprüfung: Unsicherer scrypt-Fallback entfernt.
  - Falls alte Backups scrypt-Hashes enthalten, bitte Benutzerpasswörter über Admin-UI zurücksetzen.
- Debug/Config:
  - Produktion: `FLASK_ENV=production`, `FLASK_DEBUG=0` setzen.
  - Entwicklung: `FLASK_ENV=development`, optional `FLASK_DEBUG=1`.