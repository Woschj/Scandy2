# Scandy Installation auf macOS mit Docker Desktop

Dieses Dokument beschreibt die Installation von Scandy auf einem MacBook mit Docker Desktop.

## Voraussetzungen

### 1. Docker Desktop installieren
- Lade Docker Desktop von [docker.com](https://www.docker.com/products/docker-desktop/) herunter
- Installiere die macOS-Version
- Starte Docker Desktop nach der Installation
- Warte bis Docker vollständig geladen ist (das Docker-Symbol in der Menüleiste sollte grün sein)

### 2. Terminal öffnen
- Öffne die Terminal-App (Programme > Dienstprogramme > Terminal)
- Oder verwende Spotlight (Cmd+Leertaste) und suche nach "Terminal"

## Installation

### 1. Projekt herunterladen
```bash
# Navigiere zu einem Verzeichnis deiner Wahl
cd ~/Downloads

# Lade das Scandy-Projekt herunter (falls noch nicht geschehen)
# oder navigiere zum bestehenden Projektverzeichnis
cd /path/to/your/scandy/project
```

### 2. Installationsskript ausführen
```bash
# Mache das Skript ausführbar (falls noch nicht geschehen)
chmod +x install_scandy_macos.sh

# Führe das Installationsskript aus
./install_scandy_macos.sh
```

Das Skript wird:
- Docker Desktop überprüfen
- Eine Port-Auswahl anbieten
- Eine `.env`-Datei mit sicheren Passwörtern erstellen
- Docker Compose für macOS anpassen
- Alle Services starten
- Einen Admin-Benutzer erstellen

### 3. Port-Auswahl
Das Skript bietet folgende Port-Optionen:
- **Port 5000**: Standard-Scandy-Port (empfohlen)
- **Port 8080**: Häufig verwendeter Port
- **Port 3000**: Entwicklungsport
- **Benutzerdefiniert**: Eigener Port nach Wahl

## Nach der Installation

### Zugriff auf die Anwendung
- **Web-App**: http://localhost:[PORT] (z.B. http://localhost:5000)
- **MongoDB**: mongodb://localhost:27017/scandy
- **Mongo Express**: http://localhost:8081 (Datenbank-Verwaltung)

### Standard-Anmeldedaten
- **Benutzername**: admin
- **Passwort**: Wird während der Installation angezeigt und in der `.env`-Datei gespeichert

## Verwaltung

### Nützliche Docker-Befehle
```bash
# Status aller Services anzeigen
docker-compose -f docker-compose.macos.yml ps

# Logs aller Services anzeigen
docker-compose -f docker-compose.macos.yml logs -f

# Alle Services stoppen
docker-compose -f docker-compose.macos.yml down

# Alle Services neu starten
docker-compose -f docker-compose.macos.yml restart

# Bestimmten Service neu starten
docker-compose -f docker-compose.macos.yml restart scandy-app-scandy
```

### Logs anzeigen
```bash
# Alle Logs
docker-compose -f docker-compose.macos.yml logs

# Nur App-Logs
docker-compose -f docker-compose.macos.yml logs scandy-app-scandy

# Logs in Echtzeit verfolgen
docker-compose -f docker-compose.macos.yml logs -f
```

## Sicherheit

### Wichtige Sicherheitsmaßnahmen
1. **Passwörter ändern**: Ändere alle Standard-Passwörter in der `.env`-Datei
2. **Firewall**: Stelle sicher, dass nur die benötigten Ports freigegeben sind
3. **Updates**: Halte Docker Desktop und die Scandy-Anwendung aktuell

### Passwörter ändern
```bash
# Bearbeite die .env-Datei
nano .env

# Wichtige Variablen:
# - MONGO_INITDB_ROOT_PASSWORD
# - SECRET_KEY
# - ME_CONFIG_BASICAUTH_PASSWORD
```

## Fehlerbehebung

### Häufige Probleme

#### Docker läuft nicht
```bash
# Prüfe Docker-Status
docker info

# Starte Docker Desktop neu
# Prüfe ob genügend Speicher verfügbar ist
```

#### Port bereits belegt
```bash
# Prüfe welche Ports belegt sind
lsof -i :5000

# Wähle einen anderen Port oder beende den blockierenden Prozess
```

#### App startet nicht
```bash
# Prüfe Container-Status
docker-compose -f docker-compose.macos.yml ps

# Prüfe Logs
docker-compose -f docker-compose.macos.yml logs scandy-app-scandy

# Prüfe ob alle Services laufen
docker-compose -f docker-compose.macos.yml logs
```

### Logs analysieren
```bash
# App-Logs in Echtzeit
docker-compose -f docker-compose.macos.yml logs -f scandy-app-scandy

# MongoDB-Logs
docker-compose -f docker-compose.macos.yml logs -f scandy-mongodb-scandy

# Mongo Express-Logs
docker-compose -f docker-compose.macos.yml logs -f scandy-mongo-express-scandy
```

## Deinstallation

### Alle Services stoppen
```bash
docker-compose -f docker-compose.macos.yml down
```

### Daten löschen (Vorsicht!)
```bash
# Alle Docker-Volumes löschen (alle Daten gehen verloren!)
docker-compose -f docker-compose.macos.yml down -v

# Oder einzelne Volumes
docker volume rm scandy2_mongodb_data_scandy
docker volume rm scandy2_app_uploads_scandy
```

### Docker-Images löschen
```bash
# Alle Scandy-Images löschen
docker rmi scandy-local:dev-scandy
docker rmi mongo:7
docker rmi mongo-express:1.0.0
```

## Support

Bei Problemen:
1. Prüfe die Logs mit `docker-compose -f docker-compose.macos.yml logs`
2. Stelle sicher, dass Docker Desktop läuft
3. Prüfe ob genügend Speicher und CPU verfügbar sind
4. Starte Docker Desktop neu
5. Führe das Installationsskript erneut aus

## Technische Details

### Verwendete Docker-Images
- **MongoDB**: mongo:7 (Datenbank)
- **Mongo Express**: mongo-express:1.0.0 (Datenbank-Verwaltung)
- **Scandy App**: Wird aus dem lokalen Dockerfile gebaut

### Netzwerk
- Alle Services laufen im `scandy-network-scandy` Netzwerk
- MongoDB ist auf Port 27017 erreichbar
- Mongo Express ist auf Port 8081 erreichbar
- Scandy-App ist auf dem gewählten Port erreichbar

### Volumes
- **mongodb_data_scandy**: MongoDB-Daten
- **app_uploads_scandy**: Hochgeladene Dateien
- **app_backups_scandy**: Backup-Dateien
- **app_logs_scandy**: Anwendungs-Logs
- **app_sessions_scandy**: Session-Daten
