# Scandy - Vollständige Projektdokumentation
**Version: Beta 0.8.1**  
**Autor: Andreas Klann**  
**Erstellungsdatum: Januar 2025**

---

## Inhaltsverzeichnis

1. [Projektübersicht](#projektübersicht)
2. [Systemarchitektur](#systemarchitektur)
3. [Installation und Setup](#installation-und-setup)
4. [Funktionale Module](#funktionale-module)
5. [Benutzerrollen und Berechtigungen](#benutzerrollen-und-berechtigungen)
6. [API-Dokumentation](#api-dokumentation)
7. [Datenmodell](#datenmodell)
8. [Backup-System](#backup-system)
9. [Multi-Instance-Setup](#multi-instance-setup)
10. [Deployment und Betrieb](#deployment-und-betrieb)
11. [Entwicklung und Erweiterung](#entwicklung-und-erweiterung)
12. [Troubleshooting](#troubleshooting)

---

## Projektübersicht

### Was ist Scandy?

Scandy ist eine moderne, Flask-basierte Webanwendung zur **Verwaltung von Werkzeugen, Verbrauchsgütern und Aufgaben** in Unternehmen und Organisationen. Das System wurde speziell für die Bedürfnisse von Werkstätten, Bildungseinrichtungen und Verwaltungen entwickelt.

### Hauptfunktionen

- **🔧 Werkzeugverwaltung**: Vollständige Barcode-basierte Werkzeugverwaltung mit Ausleihe-System
- **📦 Verbrauchsgüterverwaltung**: Bestandsverwaltung mit Mindestbestand-Warnungen
- **🎫 Ticket-System**: Auftrags- und Ticket-Management mit verschiedenen Kategorien
- **👥 Benutzerverwaltung**: Rollenbasierte Zugriffskontrolle mit 4 Benutzertypen
- **💼 Job-Board**: Stellenausschreibungs-System (optional)
- **📊 Berichte**: Umfassende Berichtsfunktionen und Dashboard
- **📱 QuickScan**: Touch-optimierte Barcode-Scanner-Integration
- **💾 Backup-System**: Automatische und manuelle Datensicherung
- **🌐 Multi-Instance**: Parallelbetriebs mehrerer Instanzen
- **📸 Medien-Upload**: Datei- und Bildverwaltung für alle Entitäten

### Technologie-Stack

**Backend:**
- Python 3.11+
- Flask (Webframework)
- MongoDB 7 (Datenbank)
- Gunicorn (WSGI-Server)

**Frontend:**
- HTML5 + Jinja2 Templates
- Tailwind CSS + DaisyUI
- Vanilla JavaScript
- Touch-optimiert für mobile Geräte

**Infrastructure:**
- Docker & Docker Compose
- Mongo Express (DB-Administration)
- Unified Backup System
- Health Monitoring

---

## Systemarchitektur

### Anwendungsstruktur

```
scandy/
├── app/                           # Hauptanwendung
│   ├── __init__.py               # Flask App Factory (416 Zeilen)
│   ├── config/                   # Konfiguration
│   │   ├── config.py            # Hauptkonfiguration
│   │   └── version.py           # Versionsverwaltung
│   ├── models/                   # Datenbankmodelle
│   │   ├── mongodb_database.py  # MongoDB-Verbindung
│   │   ├── mongodb_models.py    # MongoDB-Modelle (914 Zeilen)
│   │   ├── tool.py              # Werkzeug-Modelle
│   │   └── user.py              # Benutzer-Modelle
│   ├── routes/                   # API-Routen (21 Module)
│   │   ├── admin.py             # Admin-Funktionen (18.954 Zeilen!)
│   │   ├── api.py               # API-Endpunkte (549 Zeilen)
│   │   ├── auth.py              # Authentifizierung (355 Zeilen)
│   │   ├── backup_routes.py     # Backup-API (354 Zeilen)
│   │   ├── consumables.py       # Verbrauchsmaterialien (470 Zeilen)
│   │   ├── dashboard.py         # Dashboard
│   │   ├── history.py           # Ausleih-Historie
│   │   ├── jobs.py              # Job-Board (808 Zeilen)
│   │   ├── lending.py           # Ausleihe-Logik
│   │   ├── main.py              # Hauptrouten
│   │   ├── media.py             # Medien-Upload (562 Zeilen)
│   │   ├── quick_scan.py        # QuickScan-Interface
│   │   ├── setup.py             # System-Setup
│   │   ├── tickets.py           # Ticket-System (2.182 Zeilen)
│   │   ├── tools.py             # Werkzeugverwaltung (488 Zeilen)
│   │   └── workers.py           # Mitarbeiterverwaltung (1.118 Zeilen)
│   ├── services/                 # Business Logic Services
│   │   ├── job_service.py       # Job-Management
│   │   ├── ticket_service.py    # Ticket-Management
│   │   └── admin_backup_service.py # Backup-Services
│   ├── static/                   # Statische Dateien
│   │   ├── css/                 # Stylesheets
│   │   ├── js/                  # JavaScript
│   │   ├── images/              # Bilder
│   │   └── uploads/             # Hochgeladene Dateien
│   ├── templates/               # HTML-Templates
│   │   ├── admin/               # Admin-Templates
│   │   ├── auth/                # Auth-Templates
│   │   ├── components/          # UI-Komponenten
│   │   ├── consumables/         # Verbrauchsmaterialien-Templates
│   │   ├── dashboard/           # Dashboard-Templates
│   │   ├── jobs/                # Job-Board-Templates
│   │   ├── tickets/             # Ticket-Templates
│   │   ├── tools/               # Werkzeug-Templates
│   │   └── workers/             # Mitarbeiter-Templates
│   ├── utils/                   # Hilfsfunktionen
│   │   ├── auth_utils.py       # Authentifizierung
│   │   ├── backup_manager.py   # Backup-Management
│   │   ├── unified_backup_manager.py # Vereinheitlichtes Backup
│   │   ├── database_helpers.py # Datenbank-Hilfen
│   │   ├── email_utils.py      # E-Mail-Funktionen
│   │   ├── error_handler.py    # Fehlerbehandlung
│   │   ├── media_manager.py    # Medien-Management
│   │   └── logger.py           # Logging-System
│   ├── constants.py            # System-Konstanten
│   └── wsgi.py                 # WSGI-Entry-Point
├── backups/                    # Backup-Dateien
├── logs/                       # Log-Dateien
├── data/                       # Persistente Daten
├── mongo-init/                 # MongoDB-Initialisierung
├── docker-compose.yml          # Docker-Orchestrierung
├── Dockerfile                  # Container-Definition
├── requirements.txt            # Python-Abhängigkeiten
├── install_unified.sh          # Vereinheitlichtes Installationsskript
├── manage.sh                   # Management-Skript
└── README.md                   # Basis-Dokumentation
```

### Datenbankarchitektur

Scandy verwendet **MongoDB 7** mit zwei Hauptdatenbanken:

#### Hauptdatenbank (`scandy`)
- **tools**: Werkzeuge mit Barcode-Identifikation
- **consumables**: Verbrauchsmaterialien mit Bestandsführung
- **workers**: Mitarbeiter und Benutzer
- **lendings**: Ausleih-Transaktionen
- **consumable_usages**: Verbrauchshistorie
- **departments**: Abteilungen
- **categories**: Kategorien für Tools/Consumables
- **locations**: Standorte
- **users**: System-Benutzer mit Rollen
- **settings**: System-Einstellungen
- **jobs**: Stellenausschreibungen (Job-Board)

#### Ticket-Datenbank (`scandy_tickets`)
- **tickets**: Tickets/Aufträge mit Status-Workflow
- **ticket_messages**: Nachrichten und Kommunikation
- **ticket_history**: Änderungshistorie
- **auftrag_details**: Auftragsdetails
- **auftrag_material**: Auftragsmaterial

---

## Installation und Setup

### Systemvoraussetzungen

**Minimale Anforderungen:**
- Betriebssystem: Windows 10/11, macOS, Linux
- Docker Desktop (Windows/macOS) oder Docker Engine (Linux)
- Git
- 2 CPU-Kerne, 2 GB RAM, 5 GB freier Speicherplatz

**Empfohlene Konfiguration:**
- 4 CPU-Kerne, 4 GB RAM, 10 GB freier Speicherplatz
- SSD für bessere Performance

### Vereinheitlichte Installation

Scandy verwendet ein **vereinheitlichtes Installationsskript** (`install_unified.sh`), das alle vorherigen Skripte ersetzt:

#### Standard-Installation

```bash
# Repository klonen
git clone [repository-url] scandy
cd scandy

# Standard-Installation (Ports: 5000, 27017, 8081)
chmod +x install_unified.sh
./install_unified.sh
```

#### Installation mit benutzerdefinierten Ports

```bash
# Custom Ports spezifizieren
./install_unified.sh -p 8080 -m 27018 -e 8082
```

#### Named Instance mit automatischer Port-Berechnung

```bash
# Instance-Name angeben (automatische Port-Berechnung)
./install_unified.sh -n verwaltung
# Resultat: Web-App: 5001, MongoDB: 27018, Mongo Express: 8082
```

#### Update-Modus

```bash
# Nur App-Update (Daten bleiben erhalten)
./install_unified.sh -u
```

### Post-Installation Setup

Nach der Installation:

1. **Web-App aufrufen**: http://localhost:5000
2. **Setup-Assistent durchlaufen**:
   - Admin-Benutzer erstellen
   - System-Namen konfigurieren
   - E-Mail-Einstellungen (optional)
   - Kategorien und Abteilungen anlegen

3. **Standard-Zugangsdaten** (falls Setup übersprungen):
   - Benutzer: `admin`
   - Passwort: `admin123`

### Wichtige Konfigurationsdateien

#### `.env` Datei (automatisch erstellt)
```env
# Basis-Konfiguration
MONGODB_URI=mongodb://admin:PASSWORD@localhost:27017/scandy?authSource=admin
MONGODB_DB=scandy
SECRET_KEY=generierter-secret-key
SYSTEM_NAME=Scandy

# E-Mail-Konfiguration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Feature-Flags
ENABLE_TICKET_SYSTEM=true
ENABLE_JOB_BOARD=false
ENABLE_WEEKLY_REPORTS=true
```

---

## Funktionale Module

### 1. Werkzeugverwaltung

**Kernfunktionen:**
- Barcode-basierte Identifikation
- Status-Tracking (verfügbar, ausgeliehen, defekt, in Wartung)
- Kategorisierung und Standortverwaltung
- Vollständige Ausleih-Historie
- Wartungsprotokoll

**API-Routen:**
```
GET    /tools/                    # Werkzeug-Übersicht
POST   /tools/add                 # Neues Werkzeug
GET    /tools/<barcode>           # Details
POST   /tools/<barcode>/edit      # Bearbeiten
POST   /tools/<barcode>/status    # Status ändern
DELETE /tools/<barcode>/delete    # Löschen
```

**Datenmodell (tools Collection):**
```json
{
  "_id": "string",
  "barcode": "T001234",
  "name": "Bohrmaschine XY",
  "category": "Elektrowerkzeuge",
  "location": "Werkstatt 1",
  "status": "verfügbar",
  "condition": "gut",
  "purchase_date": "2024-01-15",
  "maintenance_due": "2024-12-31",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-20T14:30:00Z",
  "deleted": false
}
```

### 2. Verbrauchsgüterverwaltung

**Kernfunktionen:**
- Bestandsverwaltung mit automatischer Verfolgung
- Mindestbestand-Warnungen
- Verbrauchsprognosen basierend auf Historie
- Bestellvorschläge
- Lieferantenverwaltung

**API-Routen:**
```
GET    /consumables/                     # Übersicht
POST   /consumables/add                  # Hinzufügen
GET    /consumables/<barcode>            # Details
POST   /consumables/<barcode>/edit       # Bearbeiten
POST   /consumables/<barcode>/adjust-stock # Bestand anpassen
GET    /consumables/<barcode>/forecast   # Prognose
```

**Datenmodell (consumables Collection):**
```json
{
  "_id": "string",
  "barcode": "C001234",
  "name": "Schrauben M6x20",
  "category": "Befestigungsmaterial",
  "unit": "Stück",
  "current_stock": 150,
  "min_stock": 50,
  "max_stock": 500,
  "cost_per_unit": 0.15,
  "supplier": "Baumarkt XY",
  "last_ordered": "2024-01-10",
  "forecast_monthly_usage": 25
}
```

### 3. Ausleihsystem

**Kernfunktionen:**
- Manuelle Ausleihe über Admin-Interface
- QuickScan für schnelle Barcode-basierte Ausleihe/Rückgabe
- Überfälligkeitsverfolgung
- Automatische Benachrichtigungen
- Vollständige Audit-Historie

**Workflow:**
1. **Ausleihe**: Werkzeug + Mitarbeiter scannen → System verknüpft
2. **Rückgabe**: Werkzeug scannen → Status wird automatisch aktualisiert
3. **Überfälligkeit**: Automatische Erkennung und Warnung

**Datenmodell (lendings Collection):**
```json
{
  "_id": "string",
  "tool_barcode": "T001234",
  "worker_barcode": "M001",
  "lent_at": "2024-01-20T09:00:00Z",
  "due_date": "2024-01-22T17:00:00Z",
  "returned_at": null,
  "notes": "Für Projekt ABC",
  "lent_by": "admin",
  "status": "active"
}
```

### 4. Ticket-System

**Kernfunktionen:**
- Verschiedene Ticket-Typen: Allgemein, Auftrag, Materialbedarf
- Status-Workflow: offen → zugewiesen → in_bearbeitung → gelöst → geschlossen
- Prioritäts-Management (niedrig, normal, hoch, kritisch)
- Nachrichten-System für Kommunikation
- Vollständige Änderungshistorie
- Datei-Uploads pro Ticket
- Auftragsdetails und Materiallisten

**API-Routen:**
```
GET    /tickets/                  # Ticket-Übersicht
POST   /tickets/create            # Neues Ticket
GET    /tickets/<id>              # Details
POST   /tickets/<id>/edit         # Bearbeiten
POST   /tickets/<id>/assign       # Zuweisen
POST   /tickets/<id>/message      # Nachricht hinzufügen
POST   /tickets/<id>/close        # Schließen
```

**Erweiterte Features:**
- **Ticket-Historie**: Automatische Verfolgung aller Änderungen
- **Medien-Upload**: Bilder und Dokumente anhängen
- **Benachrichtigungen**: E-Mail-Benachrichtigungen bei Status-Änderungen
- **Export-Funktionen**: Tickets als PDF/Word exportieren

### 5. Job-Board (Optional)

**Kernfunktionen:**
- Stellenausschreibungs-Management
- Kategorisierung nach Branchen
- Volltext-Suche
- Bewerbungs-Management
- Medien-Upload für Job-Beschreibungen

**Datenmodell (jobs Collection):**
```json
{
  "_id": "string",
  "title": "Software-Entwickler",
  "company": "Tech Corp",
  "location": "Berlin",
  "industry": "IT",
  "job_type": "Vollzeit",
  "description": "...",
  "requirements": "...",
  "benefits": "...",
  "salary_range": "50.000 - 70.000 €",
  "contact_email": "hr@techcorp.com",
  "created_by": "admin",
  "created_at": "2024-01-20T10:00:00Z",
  "expires_at": "2024-02-20T23:59:59Z",
  "active": true
}
```

### 6. Medien-Upload-System

**Kernfunktionen:**
- Universeller Upload für alle Entitäten (Tools, Consumables, Tickets, Jobs)
- Automatische Bildoptimierung und Größenanpassung
- Unterstützte Formate: Bilder (JPG, PNG, GIF), Dokumente (PDF, DOC, DOCX)
- Maximale Dateigröße: 10MB pro Datei
- Maximale Anzahl: 10 Dateien pro Entität

**Upload-API:**
```
POST /media/<entity_type>/<entity_id>/upload
DELETE /media/<entity_type>/<entity_id>/<filename>
GET /media/<entity_type>/<entity_id>/list
```

### 7. Wochenberichte (Timesheet-System)

**Kernfunktionen:**
- Wöchentliche Arbeitszeit-Erfassung
- Aufgaben-Dokumentation pro Tag
- PDF-Export der Berichte
- Freigabe-Workflow
- Integration mit Teilnehmer-Rolle

---

## Benutzerrollen und Berechtigungen

### Rollenhierarchie

#### 1. Admin (Vollzugriff)
**Berechtigungen:**
- ✅ Vollzugriff auf alle Funktionen
- ✅ Kann alle Tickets sehen und bearbeiten
- ✅ Kann alle Benutzer verwalten
- ✅ Kann System-Einstellungen ändern
- ✅ Kann Backups erstellen/wiederherstellen
- ✅ Kann Multi-Instance-Setup verwalten
- ✅ Zugriff auf alle Admin-APIs

#### 2. Mitarbeiter
**Berechtigungen:**
- ✅ Kann Werkzeuge und Verbrauchsgüter verwalten
- ✅ Kann andere Mitarbeiter verwalten
- ✅ Kann manuelle Ausleihe durchführen
- ✅ Kann alle Tickets sehen und bearbeiten
- ✅ Kann Jobs erstellen und verwalten (falls aktiviert)
- ✅ Kann Wochenberichte erstellen (falls aktiviert)
- ❌ Kein Zugriff auf System-Einstellungen
- ❌ Kein Zugriff auf Benutzerverwaltung

#### 3. Anwender
**Berechtigungen:**
- ✅ Kann Werkzeuge und Verbrauchsgüter ansehen
- ✅ Kann Werkzeuge und Verbrauchsgüter hinzufügen/bearbeiten
- ✅ Kann manuelle Ausleihe durchführen
- ✅ Kann eigene Tickets erstellen und bearbeiten
- ✅ Kann zugewiesene Tickets bearbeiten
- ✅ Kann offene Tickets ansehen
- ✅ Kann Wochenberichte erstellen (falls aktiviert)
- ❌ Kein Zugriff auf Mitarbeiter-Verwaltung
- ❌ Kein Zugriff auf Admin-Funktionen

#### 4. Teilnehmer (Eingeschränkt)
**Berechtigungen:**
- ✅ Kann eigene Wochenberichte erstellen und verwalten
- ✅ Kann eigene Aufträge/Tickets erstellen
- ✅ Kann eigene Medien hochladen
- ❌ Kein Zugriff auf Werkzeug-/Verbrauchsgüter-Verwaltung
- ❌ Kein Zugriff auf QuickScan
- ❌ Kein Zugriff auf Admin-Bereiche
- ❌ Kann keine API-Änderungen vornehmen

### Decorator-System

```python
# Verfügbare Berechtigungs-Decorators
@login_required           # Alle eingeloggten Benutzer
@admin_required          # Nur Admin
@mitarbeiter_required    # Admin + Mitarbeiter
@not_teilnehmer_required # Alle außer Teilnehmer
@teilnehmer_required     # Nur Teilnehmer
```

---

## API-Dokumentation

### Authentifizierung

**Session-basierte Authentifizierung:**
- Login über `/auth/login`
- Session-Cookie wird gesetzt
- Automatischer Logout nach Inaktivität

### Core API-Endpunkte

#### Werkzeuge API
```http
GET /api/tools                    # Liste aller Werkzeuge
GET /api/tools/<barcode>          # Werkzeug-Details
POST /api/tools                   # Neues Werkzeug erstellen
PUT /api/tools/<barcode>          # Werkzeug aktualisieren
DELETE /api/tools/<barcode>       # Werkzeug löschen
```

#### Ausleihe API
```http
POST /api/lending/process         # Ausleihe verarbeiten
POST /api/lending/return          # Rückgabe verarbeiten
GET /api/lending/history          # Ausleih-Historie
GET /api/lending/overdue          # Überfällige Ausleihen
```

#### Tickets API
```http
GET /api/tickets                  # Ticket-Liste
POST /api/tickets                 # Neues Ticket
GET /api/tickets/<id>             # Ticket-Details
PUT /api/tickets/<id>             # Ticket aktualisieren
POST /api/tickets/<id>/messages   # Nachricht hinzufügen
POST /api/tickets/<id>/assign     # Ticket zuweisen
```

#### Backup API
```http
POST /backup/create               # Backup erstellen
GET /backup/list                  # Backup-Liste
POST /backup/restore/<filename>   # Backup wiederherstellen
POST /backup/upload               # Backup hochladen
```

### Response-Format

**Erfolgreiche Antwort:**
```json
{
  "status": "success",
  "message": "Operation erfolgreich",
  "data": { ... }
}
```

**Fehler-Antwort:**
```json
{
  "status": "error",
  "message": "Fehlerbesschreibung",
  "code": "ERROR_CODE"
}
```

---

## Datenmodell

### MongoDB Collections

#### tools Collection
```javascript
{
  _id: ObjectId,
  barcode: String,           // Eindeutige Barcode-ID
  name: String,              // Werkzeugname
  description: String,       // Beschreibung
  category: String,          // Kategorie
  location: String,          // Standort
  status: String,            // verfügbar|ausgeliehen|defekt|wartung
  condition: String,         // Zustand
  purchase_date: Date,       // Kaufdatum
  purchase_price: Number,    // Kaufpreis
  maintenance_due: Date,     // Nächste Wartung
  maintenance_history: [     // Wartungshistorie
    {
      date: Date,
      description: String,
      cost: Number,
      performed_by: String
    }
  ],
  lending_history: Array,    // Verweis auf lendings
  created_at: Date,
  updated_at: Date,
  deleted: Boolean
}
```

#### lendings Collection
```javascript
{
  _id: ObjectId,
  tool_barcode: String,      // Verweis auf Werkzeug
  worker_barcode: String,    // Verweis auf Mitarbeiter
  lent_at: Date,            // Ausleih-Zeitpunkt
  due_date: Date,           // Rückgabe-Datum
  returned_at: Date,        // Tatsächliche Rückgabe
  notes: String,            // Notizen
  lent_by: String,          // Ausgeliehen von (Username)
  returned_by: String,      // Zurückgegeben an (Username)
  status: String,           // active|returned|overdue
  reminder_sent: Boolean    // Erinnerung gesendet
}
```

#### tickets Collection
```javascript
{
  _id: ObjectId,
  ticket_number: String,     // Eindeutige Ticket-Nummer
  title: String,
  description: String,
  category: String,          // allgemein|auftrag|materialbedarf
  priority: String,          // niedrig|normal|hoch|kritisch
  status: String,            // offen|zugewiesen|in_bearbeitung|gelöst|geschlossen
  created_by: String,        // Ersteller (Username)
  assigned_to: String,       // Zugewiesener Bearbeiter
  department: String,        // Abteilung
  due_date: Date,           // Fälligkeitsdatum
  estimated_hours: Number,   // Geschätzte Arbeitszeit
  actual_hours: Number,      // Tatsächliche Arbeitszeit
  tags: [String],           // Tags/Schlagwörter
  created_at: Date,
  updated_at: Date,
  closed_at: Date,
  
  // Auftragsspezifische Felder
  customer_name: String,
  customer_contact: String,
  project_details: Object,
  materials_needed: [Object]
}
```

### Indizierung

**Performance-kritische Indizes:**
```javascript
// Tools
db.tools.createIndex({ "barcode": 1 }, { unique: true })
db.tools.createIndex({ "status": 1 })
db.tools.createIndex({ "category": 1 })

// Lendings
db.lendings.createIndex({ "tool_barcode": 1 })
db.lendings.createIndex({ "worker_barcode": 1 })
db.lendings.createIndex({ "status": 1 })
db.lendings.createIndex({ "due_date": 1 })

// Tickets
db.tickets.createIndex({ "ticket_number": 1 }, { unique: true })
db.tickets.createIndex({ "status": 1 })
db.tickets.createIndex({ "assigned_to": 1 })
db.tickets.createIndex({ "created_at": -1 })
```

---

## Backup-System

### Vereinheitlichtes Backup-System

Scandy verwendet ein **dreistufiges Backup-System**:

1. **ZIP-Backups** (Neu, empfohlen)
2. **JSON-Backups** (Legacy)
3. **Native MongoDB-Backups**

### Backup-Arten

#### 1. ZIP-Backups (Unified Backup Manager)
```bash
# Automatisches Backup mit Medien
POST /backup/create
{
  "include_media": true,
  "compress": true
}
```

**Inhalt:**
- Vollständige MongoDB-Daten (JSON-Export)
- Hochgeladene Medien-Dateien
- System-Konfiguration
- Metadaten und Checksums

#### 2. JSON-Backups (Legacy)
- Reine Datenbank-Exports
- Kleinere Dateigröße
- Ohne Medien-Dateien

#### 3. Native MongoDB-Backups
- Binäre MongoDB-Dumps
- Fastest Restore
- Für große Datenmengen

### Backup-Verwaltung

**Automatische Backups:**
```python
# Automatisch vor kritischen Operationen
- Vor jedem Restore
- Vor System-Updates
- Wöchentliche Scheduled Backups
```

**Backup-Rotation:**
- Täglich: 7 Backups behalten
- Wöchentlich: 4 Backups behalten
- Monatlich: 12 Backups behalten

**Backup-Verifizierung:**
- Checksums für Datenintegrität
- Automatische Restore-Tests
- Fehler-Logging

### Restore-Prozess

1. **Sicherheits-Backup** der aktuellen Datenbank
2. **Validierung** der Backup-Datei
3. **Datenbank-Restore** aus Backup
4. **Medien-Restore** (falls enthalten)
5. **Konsistenz-Prüfung**
6. **Rollback** bei Fehlern

---

## Multi-Instance-Setup

### Übersicht

Scandy unterstützt **parallele Instanzen** auf einem Server:

```
Server
├── scandy-main/          # Haupt-Instanz (Port 5000)
├── scandy-verwaltung/    # Verwaltung (Port 5001)
├── scandy-werkstatt/     # Werkstatt (Port 5002)
└── scandy-test/          # Test-Umgebung (Port 5003)
```

### Installation mehrerer Instanzen

#### Methode 1: Unified Installer
```bash
# Erste Instanz (Standard)
./install_unified.sh

# Weitere Instanzen mit Namen
./install_unified.sh -n verwaltung
./install_unified.sh -n werkstatt
./install_unified.sh -n test
```

#### Methode 2: Multi-Instance Installer
```bash
# Detaillierte Multi-Instance-Installation
./install_multi_instance.sh -n verwaltung -p 5001 -m 27018 -e 8082
./install_multi_instance.sh -n werkstatt -p 5002 -m 27019 -e 8083
```

### Port-Management

**Automatische Port-Berechnung:**
```
Instance "verwaltung":
- Web: 5000 + 1 = 5001
- MongoDB: 27017 + 1 = 27018
- Mongo Express: 8081 + 1 = 8082

Instance "werkstatt":
- Web: 5000 + 2 = 5002
- MongoDB: 27017 + 2 = 27019
- Mongo Express: 8081 + 2 = 8083
```

### Instance Management

Jede Instanz erhält ein eigenes `manage.sh` Skript:

```bash
# In der Instanz-Directory
./manage.sh start     # Instanz starten
./manage.sh stop      # Instanz stoppen
./manage.sh status    # Status prüfen
./manage.sh logs      # Logs anzeigen
./manage.sh backup    # Backup erstellen
./manage.sh update    # Update durchführen
./manage.sh shell     # Container-Shell
```

### Isolation

**Vollständige Trennung:**
- ✅ Separate Docker-Container
- ✅ Separate MongoDB-Instanzen
- ✅ Separate Volumes
- ✅ Separate Netzwerke
- ✅ Separate Backup-Verzeichnisse
- ✅ Separate Log-Dateien

---

## Deployment und Betrieb

### Produktionsumgebung

#### Docker-Compose Produktionskonfiguration
```yaml
services:
  scandy-app:
    image: scandy:production
    environment:
      - FLASK_ENV=production
      - SESSION_COOKIE_SECURE=true
      - REMEMBER_COOKIE_SECURE=true
    restart: unless-stopped
    
  scandy-mongodb:
    image: mongo:7
    restart: unless-stopped
    volumes:
      - mongodb_data:/data/db
    command: mongod --auth --bind_ip_all
```

#### Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name scandy.company.com;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### SSL/HTTPS Setup
```bash
# Let's Encrypt mit Certbot
sudo certbot --nginx -d scandy.company.com
```

### Monitoring und Logging

#### Health Checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

#### Log-Management
```python
# Strukturiertes Logging
loggers = {
    'app': logging.getLogger('scandy.app'),
    'db': logging.getLogger('scandy.database'),
    'auth': logging.getLogger('scandy.auth'),
    'backup': logging.getLogger('scandy.backup'),
    'errors': logging.getLogger('scandy.errors')
}
```

#### Performance-Monitoring
- **Response Time**: Durchschnittliche API-Antwortzeiten
- **Database Queries**: MongoDB-Performance-Metriken
- **Memory Usage**: Container-Speicherverbrauch
- **Disk Space**: Backup-Speicherplatz-Überwachung

### Wartung und Updates

#### Update-Prozess
```bash
# Automatisches Update (ohne Datenverlust)
./manage.sh update

# Oder manuell:
docker-compose down
docker-compose pull
docker-compose up -d --build
```

#### Datenbank-Wartung
```bash
# MongoDB-Performance optimieren
docker exec scandy-mongodb mongosh --eval "db.runCommand({compact: 'tools'})"

# Indizes neu aufbauen
docker exec scandy-mongodb mongosh --eval "db.tools.reIndex()"
```

#### Backup-Strategie für Produktion
```bash
# Tägliche Backups um 2:00 Uhr
0 2 * * * /path/to/scandy/manage.sh backup

# Wöchentliches Backup mit E-Mail-Versand
0 3 * * 0 /path/to/scandy/backup_and_mail.sh admin@company.com
```

---

## Entwicklung und Erweiterung

### Entwicklungsumgebung

#### Setup für Entwicklung
```bash
# Repository klonen
git clone [repo] scandy-dev
cd scandy-dev

# Python Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Entwicklungsmodus starten
export FLASK_ENV=development
export FLASK_DEBUG=1
python app/wsgi.py
```

#### Docker Development Setup
```yaml
# docker-compose.dev.yml
volumes:
  - ./app:/app/app:ro  # Read-only für Hot-Reload
  - ./requirements.txt:/app/requirements.txt:ro
```

### Code-Struktur für Erweiterungen

#### Neue Route hinzufügen
```python
# app/routes/new_feature.py
from flask import Blueprint, render_template
from app.utils.decorators import login_required

bp = Blueprint('new_feature', __name__, url_prefix='/new')

@bp.route('/')
@login_required
def index():
    return render_template('new_feature/index.html')

# In app/__init__.py registrieren:
from app.routes import new_feature
app.register_blueprint(new_feature.bp)
```

#### Neues Datenmodell
```python
# app/models/new_model.py
from app.models.mongodb_database import mongodb

class NewModel:
    COLLECTION_NAME = 'new_collection'
    
    @classmethod
    def create(cls, data):
        return mongodb.insert_one(cls.COLLECTION_NAME, data)
    
    @classmethod
    def get_by_id(cls, item_id):
        return mongodb.find_one(cls.COLLECTION_NAME, {'_id': item_id})
```

#### Frontend-Komponenten
```html
<!-- app/templates/components/new_component.html -->
<div class="card bg-base-100 shadow-xl">
    <div class="card-body">
        <h2 class="card-title">{{ title }}</h2>
        <p>{{ content }}</p>
        <div class="card-actions justify-end">
            <button class="btn btn-primary">Action</button>
        </div>
    </div>
</div>
```

### Testing

#### Unit Tests
```python
# tests/test_tools.py
import unittest
from app.models.mongodb_models import MongoDBTool

class TestTools(unittest.TestCase):
    def test_create_tool(self):
        tool_data = {
            'barcode': 'TEST001',
            'name': 'Test Tool',
            'category': 'Test'
        }
        tool_id = MongoDBTool.create(tool_data)
        self.assertIsNotNone(tool_id)
```

#### Integration Tests
```python
# tests/test_api.py
import unittest
from app import create_app

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
    
    def test_tools_api(self):
        response = self.client.get('/api/tools')
        self.assertEqual(response.status_code, 200)
```

### Performance-Optimierung

#### Datenbank-Optimierung
```python
# Indizes für neue Collections
db.new_collection.createIndex({ "field": 1 })
db.new_collection.createIndex({ "date_field": -1 })

# Aggregation Pipelines für komplexe Queries
pipeline = [
    {"$match": {"status": "active"}},
    {"$lookup": {"from": "related", "localField": "_id", "foreignField": "ref_id", "as": "related_data"}},
    {"$sort": {"created_at": -1}}
]
```

#### Caching
```python
# Flask-Caching für häufige Queries
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@cache.memoize(timeout=300)
def get_tool_statistics():
    # Teure Berechnung
    return statistics
```

---

## Troubleshooting

### Häufige Probleme

#### 1. Container startet nicht
```bash
# Logs prüfen
docker-compose logs -f scandy-app

# Container-Status
docker-compose ps

# Port-Konflikte prüfen
netstat -tulpn | grep :5000
```

#### 2. MongoDB-Verbindungsfehler
```bash
# MongoDB-Status prüfen
docker exec scandy-mongodb mongosh --eval "db.runCommand('ping')"

# Connection String validieren
echo $MONGODB_URI

# Authentifizierung testen
docker exec scandy-mongodb mongosh -u admin -p
```

#### 3. Backup-Probleme
```bash
# Speicherplatz prüfen
df -h

# Backup-Verzeichnis-Berechtigungen
ls -la backups/

# Backup-Logs prüfen
tail -f logs/backup.log
```

#### 4. Performance-Probleme
```bash
# Container-Ressourcen prüfen
docker stats

# MongoDB-Performance
docker exec scandy-mongodb mongosh --eval "db.runCommand({serverStatus: 1})"

# Slow Queries identifizieren
docker exec scandy-mongodb mongosh --eval "db.setProfilingLevel(2)"
```

### Fehlerbehebung

#### System-Reset
```bash
# Kompletter Neustart (Daten bleiben erhalten)
docker-compose down
docker-compose up -d

# Factory Reset (ACHTUNG: Alle Daten werden gelöscht!)
docker-compose down -v
docker volume prune -f
./install_unified.sh
```

#### Datenbank-Reparatur
```bash
# MongoDB-Reparatur
docker exec scandy-mongodb mongosh --eval "db.runCommand({repairDatabase: 1})"

# Konsistenz-Prüfung
python check_consistency.py

# Duplicate-Bereinigung
python fix_duplicates.py
```

#### Log-Analyse
```bash
# Alle Logs
docker-compose logs --tail=100

# Spezifische Services
docker-compose logs scandy-app
docker-compose logs scandy-mongodb

# Fehler-Logs filtern
docker-compose logs | grep ERROR
```

### Notfall-Wiederherstellung

#### Komplette Systemwiederherstellung
```bash
# 1. Backup aus anderem System
./manage.sh backup

# 2. System neu installieren
./install_unified.sh

# 3. Backup wiederherstellen
# Via Web-Interface: Admin → Backup → Upload & Restore
```

#### Datenbank-Migration
```bash
# Alte Datenbank exportieren
docker exec scandy-mongodb mongodump --out /backup

# In neue Installation importieren
docker exec scandy-mongodb mongorestore /backup
```

---

## Anhang

### Systemanforderungen (Detailliert)

#### Minimal-Setup
- **CPU**: 2 Kerne (2.0 GHz)
- **RAM**: 2 GB
- **Storage**: 5 GB SSD
- **Network**: 100 Mbit/s
- **Benutzer**: bis 10 gleichzeitig

#### Produktions-Setup
- **CPU**: 4 Kerne (2.5 GHz+)
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **Network**: 1 Gbit/s
- **Benutzer**: bis 100 gleichzeitig

#### Enterprise-Setup
- **CPU**: 8 Kerne (3.0 GHz+)
- **RAM**: 16 GB
- **Storage**: 100 GB NVMe
- **Network**: 10 Gbit/s
- **Benutzer**: 500+ gleichzeitig

### Changelog (Version Beta 0.8.1)

#### Neue Features
- ✅ **Vereinheitlichtes Backup-System** mit ZIP-Support
- ✅ **Job-Board-Modul** für Stellenausschreibungen
- ✅ **Medien-Upload-System** für alle Entitäten
- ✅ **Erweiterte Ticket-Historie** mit automatischem Logging
- ✅ **Multi-Instance-Installer** für parallele Installationen
- ✅ **Verbesserte Wochenberichte** mit PDF-Export
- ✅ **Konsistenz-Prüfung** und automatische Reparatur
- ✅ **Erweiterte API** mit neuen Endpunkten

#### Verbesserungen
- 🔧 **Performance-Optimierung** der Datenbankabfragen
- 🔧 **Verbesserte Fehlerbehandlung** mit detailliertem Logging
- 🔧 **Mobile Optimierung** des QuickScan-Interfaces
- 🔧 **Erweiterte Validierung** aller Eingaben
- 🔧 **Automatische Konfliktauflösung** bei Dateninkonsistenzen

#### Behobene Bugs
- 🐛 **Doppelte Tickets** nach Backup-Restore
- 🐛 **Ausleih-Inkonsistenzen** bei gleichzeitigen Zugriffen
- 🐛 **E-Mail-Versand-Probleme** mit bestimmten SMTP-Servern
- 🐛 **Berechtigungs-Bugs** bei Teilnehmer-Rolle

### Support und Community

#### Offizielle Kanäle
- **Dokumentation**: Diese Datei + `/docs` Verzeichnis
- **Issue Tracker**: GitHub Issues (falls verfügbar)
- **Entwickler**: Andreas Klann

#### Self-Service Debugging
```bash
# Debug-Modus aktivieren
export FLASK_DEBUG=1
export LOG_LEVEL=DEBUG

# Automatische Diagnose starten
python debug_system.py

# Systemprüfung
./manage.sh doctor
```

---

**Ende der Dokumentation**

*Diese Dokumentation wurde automatisch generiert basierend auf dem aktuellen Code-Stand von Scandy Version Beta 0.8.1 (Januar 2025). Für Updates und Erweiterungen dieser Dokumentation sollte sie entsprechend dem Code-Stand angepasst werden.*.syst