#!/bin/bash

#####################################################################
# LXC Container Update Script für Scandy
# Speziell für LXC-Container optimiert
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
    echo "║                    LXC CONTAINER UPDATE                      ║"
    echo "║                         Scandy                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Prüfe ob wir im Scandy-Verzeichnis sind (/Scandy2/)
if [ ! -d "app" ]; then
    log_error "Bitte führen Sie dieses Script im /Scandy2/ Verzeichnis aus!"
    exit 1
fi

show_banner

# Lade Umgebungsvariablen
if [ -f ".env" ]; then
    source .env
    log_info "Umgebungsvariablen geladen"
else
    log_warning ".env Datei nicht gefunden, verwende Standardwerte"
    INSTANCE_NAME="scandy"
    WEB_PORT="5000"
fi

log_step "LXC Container Update gestartet..."

# Git Pull (bereits im Container ausgeführt)
log_info "Code wurde bereits von Git geholt"

# Prüfe ob wir in einem LXC-Container sind
if [ -f "/proc/1/cgroup" ] && grep -q "lxc" /proc/1/cgroup; then
    log_info "LXC-Container erkannt"
    
    # Prozess stoppen
    log_info "Stoppe Scandy-Prozess..."
    pkill -f "gunicorn.*scandy" || true
    pkill -f "python.*app" || true
    sleep 2
    
    # Stelle sicher, dass Code korrekt kopiert ist
    log_info "Stelle sicher, dass Code korrekt kopiert ist..."
    
    # Prüfe Verzeichnisstruktur
    if [ ! -d "app" ]; then
        log_error "app-Verzeichnis nicht gefunden!"
        exit 1
    fi
    
    # Kopiere Code in das richtige Verzeichnis
    SCANDY_DIR="/opt/scandy"
    if [ -d "$SCANDY_DIR" ]; then
        log_info "Kopiere Code nach $SCANDY_DIR..."
        
        # Backup erstellen
        if [ -d "$SCANDY_DIR/app" ]; then
            log_info "Erstelle Backup des alten Codes..."
            cp -r "$SCANDY_DIR/app" "$SCANDY_DIR/app.backup.$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
        fi
        
        # Code kopieren
        log_info "Kopiere neuen Code..."
        cp -r app/* "$SCANDY_DIR/app/" 2>/dev/null || {
            log_warning "Konnte Code nicht kopieren, verwende Git-Version"
        }
        
        # Wechsle ins Scandy-Verzeichnis
        cd "$SCANDY_DIR"
        
        # Dependencies aktualisieren
        log_info "Aktualisiere Python-Pakete..."
        if [ -d "venv" ]; then
            sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt 2>/dev/null || {
                log_warning "Konnte Dependencies nicht aktualisieren"
            }
        fi
        
        # Service starten
        log_info "Starte Scandy..."
        if [ -f "start_scandy.sh" ]; then
            sudo -u scandy ./start_scandy.sh &
        else
            log_error "start_scandy.sh nicht gefunden!"
            exit 1
        fi
        
    else
        log_error "Scandy-Verzeichnis $SCANDY_DIR nicht gefunden!"
        exit 1
    fi
    
else
    log_info "Kein LXC-Container erkannt, verwende Standard-Update..."
    
    # Standard LXC-Update
    pkill -f "gunicorn.*scandy" || true
    sleep 2
    
    # Code aktualisieren
    cd /opt/scandy 2>/dev/null || {
        log_error "Konnte nicht ins /opt/scandy Verzeichnis wechseln!"
        exit 1
    }
    
    git pull || log_warning "Git pull fehlgeschlagen"
    
    # Dependencies aktualisieren
    if [ -d "venv" ]; then
        sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt
    fi
    
    # Service starten
    if [ -f "start_scandy.sh" ]; then
        sudo -u scandy ./start_scandy.sh &
    else
        log_error "start_scandy.sh nicht gefunden!"
        exit 1
    fi
fi

# Warte auf Service
log_info "Warte auf Service..."
for i in {1..15}; do
    if curl -f http://localhost:${WEB_PORT:-5000}/health &>/dev/null; then
        log_success "LXC Update abgeschlossen!"
        log_info "Service ist verfügbar unter: http://localhost:${WEB_PORT:-5000}"
        exit 0
    fi
    sleep 2
done

log_warning "Service braucht länger zum Starten"
log_info "Prüfe Logs mit: tail -f /opt/scandy/logs/app.log"

# Zeige Prozess-Status
log_info "Aktive Scandy-Prozesse:"
ps aux | grep -E "(gunicorn|scandy)" | grep -v grep || log_warning "Keine Scandy-Prozesse gefunden" 