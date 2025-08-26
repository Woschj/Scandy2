### Scandy – Codebase-Index

Stand: aktuell (aus Code gescannt)

## Struktur (Top-Level)
- `app/`: Hauptanwendung
  - `__init__.py`: App-Factory, Registrierung, Middleware, Healthcheck
  - `routes/`: Blueprints (auth, admin, tools, consumables, lending, tickets, api, media, backup, jobs, dashboard, main, setup, history, quick_scan, ticket_history, canteen, mobile)
  - `models/`: MongoDB-Zugriff (`mongodb_database.py` – Adapter/Scoping/CRUD, `mongodb_models.py` – Modelle), `user.py`, `tool.py`, `experience.py`
  - `utils/`: Auth/Permissions, Backup, Email, Logger, Filter, Context-Processor, Version-Checker, Auto-Backup u. a.
  - `services/`: Business-Logik (z. B. lending_service, statistics_service, ticket_service, job_service, admin_backup_service)
  - `templates/`: Jinja2-Templates (auth, admin, dashboard, tools, consumables, tickets, workers, jobs, components, errors)
  - `static/`: JS/CSS/Images (Tailwind/DaisyUI; JS u. a. admin-dashboard.js, quickscan.js etc.)
  - `config/`: Konfiguration (`config.py`, `version.py`), `constants.py`
- `requirements.txt`, `package.json`, `Dockerfile`, `Dockerfile.production`, `docker-compose.https.yml`
- `README.md`, `README_UNIFIED_INSTALLER.md`, `SCANDY_VOLLSTAENDIGE_DOKUMENTATION.md`
- `backups/`, `logs/`, `data/`, `mongo-init/`

## Einstiegspunkte
- WSGI: `app/wsgi.py` (von Gunicorn gestartet), App-Factory: `app.__init__.create_app()`
- Health: GET `/health` (DB-Ping, Status JSON)

## Wichtige Blueprints
- `auth` (`/auth`): Login/Logout, Setup, Profil, Session-Fixes
- `admin` (`/admin`): Benutzer/ Rollen, Einstellungen, Debug/Tools
- `api` (`/api`): JSON-APIs (Tools/Workers/Consumables, Quickscan, Notices, Forecast)
- `backup` (`/backup`): Create/List/Restore/Upload/Download/Delete/Test/Info
- `tickets` (`/tickets`): Ticket-UI; `ticket_history_routes` (API-Historie)
- `tools`, `consumables`, `lending`, `workers`, `jobs`, `media`, `dashboard`, `main`, `setup`, `history`, `quick_scan`, `canteen`, `mobile`

## Datenzugriff
- `app.models.mongodb_database.MongoDBDatabase` (Singleton):
  - Verbindet per `MONGODB_URI`, setzt `authSource=admin` bei Bedarf
  - CRUD (`find_one`, `find`, `insert_one`, `update_one`, `update_many`, `delete_*`, `aggregate`, `distinct`, `create_index`)
  - Department-Scoping via `g.current_department`
  - ID-Konvertierung: `_process_filter_ids` (String to ObjectId), Rückgabe-IDs als String

## Sicherheit
- CSRF aktiv (`flask_wtf`), Session über `Flask-Session` (filesystem)
- Role-Checks: `app.utils.decorators` und `app.utils.permissions` (Matrix + Overrides in `settings`)
- Rate-Limits (`flask_limiter`) global initialisiert
- Talisman/Compress/Logger konfiguriert

## Backup-System
- Unified: `app.utils.unified_backup_manager` – ZIP-Backups inkl. DB/Medien/Config; JSON-Import Fallback
- Routen: `app.routes.backup_routes`

## Frontend
- Tailwind/DaisyUI (via `package.json` Scripts), JS unter `app/static/js/*`

## Deployment
- Dockerfiles vorhanden; `docker-compose.https.yml` (Self-SSL), Healthchecks

Hinweise: Detaillierte Prozess-/Modulbeschreibungen siehe `SCANDY_VOLLSTAENDIGE_DOKUMENTATION.md`.
