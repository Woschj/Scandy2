# Scandy - Werkzeug- und Verbrauchsmaterialverwaltung

## 📋 Überblick

Scandy ist ein umfassendes Web-basiertes System zur Verwaltung von Werkzeugen, Verbrauchsmaterialien und Arbeitsaufträgen. Es bietet eine benutzerfreundliche Oberfläche für die Verwaltung von Inventar, Aufträgen und Benutzern.

## 🚀 Schnellstart

### Voraussetzungen
- Python 3.11+
- MongoDB
- Node.js (für CSS-Build)

### Installation
```bash
# Repository klonen
git clone <repository-url>
cd Scandy2

# Installation durchführen
./install_scandy_simple_new.sh
```

### Update
```bash
# System aktualisieren
./update_scandy_simple.sh
```

## 🏗️ Architektur

### Technologie-Stack
- **Backend**: Flask (Python)
- **Datenbank**: MongoDB
- **Frontend**: HTML5, TailwindCSS, JavaScript
- **Deployment**: Gunicorn, systemd

### Verzeichnisstruktur
```
Scandy2/
├── app/                    # Hauptapplikation
│   ├── routes/            # API-Routen
│   ├── models/            # Datenmodelle
│   ├── templates/         # HTML-Templates
│   ├── static/            # CSS, JS, Bilder
│   └── utils/             # Hilfsfunktionen
├── backups/               # Automatische Backups
├── logs/                  # Anwendungslogs
├── tests/                 # Testsuite
├── docker-compose.yml     # Docker-Konfiguration
├── requirements.txt       # Python-Abhängigkeiten
└── install_scandy_simple_new.sh  # Installationsscript
```

## ⚙️ Konfiguration

### Umgebungsvariablen (.env)
```bash
# Datenbank
MONGODB_URI=mongodb://localhost:27017/scandy
MONGODB_DB=scandy

# Sicherheit
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Webserver
WEB_PORT=5000
```

### Docker-Deployment
```bash
# Mit Docker starten
docker compose up -d

# Mit SSL
docker compose -f docker-compose.https.yml up -d
```

## 🔧 Verwendung

### Web-Interface
Nach der Installation ist Scandy unter `http://localhost:5000` erreichbar.

### Backup-System
Automatische tägliche Backups werden in `/backups` gespeichert.

### Logs
Anwendungslogs sind in `/logs` verfügbar.

## 🔐 Sicherheit

- Session-Management mit Flask-Session
- Rate-Limiting für API-Endpunkte
- Input-Validierung und CSRF-Schutz
- Sichere Passwort-Hashes (bcrypt)

## 📊 Features

- **Werkzeugverwaltung**: Inventar, Ausleihe, Wartung
- **Verbrauchsmaterialien**: Lagerbestand, Nachbestellungen
- **Auftragsverwaltung**: Tickets, Arbeitsaufträge, Zeiterfassung
- **Benutzerverwaltung**: Rollen, Berechtigungen, Abteilungen
- **Dashboard**: Übersichten, Statistiken, Berichte

## 🐛 Fehlerbehebung

### Häufige Probleme

**Service startet nicht:**
```bash
# Logs prüfen
sudo journalctl -u scandy.service -f

# Service-Status
sudo systemctl status scandy.service
```

**Datenbankverbindung fehlgeschlagen:**
```bash
# MongoDB-Status prüfen
sudo systemctl status mongod

# Verbindung testen
mongosh --eval "db.adminCommand('ping')"
```

### Backup wiederherstellen
```bash
# Backup-Dateien finden
ls backups/*.json

# Manuelle Wiederherstellung
mongorestore --db scandy backups/scandy_backup_YYYYMMDD_HHMMSS
```

## 📝 Lizenz

Dieses Projekt steht unter der MIT-Lizenz - siehe [LICENSE](LICENSE) Datei für Details.

## 🤝 Beitragen

1. Fork das Projekt
2. Erstelle einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Commit deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne einen Pull Request

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfe die Logs in `/logs`
2. Stelle sicher, dass alle Voraussetzungen erfüllt sind
3. Verwende die bereitgestellten Installations-/Update-Scripts