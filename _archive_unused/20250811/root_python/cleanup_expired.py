#!/usr/bin/env python3
"""
Automatische Bereinigung abgelaufener Benutzer und Jobs

Dieses Script kann als Cron-Job ausgeführt werden, um regelmäßig abgelaufene Daten zu bereinigen.
"""

import os
import sys
import logging
from datetime import datetime

# Füge das Projektverzeichnis zum Python-Pfad hinzu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Flask-App importieren
from app import create_app
# Altes CleanupService entfällt. Einfaches Skript für delete_at-basierte Bereinigung.

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cleanup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Hauptfunktion für die automatische Bereinigung via TTL/Backstop"""
    try:
        logger.info("Starte automatische Bereinigung abgelaufener Benutzer (delete_at)...")

        app = create_app()
        with app.app_context():
            from app.models.mongodb_database import mongodb
            from datetime import datetime

            now = datetime.now()
            # Hartes Löschen alter Nutzer als Backstop, falls TTL-Index (delete_at) noch nicht greift
            deleted_users = mongodb.delete_many('users', {'delete_at': {'$lte': now}})
            # Zugehörige Worker ebenfalls löschen (Soft Delete, falls gewünscht hart löschen)
            # Hier: harte Löschung falls delete_at erreicht
            deleted_workers = mongodb.delete_many('workers', {'delete_at': {'$lte': now}})

            total = deleted_users + deleted_workers
            logger.info(f"Bereinigung abgeschlossen: users={deleted_users}, workers={deleted_workers}, total={total}")
            return 0
    except Exception as e:
        logger.error(f"Kritischer Fehler bei der Bereinigung: {e}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code) 