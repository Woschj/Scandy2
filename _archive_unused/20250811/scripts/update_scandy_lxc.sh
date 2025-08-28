#!/bin/bash

#####################################################################
# Scandy LXC Update Script
# Für Setup mit /Scandy2/ als Quellverzeichnis
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
    echo "║                    SCANDY LXC UPDATE                         ║"
    echo "║                    /Scandy2/ → /opt/scandy/                  ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_banner

# Verzeichnisse
SOURCE_DIR="/Scandy2"
TARGET_DIR="/opt/scandy"

# Falls Script im Projekt liegt, dieses als Quelle verwenden
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/app" ]; then
    SOURCE_DIR="$SCRIPT_DIR"
fi

# Prüfe verschiedene mögliche Quellverzeichnisse
if [ ! -d "$SOURCE_DIR" ]; then
    # Versuche andere mögliche Namen
    if [ -d "/scandy2" ]; then
        SOURCE_DIR="/scandy2"
    elif [ -d "/Scandy" ]; then
        SOURCE_DIR="/Scandy"
    elif [ -d "/scandy" ]; then
        SOURCE_DIR="/scandy"
    elif [ -d "/home/woschj/Scandy2" ]; then
        SOURCE_DIR="/home/woschj/Scandy2"
    elif [ -d "/home/scandy/Scandy2" ]; then
        SOURCE_DIR="/home/scandy/Scandy2"
    elif [ -d "/root/Scandy2" ]; then
        SOURCE_DIR="/root/Scandy2"
    else
        log_error "Quellverzeichnis nicht gefunden! Suche nach Scandy2..."
        find / -name "Scandy2" -type d 2>/dev/null | head -5
        exit 1
    fi
fi

log_step "Scandy LXC Update gestartet..."

# Prüfe Quellverzeichnis
log_info "Verwende Quellverzeichnis: $SOURCE_DIR"
if [ ! -d "$SOURCE_DIR" ]; then
    log_error "Quellverzeichnis $SOURCE_DIR nicht gefunden!"
    exit 1
fi

if [ ! -d "$SOURCE_DIR/app" ]; then
    log_error "app-Verzeichnis in $SOURCE_DIR nicht gefunden!"
    exit 1
fi

# Prüfe Zielverzeichnis
if [ ! -d "$TARGET_DIR" ]; then
    log_error "Zielverzeichnis $TARGET_DIR nicht gefunden!"
    exit 1
fi

# Git Pull (falls im Quellverzeichnis)
cd "$SOURCE_DIR"
log_info "Wechsle ins Quellverzeichnis: $SOURCE_DIR"

# Git Pull
# Optional: Git Pull, nur wenn .git existiert
if [ -d .git ]; then
    log_info "Aktualisiere Code von Git..."
    git pull || log_warning "Git pull fehlgeschlagen, verwende lokalen Code"
fi

# Prozess stoppen
log_info "Stoppe Scandy-Prozess..."
pkill -f "gunicorn.*scandy" || true
pkill -f "python.*app" || true
sleep 2

# Backup erstellen
if [ -d "$TARGET_DIR/app" ]; then
    log_info "Erstelle Backup des alten Codes..."
    BACKUP_DIR="$TARGET_DIR/app.backup.$(date +%Y%m%d_%H%M%S)"
    cp -r "$TARGET_DIR/app" "$BACKUP_DIR" 2>/dev/null || {
        log_warning "Konnte Backup nicht erstellen"
    }
    log_info "Backup erstellt: $BACKUP_DIR"
fi

# Code kopieren
log_info "Kopiere Code von $SOURCE_DIR nach $TARGET_DIR..."
if cp -r "$SOURCE_DIR/app"/* "$TARGET_DIR/app/" 2>/dev/null; then
    log_success "Code erfolgreich kopiert!"
else
    log_error "Fehler beim Kopieren des Codes!"
    exit 1
fi

# Berechtigungen setzen
log_info "Setze Berechtigungen..."
chown -R scandy:scandy "$TARGET_DIR/app" 2>/dev/null || {
    log_warning "Konnte Berechtigungen nicht setzen"
}

# Wechsle ins Zielverzeichnis
cd "$TARGET_DIR"

# Dependencies aktualisieren (optional)
if [ -d "venv" ] && [ -f "requirements.txt" ]; then
    log_info "Aktualisiere Python-Pakete..."
    sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt 2>/dev/null || {
        log_warning "Konnte Dependencies nicht aktualisieren"
    }
fi

# Service starten
log_info "Starte Scandy als Systemd-Service..."
systemctl restart scandy.service 2>/dev/null || {
    log_warning "systemctl restart scandy fehlgeschlagen"
    log_info "Versuche alternative Start-Methoden..."
    
    # Fallback: Docker Compose
    if [ -f "docker-compose.yml" ]; then
        log_info "Versuche Docker Compose..."
        docker compose restart 2>/dev/null || docker compose up -d 2>/dev/null || {
            log_error "Docker Compose fehlgeschlagen"
        }
    else
        log_error "Keine Start-Methode gefunden!"
    fi
}

# Warte auf Service (systemd aktiv + HTTP 200/302 auf Port 5001)
log_info "Warte auf Service..."
for i in {1..20}; do
    if systemctl is-active --quiet scandy.service; then
        CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5001/ || true)
        if [ "$CODE" = "200" ] || [ "$CODE" = "302" ]; then
            log_success "LXC Update abgeschlossen!"
            log_info "Service ist erreichbar unter: http://127.0.0.1:5001"
            exit 0
        fi
    fi
    sleep 2
done

log_warning "Service braucht länger zum Starten"
log_info "Prüfe Logs mit: journalctl -u scandy.service -n 200 --no-pager"

# Zeige Prozess-Status
log_info "Aktive Scandy-Prozesse:"
ps aux | grep -E "(gunicorn|scandy)" | grep -v grep || log_warning "Keine Scandy-Prozesse gefunden"

# Zeige Verzeichnisstruktur
log_info "Verzeichnisstruktur:"
echo "Quellverzeichnis: $SOURCE_DIR"
echo "Zielverzeichnis: $TARGET_DIR"
ls -la "$TARGET_DIR/app/" | head -10 