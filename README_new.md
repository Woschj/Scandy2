# Scandy - Werkzeug- und Verbrauchsmaterialverwaltung

**Moderne, modulare Webanwendung für Unternehmen zur Verwaltung von Werkzeugen, Verbrauchsmaterial und Aufgaben.**

[![Version](https://img.shields.io/badge/Version-Beta%200.8.1-blue.svg)](https://github.com/your-repo/scandy)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey.svg)](https://flask.palletsprojects.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.x-red.svg)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Inhaltsverzeichnis

- [🚀 Überblick](#-überblick)
- [✨ Features](#-features)
- [🏗️ Architektur](#️-architektur)
- [📦 Installation](#-installation)
- [⚙️ Konfiguration](#️-konfiguration)
- [🎯 Verwendung](#-verwendung)
- [👥 Rollen & Berechtigungen](#-rollen--berechtigungen)
- [🔧 Administration](#-administration)
- [🔒 Sicherheit](#-sicherheit)
- [🚀 Entwicklung](#-entwicklung)
- [📊 Monitoring](#-monitoring)
- [🆘 Fehlerbehebung](#-fehlerbehebung)
- [📝 API-Dokumentation](#-api-dokumentation)
- [🤝 Beitragen](#-beitragen)
- [📄 Lizenz](#-lizenz)

---

## 🚀 Überblick

Scandy ist eine moderne Flask-basierte Webanwendung zur **Verwaltung von Werkzeugen, Verbrauchsmaterial und Aufgaben** in Unternehmen. Speziell entwickelt für Werkstätten, Bildungseinrichtungen und Verwaltungen mit Fokus auf:

- **Barcode-basierte Identifikation** für schnelle Erfassung
- **Rollenbasierte Zugriffskontrolle** mit 4 Nutzerrollen
- **Modulare Microservices-Architektur** für einfache Erweiterung
- **Touch-optimierte Oberfläche** für mobile Geräte
- **Automatische Datensicherung** und Wiederherstellung

### 🎯 Zielgruppe

- **Werkstätten** - Werkzeugverwaltung und Ausleihe
- **Bildungseinrichtungen** - Ressourcen-Management
- **Verwaltungen** - Verbrauchsmaterial und Aufgaben
- **KMUs** - Einfache, skalierbare Lösung

---

## ✨ Features

### 🔧 Kernfunktionalitäten

- **📱 Werkzeugverwaltung**
  - Barcode-basierte Identifikation
  - Status-Tracking (verfügbar/ausgeliehen/defekt/wartung)
  - Vollständige Ausleih-Historie
  - Kategorisierung und Standortverwaltung

- **📦 Verbrauchsmaterial**
  - Bestandsverwaltung mit automatischer Verfolgung
  - Mindestbestand-Warnungen
  - Verbrauchsprognosen
  - Lieferantenverwaltung

- **🎫 Ticket-System**
  - Aufgaben- und Auftrags-Management
  - Status-Workflow (offen → zugewiesen → in Bearbeitung → gelöst)
  - Prioritäts-Management
  - Nachrichten-System und Datei-Uploads

- **👥 Nutzerverwaltung**
  - 4 Rollen: Admin, Mitarbeitende, Anwender, Teilnehmende
  - Berechtigungssystem mit granularer Kontrolle
  - Abteilungsbasierte Sichtbarkeit

### 🚀 Erweiterte Features

- **📷 Medien-Management** - Upload von Bildern und Dokumenten
- **💼 Job-Board** - Optionale Stellenausschreibungen
- **📊 Dashboard** - Echtzeit-Übersichten und Statistiken
- **🔄 QuickScan** - Touch-optimierte Barcode-Scanner
- **🌐 WordPress-Integration** - Kantinenplan-Integration
- **📱 Mobile-Optimierung** - Responsive Design
- **🔒 SSL-Unterstützung** - Sichere HTTPS-Verbindungen
- **💾 Automatische Backups** - Datenintegrität gewährleistet

---

## 🏗️ Architektur

### 🛠️ Technologie-Stack

**Backend:**
- **Python 3.11+** - Moderne Python-Version
- **Flask 3.x** - Leichtgewichtiges Web-Framework
- **MongoDB 7.x** - NoSQL-Datenbank
- **Gunicorn** - WSGI-Server für Produktion

**Frontend:**
- **HTML5** - Semantische Struktur
- **Tailwind CSS** - Utility-First CSS-Framework
- **DaisyUI** - Komponenten-Bibliothek
- **Vanilla JavaScript** - Progressive Enhancement

**Infrastructure:**
- **Docker & Docker Compose** - Containerisierung
- **Mongo Express** - Datenbank-Administration
- **Systemd** - Service-Management
- **Nginx** (optional) - Reverse Proxy

### 📁 Projektstruktur

```
scandy/
├── app/                          # Hauptanwendung
│   ├── __init__.py              # Flask-App Factory
│   ├── routes/                  # Web-Routen (modular)
│   │   ├── admin_*.py          # Modulare Admin-Bereiche
│   │   ├── api.py              # REST-API
│   │   └── auth.py             # Authentifizierung
│   ├── services/               # Business-Logik
│   ├── models/                 # Datenmodelle
│   ├── templates/              # HTML-Templates
│   ├── static/                 # CSS/JS/Medien
│   └── utils/                  # Hilfsfunktionen
├── backups/                     # Datensicherungen
├── logs/                        # Anwendungslogs
├── data/                        # Persistente Daten
├── venv/                        # Python Virtual Environment
├── install_scandy_simple_new.sh # Haupt-Installationsskript
├── update_scandy_simple.sh     # Update-Skript
├── docker-compose.yml          # Container-Orchestrierung
└── requirements.txt            # Python-Abhängigkeiten
```

### 🔧 Modulare Architektur

Scandy verwendet eine **Microservices-ähnliche modulare Architektur** innerhalb der Flask-Anwendung:

```
Admin-Bereich (aufgeteilt in Module):
├── admin_core.py     - Dashboard, Kernfunktionen
├── admin_users.py    - Nutzerverwaltung
├── admin_content.py  - CRUD-Operationen
├── admin_system.py   - Systemeinstellungen
├── admin_trash.py    - Papierkorb
├── admin_media.py    - Medien-Management
└── admin_tickets.py  - Ticket-Management
```

**Vorteile:**
- **🧹 Einfache Wartung** - Kleine, fokussierte Module
- **🚀 Parallele Entwicklung** - Teams arbeiten unabhängig
- **🔧 Isolierte Tests** - Einzelne Module testbar
- **📈 Skalierbarkeit** - Neue Features einfach hinzufügen

---

## 📦 Installation

### 🔧 Systemvoraussetzungen

**Minimal:**
- Ubuntu/Debian Linux
- 2 CPU-Kerne, 2 GB RAM, 5 GB Speicher
- Root-Zugriff für Installation

**Empfohlen:**
- Ubuntu 22.04+
- 4 CPU-Kerne, 4 GB RAM, 10 GB SSD
- Docker & Docker Compose

### 🚀 Schnellinstallation

```bash
# Repository klonen
git clone <repository-url> scandy
cd scandy

# Ausführbar machen und installieren
chmod +x install_scandy_simple_new.sh
sudo ./install_scandy_simple_new.sh
```

**Nach der Installation:**
- Scandy läuft auf `http://localhost/` (Port 80)
- Admin-Panel: `http://localhost/admin/`
- MongoDB: `localhost:27017`
- Mongo Express: `http://localhost:8081`

### ⚙️ Erstkonfiguration

1. **Web-Browser öffnen**: `http://localhost/`
2. **Setup-Assistent** durchlaufen
3. **Admin-Nutzer** erstellen
4. **System konfigurieren**:
   - Firmenname
   - Abteilungen einrichten
   - Kategorien definieren
   - E-Mail-Einstellungen (optional)

### 🔄 Updates

```bash
# Automatisches Update
sudo ./update_scandy_simple.sh

# Vollständiges Update
sudo ./update_scandy_universal.sh
```

---

## ⚙️ Konfiguration

### 📄 Umgebungsvariablen (.env)

```bash
# Datenbank
MONGODB_URI=mongodb://admin:PASSWORD@localhost:27017/scandy?authSource=admin
MONGO_INITDB_DATABASE=scandy

# Sicherheit
SECRET_KEY=your-super-secret-key-here
SESSION_COOKIE_SECURE=false  # true für HTTPS

# E-Mail (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Features
ENABLE_WEEKLY_REPORTS=true
ENABLE_JOB_BOARD=false
ENABLE_TICKET_SYSTEM=true
ENABLE_CANTEEN_INTEGRATION=false
```

### 🔧 Feature-Flags

```python
# In der Anwendung konfigurierbar
FEATURE_SETTINGS = {
    'weekly_reports': True,      # Wochenberichte
    'job_board': False,          # Job-Börse
    'ticket_system': True,       # Ticket-System
    'canteen_integration': False # Kantinen-Integration
}
```

### 👥 Abteilungsverwaltung

- **Abteilungen** definieren Berechtigungen und Sichtbarkeit
- **Department-Scopes** isolieren Daten zwischen Abteilungen
- **Admin-Nutzende** sehen alle Abteilungen
- **Mitarbeitende** sehen nur eigene Abteilung

---

## 🎯 Verwendung

### 📱 Erste Schritte

1. **Anmeldung**: `/auth/login`
2. **Dashboard** öffnen für Übersicht
3. **Erste Daten** anlegen:
   - Werkzeuge hinzufügen
   - Mitarbeitende registrieren
   - Kategorien definieren

### 🔧 Werkzeugverwaltung

#### Neues Werkzeug anlegen:
1. **Admin-Bereich** → "Werkzeuge" → "Neu"
2. **Barcode** automatisch generieren oder manuell eingeben
3. **Details** ausfüllen:
   - Name, Beschreibung, Kategorie
   - Anschaffungspreis, Wartungsintervalle
   - Standort und Verantwortliche

#### Ausleihe/Rückgabe:
- **Manuell**: Admin-Bereich → Ausleihe
- **QuickScan**: Touch-Oberfläche für mobile Geräte
- **Automatisch**: Barcode-Scan von Werkzeug + Mitarbeitende

### 📦 Verbrauchsmaterial

#### Bestandsverwaltung:
1. **Material anlegen** mit Mindestbestand
2. **Bestand anpassen** bei Ein-/Ausgang
3. **Automatische Warnungen** bei Unterschreitung
4. **Prognosen** basierend auf Verbrauchshistorie

### 🎫 Ticket-System

#### Neues Ticket erstellen:
1. **Ticket-Bereich** → "Neu"
2. **Typ wählen**: Allgemein/Auftrag/Materialbedarf
3. **Priorität setzen**: Niedrig/Normal/Hoch/Kritisch
4. **Beschreibung** und **Anhänge** hinzufügen

#### Workflow:
```
Offen → Zugewiesen → In Bearbeitung → Gelöst → Geschlossen
```

#### Kommunikation:
- **Nachrichten** zwischen allen Beteiligten
- **Datei-Uploads** für jeden Ticket
- **Status-Historie** vollständig nachvollziehbar

### 📊 Dashboard & Berichte

#### Echtzeit-Übersichten:
- **Werkzeug-Status**: Verfügbar/Ausgeliehen/Defekt
- **Bestands-Warnungen**: Kritische Verbrauchsmaterialien
- **Ticket-Statistiken**: Offen/Gelöst/Überfällig
- **Mitarbeitende-Auslastung**: Aktive Ausleihen

#### Export-Funktionen:
- **Excel-Export** für alle Listen
- **PDF-Berichte** für Tickets
- **CSV-Export** für Massendaten

---

## 👥 Rollen & Berechtigungen

### 👑 Administrator (Admin)
**Vollzugriff auf alle Funktionen:**
- ✅ Alle Nutzende verwalten
- ✅ Systemeinstellungen ändern
- ✅ Backups erstellen/wiederherstellen
- ✅ Alle Abteilungen einsehen
- ✅ Alle Tickets bearbeiten

### 🔧 Mitarbeitende
**Verwaltung innerhalb der eigenen Abteilung:**
- ✅ Werkzeuge und Materialien verwalten
- ✅ Tickets zuweisen und bearbeiten
- ✅ Ausleihen durchführen
- ✅ Berichte erstellen
- ❌ Kein Zugriff auf Systemeinstellungen

### 👤 Anwender (Nutzende)
**Eingeschränkte Verwaltung:**
- ✅ Eigene Tickets erstellen/bearbeiten
- ✅ Werkzeuge und Materialien einsehen
- ✅ Ausleihen anfordern
- ❌ Keine Verwaltung anderer Nutzende

### 🎓 Teilnehmende
**Minimale Berechtigungen:**
- ✅ Eigene Tickets erstellen
- ✅ Wochenberichte ausfüllen
- ✅ Job-Börse einsehen
- ❌ Kein Zugriff auf Verwaltungsfunktionen

### 🔐 Berechtigungssystem

```python
# Granulare Berechtigungen
PERMISSIONS = {
    'tools': {
        'view': True,
        'create': True,
        'edit': True,
        'delete': False
    },
    'tickets': {
        'view': True,
        'assign': True,
        'close': False
    }
}
```

---

## 🔧 Administration

### 👥 Nutzerverwaltung

#### Neuen Nutzende anlegen:
1. **Admin-Bereich** → "Nutzerverwaltung" → "Neu"
2. **Rolle zuweisen** (Admin/Mitarbeitende/Anwender/Teilnehmende)
3. **Abteilung zuweisen** für Sichtbarkeit
4. **Berechtigungen definieren** (optional)

#### Massenimport:
```bash
# Excel-Datei vorbereiten mit Spalten:
# username, email, role, department, firstname, lastname
```

### ⚙️ Systemeinstellungen

#### Grundkonfiguration:
- **Systemname** und **Beschreibung**
- **Logo hochladen** (max. 5MB)
- **Farbschema** anpassen
- **Sprache** einstellen

#### Feature-Management:
- **Wochenberichte** aktivieren/deaktivieren
- **Job-Börse** ein-/ausschalten
- **Ticket-System** konfigurieren
- **Kantinen-Integration** einrichten

### 💾 Backup & Wiederherstellung

#### Automatische Backups:
- **Täglich** um 02:00 Uhr
- **Wöchentlich** Sonntags
- **Monatlich** zum Monatsende
- **Aufbewahrung**: 7 Tage / 4 Wochen / 12 Monate

#### Manuelle Sicherung:
```bash
# Über Web-Interface: Admin → Backup → "Backup erstellen"
# Oder per API: POST /backup/create
```

#### Wiederherstellung:
```bash
# Über Web-Interface: Admin → Backup → Datei auswählen → "Wiederherstellen"
# Automatische Sicherung vor Restore
```

### 📊 Statistiken & Monitoring

#### System-Metriken:
- **CPU- und RAM-Auslastung**
- **Datenbank-Performance**
- **API-Response-Zeiten**
- **Fehler-Raten**

#### Nutzer-Aktivitäten:
- **Login-Häufigkeit**
- **Ticket-Erstellungen**
- **Ausleih-Statistiken**
- **Seitenaufrufe**

---

## 🔒 Sicherheit

### 🛡️ Sicherheitsmaßnahmen

#### Authentifizierung:
- **Passwort-Hashing** mit bcrypt
- **Session-Management** mit sicheren Cookies
- **Login-Versuche** limitiert (Anti-Brute-Force)
- **Zwei-Faktor-Authentifizierung** (geplant)

#### Autorisierung:
- **Rollenbasierte Zugriffe** (RBAC)
- **Department-Scopes** für Datenisolation
- **API-Rate-Limiting** (200 Requests/Tag pro IP)
- **CSRF-Schutz** für Formulare

#### Datenintegrität:
- **SSL/TLS-Verschlüsselung** (Let's Encrypt)
- **Datenbank-Authentifizierung**
- **Backup-Verschlüsselung**
- **Audit-Logging** aller Aktionen

### 🔐 Best Practices

#### Passwort-Richtlinien:
- **Mindestlänge**: 8 Zeichen
- **Komplexität**: Groß-/Kleinbuchstaben, Zahlen, Sonderzeichen
- **Regelmäßige Änderung** empfohlen
- **Passwort-Reset** über E-Mail

#### Netzwerksicherheit:
- **Firewall-Konfiguration** (ufw)
- **Fail2Ban** für SSH-Schutz
- **Regelmäßige Updates** des Systems
- **Monitoring** ungewöhnlicher Aktivitäten

#### Datenschutz:
- **DSGVO-konform** (geplant)
- **Datenminimierung** (nur notwendige Daten)
- **Löschkonzepte** für inaktive Nutzende
- **Datenschutzbeauftragte** benennen

### 🚨 Sicherheits-Checkliste

- [ ] **Starke Passwörter** für alle Nutzende
- [ ] **Regelmäßige Backups** aktiviert
- [ ] **SSL-Zertifikate** installiert und gültig
- [ ] **Firewall** konfiguriert
- [ ] **System-Updates** durchgeführt
- [ ] **Zugangsberechtigungen** überprüft
- [ ] **Logs** auf Anomalien prüfen
- [ ] **Sicherheits-Updates** installiert

---

## 🚀 Entwicklung

### 🛠️ Entwicklungsumgebung

```bash
# Repository klonen
git clone <repository-url> scandy-dev
cd scandy-dev

# Python Virtual Environment
python3 -m venv venv
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Entwicklungsserver starten
export FLASK_ENV=development
export FLASK_DEBUG=1
python app/wsgi.py
```

### 📁 Code-Organisation

#### Neue Features hinzufügen:

1. **Route erstellen**: `app/routes/neu_modul.py`
2. **Blueprint registrieren**: `app/routes/__init__.py`
3. **Template anlegen**: `app/templates/neu_modul/`
4. **Service schreiben**: `app/services/neu_service.py`
5. **Datenmodell**: `app/models/neu_model.py`

#### Beispiel: Neues Modul

```python
# app/routes/example.py
from flask import Blueprint, render_template
from app.utils.decorators import login_required

bp = Blueprint('example', __name__, url_prefix='/example')

@bp.route('/')
@login_required
def index():
    return render_template('example/index.html')
```

```python
# app/routes/__init__.py
from app.routes.example import bp as example_bp

# In init_app():
app.register_blueprint(example_bp)
```

### 🧪 Testing

```bash
# Unit Tests
python -m pytest tests/

# Integration Tests
curl http://localhost:5000/health

# API Tests
curl http://localhost:5000/api/tools
```

### 📦 Deployment

#### Produktionsumgebung:
```bash
# Docker-Deployment
docker-compose -f docker-compose.yml up -d

# Systemd-Service
sudo systemctl enable scandy
sudo systemctl start scandy
```

#### Skalierung:
- **Horizontale Skalierung** mit Load Balancer
- **Datenbank-Clustering** für Hochverfügbarkeit
- **CDN** für statische Assets
- **Redis** für Session-Speicher

---

## 📊 Monitoring

### 🏥 Health Checks

```bash
# System-Status
curl http://localhost/health
# {"status":"healthy","database":"connected","timestamp":"..."}
```

### 📈 Metriken

#### Anwendungs-Metriken:
- **Response Time** < 500ms (Ziel)
- **Uptime** > 99.5%
- **Error Rate** < 1%
- **Concurrent Users** max. 100

#### Datenbank-Metriken:
- **Connection Pool** aktiv überwachen
- **Query Performance** < 100ms
- **Storage Usage** < 80% Kapazität
- **Backup Success** 100%

### 📋 Logging

#### Log-Level:
- **DEBUG**: Detaillierte Informationen
- **INFO**: Normale Betriebsmeldungen
- **WARNING**: Warnungen
- **ERROR**: Fehler
- **CRITICAL**: Kritische Fehler

#### Log-Rotation:
- **Tägliche Rotation**
- **7 Tage Aufbewahrung**
- **Automatische Komprimierung**

### 🚨 Alerting

#### Automatische Benachrichtigungen:
- **System Down** (SMS/E-Mail)
- **Hohe CPU/RAM-Auslastung**
- **Datenbank-Verbindungsprobleme**
- **Backup-Fehler**
- **Sicherheitsvorfälle**

---

## 🆘 Fehlerbehebung

### 🚨 Häufige Probleme

#### 1. Scandy startet nicht
```bash
# Logs prüfen
sudo journalctl -u scandy -n 20

# Service-Status
sudo systemctl status scandy

# Manuell starten
cd /opt/scandy && source venv/bin/activate && python app/wsgi.py
```

#### 2. Datenbank-Verbindungsfehler
```bash
# MongoDB-Status prüfen
sudo systemctl status mongod

# Verbindung testen
mongosh --eval "db.runCommand('ping')"

# Logs prüfen
sudo tail -f /var/log/mongodb/mongod.log
```

#### 3. SSL-Zertifikate ablaufen
```bash
# Zertifikat erneuern
sudo certbot renew

# Nginx neu laden
sudo systemctl reload nginx
```

#### 4. Hohe Speicherauslastung
```bash
# Prozesse prüfen
ps aux --sort=-%mem | head -10

# MongoDB-Optimierung
mongosh --eval "db.runCommand({compact: 'scandy'})"
```

### 🔧 Wartungsaufgaben

#### Wöchentliche Checks:
- [ ] **Backup-Status** prüfen
- [ ] **Festplatten-Speicher** überwachen
- [ ] **Log-Dateien** rotieren
- [ ] **SSL-Zertifikate** auf Ablauf prüfen

#### Monatliche Aufgaben:
- [ ] **System-Updates** durchführen
- [ ] **Datenbank-Optimierung** (Indizes neu bauen)
- [ ] **Backup-Tests** durchführen
- [ ] **Performance-Metriken** analysieren

#### Jährliche Reviews:
- [ ] **Sicherheitsaudit** durchführen
- [ ] **Notfallwiederherstellung** testen
- [ ] **Skalierungsstrategie** überprüfen

---

## 📝 API-Dokumentation

### 🔗 Basis-URL
```
http://localhost/api/v1/
```

### 🔐 Authentifizierung
```bash
# Session-basiert
curl -X GET http://localhost/api/tools \
  -H "Cookie: session=your-session-id"
```

### 📋 Endpunkte

#### Werkzeuge
```http
GET    /api/tools                    # Alle Werkzeuge
GET    /api/tools/{barcode}          # Einzelnes Werkzeug
POST   /api/tools                    # Neues Werkzeug
PUT    /api/tools/{barcode}          # Werkzeug aktualisieren
DELETE /api/tools/{barcode}          # Werkzeug löschen
```

#### Nutzende
```http
GET    /api/users                    # Alle Nutzende
POST   /api/users                    # Neuen Nutzende anlegen
PUT    /api/users/{id}               # Nutzende aktualisieren
DELETE /api/users/{id}               # Nutzende löschen
```

#### Tickets
```http
GET    /api/tickets                  # Alle Tickets
POST   /api/tickets                  # Neues Ticket
GET    /api/tickets/{id}             # Ticket-Details
PUT    /api/tickets/{id}             # Ticket aktualisieren
POST   /api/tickets/{id}/messages    # Nachricht hinzufügen
```

### 📄 Response-Format

#### Erfolgreiche Antwort:
```json
{
  "status": "success",
  "message": "Operation erfolgreich",
  "data": { ... }
}
```

#### Fehlerantwort:
```json
{
  "status": "error",
  "message": "Fehlerbeschreibung",
  "code": "ERROR_CODE"
}
```

### ⚡ Rate Limiting
- **200 Requests** pro Tag pro IP-Adresse
- **50 Requests** pro Stunde pro IP-Adresse

---

## 🤝 Beitragen

### 🐛 Bug Reports
1. **GitHub Issue** erstellen
2. **Schritte zur Reproduktion** beschreiben
3. **System-Informationen** angeben
4. **Logs** beifügen (ohne sensible Daten)

### ✨ Feature Requests
1. **GitHub Issue** mit Label "enhancement"
2. **Detaillierte Beschreibung** des gewünschten Features
3. **Nutzen** für die Community erklären
4. **Mockups/Screenshots** falls möglich

### 🔧 Code-Beiträge
1. **Fork** des Repositories
2. **Feature-Branch** erstellen (`git checkout -b feature/neu-feature`)
3. **Tests schreiben** für neue Funktionen
4. **Code formatieren** (Black, Flake8)
5. **Pull Request** erstellen

### 📝 Coding Standards
- **PEP 8** für Python-Code
- **Google Style Guide** für Docstrings
- **Semantische Commit Messages**
- **Vollständige Testabdeckung**

---

## 📄 Lizenz

**MIT License**

Copyright (c) 2024 Scandy Development Team

Hiermit wird unentgeltlich jeder Person, die eine Kopie der Software und der zugehörigen Dokumentationen (die "Software") erhält, die Erlaubnis erteilt, sie uneingeschränkt zu nutzen, inklusive und ohne Ausnahme des Rechts, sie zu verwenden, zu kopieren, zu verändern, zusammenzufügen, zu verbreiten, zu unterlizenzieren und/oder zu verkaufen, und Personen, denen diese Software überlassen wird, diese Rechte zu verschaffen, unter den folgenden Bedingungen:

Der obige Urheberrechtsvermerk und dieser Erlaubnisvermerk sind in allen Kopien oder wesentlichen Teilen der Software beizufügen.

DIE SOFTWARE WIRD OHNE JEDE AUSDRÜCKLICHE ODER IMPLIZITE GARANTIE BEREITGESTELLT, EINSCHLIESSLICH DER GARANTIE ZUR BENUTZUNG FÜR DEN VORGESEHENEN ODER EINEM BESTIMMTEN ZWECK SOWIE JEGLICHER RECHTSVERLETZUNG, JEDOCH NICHT DARAUF BESCHRÄNKT. IN KEINEM FALL SIND DIE AUTOREN ODER URHEBERRECHTSINHABER FÜR JEGLICHEN SCHADEN ODER SONSTIGE ANSPRÜCHE HAFTBAR ZU MACHEN, OB INFOLGE DER ERFÜLLUNG EINES VERTRAGES, EINES DELIKTES ODER ANDERS IM ZUSAMMENHANG MIT DER SOFTWARE ODER SONSTIGEM GEBRAUCH DER SOFTWARE ENTSTANDEN.

---

## 📞 Support

### 📧 Kontakt
- **E-Mail**: support@scandy.local
- **GitHub Issues**: Für Bug Reports und Feature Requests
- **Dokumentation**: Vollständige Anleitung in diesem README

### 🆘 Notfall-Support
Bei kritischen Problemen:
1. **System-Status prüfen**: `curl http://localhost/health`
2. **Logs analysieren**: `sudo journalctl -u scandy -n 50`
3. **Backup wiederherstellen** falls nötig
4. **GitHub Issue** mit allen Details erstellen

### 📚 Weitere Ressourcen
- **Flask-Dokumentation**: https://flask.palletsprojects.com/
- **MongoDB-Manual**: https://docs.mongodb.com/
- **Tailwind CSS**: https://tailwindcss.com/
- **DaisyUI**: https://daisyui.com/

---

*Scandy - Professionelle Werkzeug- und Verbrauchsmaterialverwaltung für moderne Unternehmen.*
