### Scandy – Fehlerbericht zur Codeprüfung

Stand: aktuell (aus Quellcode gescannt)

Wichtig: Dieser Bericht priorisiert sicherheitsrelevante Punkte, Stabilität und Wartbarkeit. Fundstellen sind anhand von Datei(en) und näherem Kontext benannt. Korrekturen sollten in einem eigenen Branch erfolgen und getestet werden.

## A. Sicherheit
- Unsichere Beispiel-/Default-Credentials in Beispielen/Compose
  - Datei: `docker-compose.https.yml`
    - Enthält echte Beispiel-`MONGODB_URI`, `SECRET_KEY` sowie Mongo-Root-Passwort im Klartext.
    - Empfehlung: Diese Werte ausschließlich aus `.env` laden; Beispielwerte maskieren. Compose-Datei auf Placeholder umstellen oder per `env_file` einbinden.
  - Datei: `env.example`
    - Enthält Beispielpasswörter als Klartext. Ist okay als Vorlage, aber deutliche Warnhinweise sind vorhanden. Empfehlung: Placeholder (z. B. `CHANGE_ME`) statt realistisch wirkender Werte.

- Notfall-/Debug-Routen zugangsbeschränkt halten
  - Datei: `app/routes/main.py` → Route `/emergency-admin`
    - Erstellt Admin-Konto mit festem Username `admin` und Standardpasswort-Hinweis.
    - Risiko: Wenn nicht hinreichend abgeschirmt (z. B. durch ENV-Flag, interne Netze), kann das in Produktion missbraucht werden.
    - Empfehlung: Route komplett entfernen oder durch ENV-Flag schützen (z. B. `ENABLE_EMERGENCY_ADMIN=false`) und zusätzlich IP-Range/Token absichern.

- Passwortbehandlung und Hash-Kompatibilität
  - Datei: `app/utils/auth_utils.py` → `check_password_compatible`
    - Unterstützt werkzeug, bcrypt und scrypt. In `check_scrypt_password` gibt es permissiven Fallback:
      - Wenn Exception, wird für bestimmte Passwörter (`admin123`, `password`, `test`) `True` zurückgegeben.
      - Sehr kritisch: Erlaubt ggf. Login bei Fehlern.
    - Empfehlung: Den Fallback vollständig entfernen. Bei Fehlern strikt `False` zurückgeben und Migrationspfad dokumentieren.

- CSRF/Session
  - Global aktiv, gut. Prüfen, dass API-Endpoints mit State-Änderungen nur mit Session-/Rollenprüfungen erreichbar sind (weitgehend erfüllt).

## B. Stabilität/Fehlerbehandlung
- Breite `except:`-Blöcke
  - Zahlreiche Stellen mit nacktem `except:` (ohne Exception-Typ), z. B.:
    - `app/routes/admin.py`, `app/routes/workers.py`, `app/routes/tickets.py`, `app/models/mongodb_models.py`, `app/utils/unified_backup_manager.py`, u. a.
  - Risiko: Verbirgt unerwartete Fehler, erschwert Debugging.
  - Empfehlung: Konkrete Exception-Typen verwenden (z. B. `Exception as e` ist Minimum), loggen und gezielt behandeln.

- Logging in Login-Lifecycle
  - Datei: `app/__init__.py` → `login_manager.user_loader`
    - Enthält viele `print`-Statements und ausführliche Debug-Ausgaben (inkl. Auflistung aller User-IDs). In Produktion unerwünscht.
  - Empfehlung: Auf strukturiertes Logging umstellen, sensible Daten maskieren, Debug-Ausgaben nur im Debug-Modus.

- Department-Scoping
  - Datei: `app/models/mongodb_database.py`
    - Scoping-Mechanik ist vorhanden und robust. Prüfen, ob alle Collections konsistent in `_SCOPED_COLLECTIONS` gelistet sind (z. B. `consumable_usages` vs. `consumable_usage`).
  - Empfehlung: Einheitliche Benennung verwenden und Liste gegen tatsächliche Collections abgleichen.

## C. Konfiguration/Deployment
- DEBUG in `config`
  - Datei: `app/config/config.py` meldet `DEBUG = True` in Konfigklassen (Fundstelle via Suche).
  - Empfehlung: In Produktion sicherstellen, dass `FLASK_ENV=production` und `DEBUG=False` gesetzt sind. Konfigurationsableitung strikt über ENV.

- Dockerfiles
  - Node/NPM im App-Container installiert – ok für Build, in Produktion ggf. Mehrstufigen Build verwenden und Runtime-Image schlank halten.
  - Empfehlung: Multi-stage Docker Build einführen (Builder → Runtime), `npm ci`, feste Versionen/Lockfiles.

## D. API/Validierung
- `app/routes/api.py` → Endpunkte wie `/api/inventory/*`, `/api/notices/*`
  - Meist solide Validierung, Logging vorhanden. Prüfen, dass alle schreibenden Endpunkte Rollen-Decorators haben (in Beispielen vorhanden).
  - Empfehlung: Einheitliche Fehlerobjekte und Statuscodes; Payload-Schema validieren (Marshmallow/Pydantic optional).

## E. Backup-System
- `app/utils/unified_backup_manager.py`
  - Nutzt `mongodump` via `subprocess.run` mit Timeout; Fallback auf Python-Export. Solide, aber: breite `except:` im Modul vorhanden.
  - Medien-Backup: Abbruch bei Max-Größe; nimmt erstes gefundenes Medienverzeichnis. Dokumentieren/konfigurierbar machen.
  - Empfehlung: Rückgabewerte/Fehlerfälle stärker typisieren und durchtesten; Pfade/Größen per ENV konfigurierbar machen.

## F. Sonstiges
- TODOs offen
  - `app/services/consumable_service.py` L191: TODO aktuellen Benutzer verwenden.
  - `app/templates/admin/server-settings.html` (JS): TODO Edit-Modal.
  - Empfehlung: Tickets/Issues anlegen, Priorisierung abstimmen.

- Sensible Werte in Doku
  - `SCANDY_VOLLSTAENDIGE_DOKUMENTATION.md` enthält Beispiel-URIs und Hinweise auf Passwörter als Platzhalter – ok, aber sicherstellen, dass diese nicht mit Produktivwerten verwechselt werden.

## G. Konkrete Fix-Vorschläge (Kurzliste)
1) Entferne permissiven Passwort-Fallback in `check_scrypt_password` (erledigt).
2) Schütze/entferne `/emergency-admin` hinter ENV-Flag; in Produktion deaktivieren. (erledigt; `ENABLE_EMERGENCY_ADMIN=false` default)
3) Ersetze alle nackten `except:` durch `except Exception as e:` mit Logging; wo möglich spezifische Exceptions.
4) Reduziere Debug-`print` in `user_loader`, nutze Logger und Debug-Flag.
5) Ersetze Klartext-Secret/Passwörter in `docker-compose.https.yml` durch `.env`-Variablen. (erledigt; `env_file: .env` + Variablen)
6) Setze `DEBUG=False` für Produktion in `config` und kontrolliere via ENV.
7) Optional: Multi-stage Docker Build, Lockfiles (`package-lock.json`/`pip` constraints), Security-Scans in CI.

Ende des Berichts.
