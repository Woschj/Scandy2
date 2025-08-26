#!/bin/bash

#####################################################################
# Quick LXC Update Script
# Einfaches Update: Dateien kopieren + systemctl restart scandy
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
echo "║                    QUICK LXC UPDATE                          ║"
echo "║                    Dateien kopieren + systemctl restart      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verzeichnisse
SOURCE_DIR="/Scandy2"
TARGET_DIR="/opt/scandy"

# Prüfe verschiedene mögliche Quellverzeichnisse
if [ ! -d "$SOURCE_DIR" ]; then
    # Versuche andere mögliche Namen
    if [ -d "/scandy2" ]; then
        SOURCE_DIR="/scandy2"
    elif [ -d "/Scandy" ]; then
        SOURCE_DIR="/Scandy"
    elif [ -d "/scandy" ]; then
        SOURCE_DIR="/scandy"
    elif [ -d "/home/scandy/Scandy2" ]; then
        SOURCE_DIR="/home/scandy/Scandy2"
    elif [ -d "/root/Scandy2" ]; then
        SOURCE_DIR="/root/Scandy2"
    else
        log_error "Quellverzeichnis nicht gefunden!"
        echo "Verfügbare Verzeichnisse:"
        find / -name "*scandy*" -type d 2>/dev/null | head -5
        exit 1
    fi
fi

log_info "Verwende Quellverzeichnis: $SOURCE_DIR"
log_info "Zielverzeichnis: $TARGET_DIR"

# Prüfe Verzeichnisse
if [ ! -d "$SOURCE_DIR/app" ]; then
    log_error "app-Verzeichnis in $SOURCE_DIR nicht gefunden!"
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    log_error "Zielverzeichnis $TARGET_DIR nicht gefunden!"
    exit 1
fi

# Git Pull (falls im Quellverzeichnis)
cd "$SOURCE_DIR"
log_info "Aktualisiere Code von Git..."
git pull origin main || git pull origin master || git pull origin IT-VW || {
    log_warning "Git pull fehlgeschlagen, verwende aktuellen Code"
}

# Backup erstellen
if [ -d "$TARGET_DIR/app" ]; then
    log_info "Erstelle Backup..."
    BACKUP_DIR="$TARGET_DIR/app.backup.$(date +%Y%m%d_%H%M%S)"
    cp -r "$TARGET_DIR/app" "$BACKUP_DIR" 2>/dev/null || {
        log_warning "Konnte Backup nicht erstellen"
    }
    log_info "Backup: $BACKUP_DIR"
fi

# Code kopieren
log_info "Kopiere Code..."
if cp -r "$SOURCE_DIR/app"/* "$TARGET_DIR/app/" 2>/dev/null; then
    log_success "Code kopiert!"
else
    log_error "Fehler beim Kopieren!"
    exit 1
fi

# Berechtigungen setzen
log_info "Setze Berechtigungen..."
chown -R scandy:scandy "$TARGET_DIR/app" 2>/dev/null || {
    log_warning "Konnte Berechtigungen nicht setzen"
}

# Service neu starten
log_info "Starte Scandy-Service neu..."
systemctl restart scandy

# Status prüfen
log_info "Prüfe Service-Status..."
sleep 3
if systemctl is-active --quiet scandy; then
    log_success "Service läuft!"
else
    log_warning "Service-Status unklar"
    systemctl status scandy --no-pager -l
fi

log_success "Quick Update abgeschlossen!"
log_info "Service sollte verfügbar sein unter: http://localhost:5000" 