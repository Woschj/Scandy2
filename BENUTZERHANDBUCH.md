## Scandy – Benutzerhandbuch

Dieses Handbuch erklärt die Bedienung der Anwendung für Endanwender und Administratoren. Es beschreibt nur Funktionen, die tatsächlich in der App vorhanden sind.

### Zielgruppe und Überblick
- Für Anwender: Arbeiten mit Werkzeuge, Verbrauchsmaterial, Mitarbeitern und Tickets.
- Für Administratoren: Zusätzlich Verwaltung von Benutzern/Rollen, Abteilungen, Kategorien/Standorten, Feature-Einstellungen sowie Backups.

### Rollen und Berechtigungen
- Admin: Vollzugriff inkl. Systemeinstellungen, Benutzerverwaltung, Backups.
- Mitarbeiter: Arbeiten innerhalb der eigenen Abteilung, keine Systemeinstellungen.
- Anwender (Benutzer): Bearbeitung/Sicht in eigener Abteilung, keine Systemeinstellungen.
- Teilnehmer: Eigene Tickets sehen/erstellen, Jobbörse sehen (falls aktiv).

Hinweis: Sicht- und Bearbeitungsrechte sind abteilungsbezogen. Die Standard-Abteilung eines Benutzers steuert den Kontext.

---

## 1. Anmeldung und Navigation

### Anmelden/Abmelden
- Anmelden: Auf der Login-Seite Benutzernamen und Passwort eingeben.
- Abmelden: Über den Abmelden-Link im Menü.

### Grundlegende Bedienmuster
- Filter: Selektoren (z. B. Kategorie/Standort/Status) filtern Listen live.
- Suche: Suchfelder durchsuchen sichtbare Tabelleninhalte.
- Badges: zeigen Status (z. B. Verfügbar/Ausgeliehen/Defekt, Kritisch etc.).
- Aktionen: Kontextbuttons in Tabellenzeilen (Details, Bearbeiten, Löschen, Rückgabe).

---

## 2. Dashboard

Das Dashboard zeigt eine kompakte Übersicht:
- Werkzeuge: Gesamt, Verfügbar, Ausgeliehen, Defekt; ggf. Überfällig.
- Verbrauchsmaterial: Sufficient/Warnung/Kritisch.
- Mitarbeiter (rollenabhängig): Anzahl, Verteilung nach Abteilungen.
- Tickets: Offen, In Bearbeitung, Geschlossen.
- Warnungen: u. a. überfällige Ausleihen und kritische Bestände.
- Bestandsprognose (falls Daten vorhanden): Täglicher Verbrauch, Resttage.
- Mitteilungen: Informationskarten aus dem Admin-Bereich.

Tipp: Über die Warnhinweise gelangen Sie mit einem Klick zur gefilterten Liste (z. B. überfällige Werkzeuge).

---

## 3. Werkzeuge

### 3.1 Liste
- Aufruf: Werkzeuge-Übersicht.
- Filter: Kategorie, Standort, Status (Verfügbar/Ausgeliehen/Überfällig/Defekt).
- Aktionen pro Zeile: Details öffnen, Löschen in den Papierkorb (über Admin-Funktionen).

### 3.2 Anlegen
- Pflichtfelder: Name, Barcode, Kategorie, Standort, Status (Verfügbar/Defekt).
- Optionale Felder (sofern aktiviert): Seriennummer, Rechnungsnummer, MAC LAN/WLAN.
- Software-Management aktiv: Nutzergruppen- und Softwarezuordnung möglich.
- Benutzerdefinierte Felder: werden angezeigt, wenn im Admin konfiguriert.

### 3.3 Details und Bearbeiten
- Stammdaten anzeigen; Status-Kachel (Verfügbar/Ausgeliehen/Überfällig/Defekt).
- Bei Ausleihe: Anzeige „Ausgeliehen an“, Zeitraum und Überfälligkeit.
- Bearbeiten-Dialog: Stammdaten, optionale Felder, Software/Gruppen, benutzerdefinierte Felder.
- Barcode ändern: Über „Barcode ändern“ Dialog (führt zur aktualisierten Detailseite).

### 3.4 Medienverwaltung (Werkzeug)
- Medien hochladen (Bilder/PDFs), Liste und Galerie.
- Vorschaubild setzen (Stern), Löschen von Medien.
- PDF-Dateien können heruntergeladen werden.

