### Scandy – Bedienungsanleitung (Endanwender & Admin)

Version: 1.0 (aus Codebasis generiert)

- Zielgruppe: Admins, Mitarbeiter, Anwender, Teilnehmer
- Systeme: Flask/MongoDB, Docker empfohlen

## 1. Schnellstart
- Installation (Standard):
  - Im Projekt: `chmod +x install_unified.sh && ./install_unified.sh`
  - App: http://localhost:5000, MongoDB: 27017, Mongo Express: 8081
- Erstkonfiguration:
  - Aufruf http://localhost:5000 → Setup-Assistent (Admin anlegen)
  - Alternativ: vorhandenes Admin-Konto nutzen
- Nach Erststart:
  - `.env` prüfen, Passwörter/`SECRET_KEY` ändern
  - Admin-Einstellungen prüfen, Backup aktivieren

## 2. Rollen & Anmeldung
- Login: `/auth/login`
- Rollen:
  - Admin: Vollzugriff (Benutzer, Rollen, Backup, Einstellungen)
  - Mitarbeiter: Werkzeuge/Verbrauchsmaterial/Tickets verwalten
  - Anwender: Eigene Inhalte, eingeschränkte Verwaltung
  - Teilnehmer: Wochenberichte/Tickets (sehr eingeschränkt)

## 3. Hauptbereiche
- Startseite/Dashboard: Kennzahlen, Warnungen
- Werkzeuge (`/tools`): Bestand, Barcode, Status, Historie
- Verbrauchsmaterial (`/consumables`): Bestände, Mindestmengen, Prognose
- Ausleihe (`/lending`, QuickScan): Ausleihe/Rückgabe per Barcode
- Tickets (`/tickets`): Aufgaben/Aufträge, Statusworkflow, Nachrichten, Dateien
- Jobs (optional, `/jobs`): Stellenausschreibungen
- Medien (`/media`): Upload/Verwaltung
- Admin (`/admin`): Benutzer, Rollen, Einstellungen, E-Mail, Backup/Restore

## 4. Werkzeuge – tägliche Nutzung
- Anlegen: Werkzeuge → „Neu“ → speichern
- Barcode: Generieren/Drucken über Admin- bzw. Detailansicht
- Status: In den Werkzeugdetails ändern (verfügbar/ausgeliehen/defekt/Wartung)
- Historie: Alle Änderungen/Ausleihen einsehbar

## 5. Verbrauchsmaterial – Bestände
- Anlegen/Bearbeiten: Bereich „Verbrauchsmaterial“
- Bestand anpassen: „Bestand anpassen“ (positiv/negativ)
- Prognose: Detailseite → „Prognose“ (30-Tage-Basis)

## 6. Ausleihe & Rückgabe
- Manuell (Adminbereich): Werkzeug + Mitarbeiter auswählen → „Ausleihen“
- QuickScan (Touch):
  - 1) Mitarbeiter scannen
  - 2) Werkzeug/Artikel scannen
  - 3) Bestätigen → Ausleihe/Rückgabe

## 7. Tickets
- Erstellen: Tickets → „Neu“
- Workflow: offen → zugewiesen → in_bearbeitung → gelöst → geschlossen
- Nachrichten/Dateien: Im Ticketverlauf hinzufügen
- Historie: Vollständige Nachverfolgung pro Ticket

## 8. Medien
- Uploads an Entitäten (Bilder/Dokumente)
- Typische Limits: 10 MB/Datei, max. 10 Dateien/Eintrag

## 9. Dashboard & Berichte
- Übersicht, Mindestbestand-Warnungen, überfällige Ausleihen
- Duplikat-Hinweise und Auffälligkeiten

## 10. Adminbereich
- Benutzerverwaltung: anlegen/bearbeiten, Passwort zurücksetzen
- Rollenrechte: pro Bereich/Aktion verfeinern
- Einstellungen:
  - Labels/Symbole (Tools/Consumables/Tickets)
  - Farben (Admin → Einstellungen → Farben)
  - E-Mail (SMTP) konfigurieren und testen
- Backup/Restore:
  - Backup erstellen (optional mit Medien)
  - Backups auflisten/downloaden/löschen
  - Wiederherstellen (inkl. Medien optional)

## 11. Backups – Empfehlungen
- Automatisieren (Cron/`manage.sh backup`)
- Regelmäßig Test-Restore
- Rotation: täglich 7, wöchentlich 4, monatlich 12

## 12. Mobile & QuickScan
- `/mobile/quickscan`: große Buttons, Scanner-kompatibel (Kamera/USB)

## 13. API – Kurzüberblick
- Werkzeuge: GET `/api/tools`, GET `/api/tools/<barcode>`, POST/PUT/DELETE
- Ausleihe: POST `/api/lending/process`, POST `/api/lending/return`
- Tickets: GET/POST `/api/tickets`, GET/PUT `/api/tickets/<id>`
- Backup: POST `/backup/create`, GET `/backup/list`, POST `/backup/restore`
- Auth: sessionbasiert, CSRF aktiv; Berechtigungen nach Rolle

## 14. Sicherheit – Hinweise
- Alle Standardpasswörter ändern (Mongo/Admin/Email/`SECRET_KEY`)
- HTTPS aktivieren (Proxy oder Container)
- Rollenrechte prüfen; Debug-/Notfallrouten in Produktion deaktivieren
- Regelmäßige Updates/Abhängigkeitspflege

## 15. Troubleshooting (Kurz)
- App startet nicht: Logs (`docker-compose logs scandy-app`), `/health`
- Mongo-Fehler: Container-Status, `mongosh --eval "db.adminCommand('ping')"`
- Login-Probleme: `/auth/fix-session` und Browser-Cookies löschen
- Backup-Fehler: Speicher/Dateirechte prüfen, `logs/backup.log`

## 16. Multi-Instance (optional)
- Weitere Instanz: `./install_unified.sh -n verwaltung` (Ports automatisch)
- Eigene Volumes/Netzwerke je Instanz, eigenes `manage.sh`

## 17. Pflege & Updates
- Update: `./manage.sh update` oder Docker-Images neu bauen/pullen
- Indizes/Datenbank regelmäßig prüfen

## 18. Anhang
- Empfehlungen: 4 CPU, 4–8 GB RAM, SSD
- Stack: Flask 3, MongoDB 7, Gunicorn, Tailwind + DaisyUI
