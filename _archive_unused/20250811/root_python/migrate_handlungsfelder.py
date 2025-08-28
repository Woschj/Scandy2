#!/usr/bin/env python3
"""
Migrationsskript für Handlungsfelder
Stellt sicher, dass alle Benutzer das handlungsfelder Feld haben
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.mongodb_database import mongodb
from app.utils.database_helpers import get_ticket_categories_from_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_handlungsfelder():
    """Migriert alte Benutzerdaten für Handlungsfelder"""
    try:
        logger.info("Starte Handlungsfeld-Migration...")
        
        # Hole alle Benutzer
        users = list(mongodb.find('users', {}))
        logger.info(f"Gefundene Benutzer: {len(users)}")
        
        migrated_count = 0
        
        for user in users:
            user_id = user['_id']
            
            # Prüfe ob handlungsfelder Feld fehlt
            if 'handlungsfelder' not in user:
                logger.info(f"Migriere Benutzer: {user.get('username', 'Unknown')} (ID: {user_id})")
                
                # Setze Standard-Handlungsfelder basierend auf Rolle
                default_handlungsfelder = []
                
                if user.get('role') in ['admin', 'mitarbeiter']:
                    # Admins und Mitarbeiter bekommen alle Handlungsfelder
                    default_handlungsfelder = get_ticket_categories_from_settings()
                else:
                    # Andere Benutzer bekommen keine Handlungsfelder (sehen alle Tickets)
                    default_handlungsfelder = []
                
                # Aktualisiere Benutzer
                mongodb.update_one('users', {'_id': user_id}, {
                    '$set': {'handlungsfelder': default_handlungsfelder}
                })
                
                migrated_count += 1
                logger.info(f"  → Handlungsfelder gesetzt: {default_handlungsfelder}")
        
        logger.info(f"Migration abgeschlossen! {migrated_count} Benutzer migriert.")
        return True
        
    except Exception as e:
        logger.error(f"Fehler bei der Migration: {str(e)}")
        return False

def check_handlungsfelder():
    """Prüft den Status der Handlungsfeld-Migration"""
    try:
        logger.info("Prüfe Handlungsfeld-Status...")
        
        # Hole alle Benutzer
        users = list(mongodb.find('users', {}))
        
        users_with_handlungsfelder = 0
        users_without_handlungsfelder = 0
        
        for user in users:
            if 'handlungsfelder' in user:
                users_with_handlungsfelder += 1
                logger.info(f"✓ {user.get('username', 'Unknown')}: {len(user.get('handlungsfelder', []))} Handlungsfelder")
            else:
                users_without_handlungsfelder += 1
                logger.warning(f"✗ {user.get('username', 'Unknown')}: Keine Handlungsfelder")
        
        logger.info(f"Status: {users_with_handlungsfelder} Benutzer mit Handlungsfeldern, {users_without_handlungsfelder} ohne")
        
        return users_without_handlungsfelder == 0
        
    except Exception as e:
        logger.error(f"Fehler beim Prüfen: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Handlungsfeld-Migration')
    parser.add_argument('--check', action='store_true', help='Nur Status prüfen')
    parser.add_argument('--migrate', action='store_true', help='Migration durchführen')
    
    args = parser.parse_args()
    
    if args.check:
        check_handlungsfelder()
    elif args.migrate:
        migrate_handlungsfelder()
    else:
        print("Verwendung:")
        print("  python migrate_handlungsfelder.py --check    # Status prüfen")
        print("  python migrate_handlungsfelder.py --migrate  # Migration durchführen") 