### 3.5 Historie (Werkzeug)
- Ausleihhistorie tabellarisch: Ausgeliehen/Rückgabe, Mitarbeiter, Fälligkeitsinfos.

---

## 4. Verbrauchsmaterial

### 4.1 Liste
- Filter: Kategorie, Standort, Bestandsstatus (Niedrig/Normal etc.).
- Anzeige: Barcode, Name, Standort, Bestand (Kritisch/Genug/Nicht verfügbar).

### 4.2 Details/Anlegen/Bearbeiten
- Analog zu Werkzeugen, jedoch mit Fokus auf Bestandsinformation.
- Benutzerdefinierte Felder werden angezeigt, falls vorhanden.

---

## 5. Mitarbeiter

### 5.1 Liste
- Filter: Abteilung.
- Anzeige: Name, Barcode, Abteilung, E-Mail, verknüpfter Benutzer/ Rolle, aktive Ausleihen.

### 5.2 Details
- Stammdaten inkl. Benutzerkonto-Infos (Rolle/aktiv).
- Aktuelle Ausleihen: Werkzeuge mit Rückgabe-Button.
- Ausleihhistorie: Werkzeuge und Verbrauchsmaterial mit Datum/Status.
- Aktionen: Ausweis (Karte) öffnen, Bearbeiten, Löschen (Papierkorb, falls keine aktiven Ausleihen).

---

## 6. Ausleihe & Rückgabe

### 6.1 Manuelle Ausleihe
Schrittfolge auf der Seite „Manuelle Ausleihe“:
1) Artikel wählen: Tab „Werkzeuge“ oder „Verbrauchsmaterial“; per Suchfeld filtern.
2) Mitarbeiter wählen: Liste mit Suchfeld.
3) Zusammenfassung prüfen; für Verbrauchsmaterial Menge eingeben.
4) „Ausleihe bestätigen“ – erzeugt eine Ausleihe (Werkzeug) oder eine Ausgabe (Verbrauchsmaterial).

Tabelle „Aktuelle Ausleihen“ darunter:
- Filtern nach Kategorie, Suche.
- Werkzeuge können direkt zurückgegeben werden.

### 6.2 Rückgabe außerhalb der Seite
- Rückgabe-Button in Mitarbeiter-Details (bei aktiven Ausleihen).
- Rückgabe-Aktionen im Admin-Dashboard (falls eingeblendet).

---

## 7. Tickets (Arbeitsaufträge)

### 8.1 Übersicht
- Tabs: Offene, Zugewiesene/Meine & Abgeschlossene, optional Alle.
- Globale Filter: Suche (Titel/ID/Beschreibung), Status, Priorität, Kategorie (Handlungsfelder).

### 8.2 Erstellen
- Erstellen-Formular (sofern verfügbar) mit Titel, Beschreibung, Kategorie etc.

### 8.3 Detailansicht
- Kopf: Ticketnummer, Titel, Beschreibung, Status-Badge, Verantwortliche Person (falls gesetzt).
- Metadaten: Erstellt von, Zuweisungen, Priorität, Kategorie, Erstellung, Fälligkeit.
- Aktionen (rollen-/verantwortlichenabhängig):
  - Status ändern (Offen/In Arbeit/Wartend/Abgeschlossen/Abgebrochen).
  - Zuweisungen ändern (Mehrfachauswahl) und speichern.
  - Verantwortliche Person setzen.
  - Kategorie, geschätzte Zeit, Fälligkeit speichern.
- Nachrichten: Schreiben, Verlauf wird geladen und angezeigt.
- Medien: Upload, Vorschau/Galerie, PDF-Download, Löschen.
- Export: Word-Export des Tickets (Download-Link).
- Historie: Paginierter Änderungsverlauf, „Mehr laden“ bei Bedarf.

---

## 8. Medienverwaltung (kontextbezogen)

### 9.1 Werkzeuge
- Upload (Bild/PDF), Vorschau-Kacheln, Galerie.
- Vorschaubild setzen (Sternsymbol) – wird in Listen verwendet.
- Medien löschen, PDFs herunterladen.

### 9.2 Tickets
- Upload (Bild/PDF), Galerie mit Thumbnails.
- Medien löschen, PDFs herunterladen.

---

## 9. Admin-Bereich

