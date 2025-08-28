#!/bin/bash

#####################################################################
# Code-Kopierung für LXC Container
# Kopiert Code nach /opt/scandy/app nach git pull
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    CODE KOPIERUNG                            ║"
    echo "║                    LXC Container                             ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_banner

log_step "Code-Kopierung gestartet..."

# Prüfe ob wir im Scandy-Verzeichnis sind (/Scandy2/)
if [ ! -d "app" ]; then
    log_error "app-Verzeichnis nicht gefunden! Bitte im /Scandy2/ Verzeichnis ausführen."
    exit 1
fi

# Prüfe ob /opt/scandy existiert
SCANDY_DIR="/opt/scandy"
if [ ! -d "$SCANDY_DIR" ]; then
    log_error "Scandy-Verzeichnis $SCANDY_DIR nicht gefunden!"
    exit 1
fi

# Prozess stoppen
log_info "Stoppe Scandy-Prozess..."
pkill -f "gunicorn.*scandy" || true
pkill -f "python.*app" || true
sleep 2

# Backup erstellen
if [ -d "$SCANDY_DIR/app" ]; then
    log_info "Erstelle Backup des alten Codes..."
    BACKUP_DIR="$SCANDY_DIR/app.backup.$(date +%Y%m%d_%H%M%S)"
    cp -r "$SCANDY_DIR/app" "$BACKUP_DIR" 2>/dev/null || {
        log_warning "Konnte Backup nicht erstellen"
    }
    log_info "Backup erstellt: $BACKUP_DIR"
fi

# Code kopieren
log_info "Kopiere Code nach $SCANDY_DIR/app..."
if cp -r app/* "$SCANDY_DIR/app/" 2>/dev/null; then
    log_success "Code erfolgreich kopiert!"
else
    log_error "Fehler beim Kopieren des Codes!"
    exit 1
fi

# Berechtigungen setzen
log_info "Setze Berechtigungen..."
chown -R scandy:scandy "$SCANDY_DIR/app" 2>/dev/null || {
    log_warning "Konnte Berechtigungen nicht setzen"
}

# Wechsle ins Scandy-Verzeichnis
cd "$SCANDY_DIR"

# Dependencies aktualisieren (optional)
if [ -d "venv" ] && [ -f "requirements.txt" ]; then
    log_info "Aktualisiere Python-Pakete..."
    sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt 2>/dev/null || {
        log_warning "Konnte Dependencies nicht aktualisieren"
    }
fi

# Service starten
log_info "Starte Scandy..."
if [ -f "start_scandy.sh" ]; then
    sudo -u scandy ./start_scandy.sh &
    log_success "Scandy gestartet!"
else
    log_error "start_scandy.sh nicht gefunden!"
    exit 1
fi

# Warte auf Service
log_info "Warte auf Service..."
for i in {1..10}; do
    if curl -f http://localhost:5000/health &>/dev/null; then
        log_success "Code-Kopierung abgeschlossen!"
        log_info "Service ist verfügbar unter: http://localhost:5000"
        exit 0
    fi
    sleep 2
done

log_warning "Service braucht länger zum Starten"
log_info "Prüfe Logs mit: tail -f /opt/scandy/logs/app.log"

# Zeige Prozess-Status
log_info "Aktive Scandy-Prozesse:"
ps aux | grep -E "(gunicorn|scandy)" | grep -v grep || log_warning "Keine Scandy-Prozesse gefunden" 