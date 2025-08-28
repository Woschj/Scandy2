#!/bin/bash

#####################################################################
# Setup Backup Cleanup Cron Job
# Richtet automatische Bereinigung alter Backups ein
#####################################################################

set -e

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    BACKUP CLEANUP CRON SETUP                 ║"
echo "║                    Automatische Bereinigung alter Backups    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Prüfe ob wir im Scandy-Verzeichnis sind
if [ ! -f "cleanup_old_backups_improved.py" ]; then
    log_error "cleanup_old_backups_improved.py nicht gefunden!"
    log_info "Bitte im Scandy-Verzeichnis ausführen"
    exit 1
fi

# Scandy-Verzeichnis finden
SCANDY_DIR=$(pwd)
log_info "Scandy-Verzeichnis: $SCANDY_DIR"

# Cron-Job erstellen
log_info "Erstelle Cron-Job für automatische Backup-Bereinigung..."

# Entferne bestehenden Cron-Job
(crontab -l 2>/dev/null | grep -v "cleanup_old_backups.py") | crontab -

# Füge neuen Cron-Job hinzu (täglich um 2:00 Uhr)
CRON_JOB="0 2 * * * cd $SCANDY_DIR && python3 cleanup_old_backups_improved.py >> $SCANDY_DIR/logs/backup_cleanup.log 2>&1"

(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

log_success "Cron-Job eingerichtet!"
log_info "Backup-Bereinigung läuft täglich um 2:00 Uhr"
log_info "Logs werden in logs/backup_cleanup.log geschrieben"

# Zeige aktuellen Cron-Jobs
log_info "Aktuelle Cron-Jobs:"
crontab -l | grep -E "(cleanup|backup)" || log_warning "Keine Backup-Cron-Jobs gefunden"

# Teste das Cleanup-Script
log_info "Teste Cleanup-Script..."
python3 cleanup_old_backups_improved.py

log_success "Setup abgeschlossen!"
log_info "Backup-Bereinigung ist jetzt automatisch aktiv" 