### 10.1 Benutzerverwaltung
- Liste mit Suche, Filtern (Rolle, Abteilung), Sortierung.
- Benutzer anlegen/bearbeiten:
  - Pflicht: Benutzername, Rolle.
  - Optional: E-Mail, Vor-/Nachname, Passwort (beim Anlegen leer = automatisches sicheres Passwort).
  - Optionen: Konto aktiv, Ablaufdatum, Wochenplan- und Kantinenplan-Rechte.
  - Abteilungen: Mehrfachzuordnung; Standard-Abteilung wählen.
  - Handlungsfelder: Sicht-/Bearbeitungsbereiche für Tickets zuweisen.
- Aktionen: Bearbeiten, in Papierkorb verschieben (endgültiges Löschen erfolgt über Papierkorb-Mechanismen).

### 10.2 Rollen & Berechtigungen
- Übersicht von Bereichen/Aktionen pro Rolle.
- Admin-Rechte sind fest; andere Rollen je nach Bereich konfigurierbar (sofern freigeschaltet).

### 10.3 Feature-Einstellungen
- Pro Abteilung Features schalten: Ticketsystem, Software-Management, Jobbörse, Wochenberichte, Kantinenplan.
- Feldverwaltung: Verweis auf zentrale Seite zum Aktivieren/Deaktivieren von Standardfeldern und Erstellen benutzerdefinierter Felder für Werkzeuge/Verbrauchsgüter.

### 10.4 Abteilungen, Kategorien, Standorte, Handlungsfelder
- Abteilungen: Anlegen, Umbenennen, Löschen (Achtung: Löschen entfernt alle zugehörigen Daten der Abteilung).
- Kategorien/Standorte: Verwaltung über Admin-Dashboard/Systembereich.
- Handlungsfelder (Ticket-Kategorien): werden Nutzern zugewiesen und steuern deren Ticket-Sichtbarkeit.

### 10.5 Backups
- Automatisches Backup-System:
  - Status: Aktiv/Gestoppt; nächste Backups; wöchentliches Archiv (Freitag).
  - Steuerung: Starten/Stoppen; Status/Logs aktualisieren; „Backup jetzt versenden“ (wöchentliches ZIP per E-Mail, Größenlimit beachten).
  - Konfiguration: tägliche Backup-Zeiten, wöchentliche Uhrzeit, E-Mail-Adresse für Versand.
  - Logs: im UI einsehbar.
- JSON-Import:
  - Altes JSON-Backup hochladen und einer Ziel-Abteilung zuweisen.

---

## 10. Kantinenplan und Jobbörse (optional)

- Kantinenplan: Bei aktivem Feature können berechtigte Benutzer Mahlzeiten verwalten/sehen.
- Jobbörse: Bei aktivem Feature werden Stellenangebote und Jobverwaltung sichtbar.

---

## 11. Tipps & Fehlerbehebung

### 12.1 Barcodes und Duplikate
- Halten Sie Barcodes eindeutig. Das Dashboard warnt bei Duplikaten.
- Barcode-Änderungen sind im Werkzeug-Detail verfügbar.

### 11.2 Berechtigungen
- Prüfen Sie Abteilung und Rolle, wenn Bereiche/Schaltflächen fehlen.
- Feature-Schalter pro Abteilung beeinflussen Felder und Masken.

### 11.3 Backups
- Prüfen Sie Status/Logs bei E-Mail-Problemen (Größenlimit beachten).
- Testversand des wöchentlichen Archivs hilft bei der Diagnose.

---

## 12. Glossar
- Abteilung: Datenraum; filtert Sicht und Aktionen.
- Handlungsfeld: Ticket-Kategorie zur Steuerung der Sichtbarkeit.
- Vorschaubild: Markiertes Medienbild eines Werkzeugs für Listenansichten.
- Ausgabe (Verbrauchsmaterial): Mengengesteuerte Entnahme aus dem Bestand.

---

## 13. Kurzübersicht Aufgaben
- Werkzeuge/Verbrauchsmaterial anlegen, filtern, bearbeiten, Medien verwalten.
- Mitarbeiter verwalten, Ausleihen einsehen und Rückgabe durchführen.
- Manuelle Ausleihe für Buchungen.
- Tickets erstellen, filtern, bearbeiten, Medien/Nachrichten, Export.
- Admin: Benutzer/Rollen, Abteilungen, Kategorien/Standorte, Features/Felder, Backups.

