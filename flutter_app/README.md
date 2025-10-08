# Scandy Desktop - Flutter Windows App

Eine native Windows-Desktop-Anwendung für die Verwaltung von Werkzeugen, Verbrauchsmaterialien und Mitarbeitern.

## Features

- **Werkzeugverwaltung**: Vollständige CRUD-Operationen für Werkzeuge
- **Mitarbeiterverwaltung**: Verwaltung von Mitarbeiterdaten und Abteilungen
- **Verbrauchsmaterial-Management**: Bestandsverfolgung und Verbrauchserfassung
- **Ausleihsystem**: Werkzeug-Ausleihe und -Rückgabe
- **Ticket-System**: Aufgaben- und Problemverfolgung
- **Barcode-Scanner**: Quick-Scan für schnelle Operationen
- **Dashboard**: Übersichtliche Statistiken und Schnellzugriff
- **SQLite-Datenbank**: Lokale Datenbank ohne Server-Abhängigkeiten

## Technologie-Stack

- **Flutter**: Cross-Platform UI Framework
- **SQLite**: Lokale Datenbank
- **Provider**: State Management
- **GoRouter**: Navigation
- **Material Design**: Moderne UI-Komponenten

## Installation

### Voraussetzungen

- Flutter SDK (3.10.0 oder höher)
- Visual Studio 2022 mit C++-Entwicklungstools
- Windows 10/11

### Build-Anweisungen

1. **Flutter SDK installieren**
   ```bash
   # Flutter SDK von https://flutter.dev herunterladen
   # PATH-Variable setzen
   flutter doctor
   ```

2. **Projekt klonen und Abhängigkeiten installieren**
   ```bash
   cd flutter_app
   flutter pub get
   ```

3. **Windows-Build erstellen**
   ```bash
   flutter build windows --release
   ```

4. **Anwendung starten**
   ```bash
   flutter run -d windows
   ```

## Verwendung

### Erste Schritte

1. **Anmeldung**: Verwenden Sie die Demo-Zugangsdaten:
   - Benutzername: `admin`
   - Passwort: `admin`

2. **Daten hinzufügen**:
   - Werkzeuge über "Werkzeuge" → "Hinzufügen"
   - Mitarbeiter über "Mitarbeiter" → "Hinzufügen"
   - Verbrauchsmaterial über "Verbrauchsmaterial" → "Hinzufügen"

3. **Quick Scan verwenden**:
   - Barcode-Scanner für schnelle Operationen
   - Automatische Erkennung von Werkzeugen, Mitarbeitern und Verbrauchsmaterial

### Hauptfunktionen

#### Dashboard
- Übersichtliche Statistiken
- Schnellzugriff auf alle Module
- Aktuelle Ausleihen und Warnungen

#### Werkzeugverwaltung
- Vollständige Werkzeugdaten mit technischen Details
- Barcode-Generierung und -Verwaltung
- Status-Tracking (Verfügbar, Ausgeliehen, Defekt, Wartung)
- Kategorisierung und Standortverwaltung

#### Mitarbeiterverwaltung
- Mitarbeiterdaten mit Kontaktinformationen
- Abteilungszuordnung
- Barcode-basierte Identifikation

#### Verbrauchsmaterial
- Bestandsverfolgung mit Mindestbeständen
- Verbrauchserfassung
- Nachbestellwarnungen
- Kategorisierung

#### Ausleihsystem
- Werkzeug-Ausleihe an Mitarbeiter
- Rückgabe-Verwaltung
- Überfälligkeits-Tracking
- Ausleihhistorie

#### Ticket-System
- Aufgaben- und Problemverfolgung
- Prioritäts- und Status-Management
- Kategorisierung
- Zuweisung an Mitarbeiter

## Datenbank

Die Anwendung verwendet SQLite als lokale Datenbank. Die Datenbank wird automatisch erstellt und initialisiert beim ersten Start.

### Datenbank-Schema

- **users**: Benutzer und Authentifizierung
- **tools**: Werkzeugdaten
- **workers**: Mitarbeiterdaten
- **consumables**: Verbrauchsmaterialdaten
- **lendings**: Ausleihverwaltung
- **tickets**: Ticket-System
- **settings**: Anwendungseinstellungen

## Entwicklung

### Projekt-Struktur

```
lib/
├── main.dart                 # App-Einstiegspunkt
├── models/                   # Datenmodelle
├── providers/                # State Management
├── screens/                  # UI-Screens
├── widgets/                  # Wiederverwendbare Widgets
└── utils/                    # Hilfsfunktionen
```

### State Management

Die App verwendet Provider für State Management:
- `DatabaseProvider`: Datenbankoperationen
- `AuthProvider`: Authentifizierung
- `ToolsProvider`: Werkzeugverwaltung
- `WorkersProvider`: Mitarbeiterverwaltung
- `ConsumablesProvider`: Verbrauchsmaterialverwaltung
- `LendingProvider`: Ausleihsystem
- `TicketsProvider`: Ticket-System
- `DashboardProvider`: Dashboard-Statistiken

### Navigation

GoRouter wird für die Navigation verwendet:
- `/login`: Anmeldung
- `/dashboard`: Hauptübersicht
- `/tools`: Werkzeugverwaltung
- `/workers`: Mitarbeiterverwaltung
- `/consumables`: Verbrauchsmaterialverwaltung
- `/lending`: Ausleihsystem
- `/tickets`: Ticket-System
- `/quick-scan`: Barcode-Scanner

## Build und Deployment

### Release-Build

```bash
flutter build windows --release
```

Die kompilierte Anwendung befindet sich in `build/windows/runner/Release/`.

### Installer erstellen

Für eine einfache Installation können Sie ein Installer-Paket erstellen:

1. **NSIS verwenden** (empfohlen)
2. **Inno Setup verwenden**
3. **Windows App Packaging Project verwenden**

### Portierung zu anderen Plattformen

Die App kann einfach zu anderen Plattformen portiert werden:

- **macOS**: `flutter build macos`
- **Linux**: `flutter build linux`
- **Web**: `flutter build web`

## Troubleshooting

### Häufige Probleme

1. **Flutter Doctor Issues**
   ```bash
   flutter doctor -v
   ```

2. **Build-Fehler**
   - Visual Studio 2022 mit C++-Tools installieren
   - Windows SDK installieren
   - Flutter SDK aktualisieren

3. **Datenbank-Fehler**
   - App als Administrator ausführen
   - Schreibrechte prüfen

### Logs

Die Anwendung erstellt Logs in:
- Windows Event Log
- Console Output (Debug-Modus)

## Lizenz

MIT License - siehe LICENSE-Datei für Details.

## Support

Bei Problemen oder Fragen:
1. GitHub Issues erstellen
2. Dokumentation prüfen
3. Flutter Community konsultieren
