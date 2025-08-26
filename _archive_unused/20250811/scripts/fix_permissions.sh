#!/bin/bash

# Scandy Berechtigungsreparatur-Skript
# Behebt alle Berechtigungsprobleme in der Scandy-Installation

set -euo pipefail

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $*"; }
success() { echo -e "${GREEN}✅${NC} $*"; }
error() { echo -e "${RED}❌${NC} $*"; }
warning() { echo -e "${YELLOW}⚠️${NC} $*"; }

echo "========================================"
echo "🔧 Scandy Berechtigungsreparatur"
echo "========================================"

# Prüfe Root-Rechte
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    error "Bitte als root ausführen (sudo)"
    exit 1
fi

SCANDY_DIR="/opt/scandy"

# Prüfe ob Scandy installiert ist
if [ ! -d "$SCANDY_DIR" ]; then
    error "Scandy ist nicht in $SCANDY_DIR installiert!"
    exit 1
fi

log "Starte Berechtigungsreparatur für $SCANDY_DIR..."

# 1. Hauptverzeichnis-Berechtigungen
log "Korrigiere Hauptverzeichnis-Berechtigungen..."
chown -R root:root "$SCANDY_DIR"
chmod -R 755 "$SCANDY_DIR"
success "Hauptverzeichnis-Berechtigungen korrigiert"

# 2. Spezielle Verzeichnisse
log "Korrigiere spezielle Verzeichnisse..."

# Logs-Verzeichnis
if [ -d "$SCANDY_DIR/logs" ]; then
    chmod -R 777 "$SCANDY_DIR/logs"
    success "Logs-Verzeichnis-Berechtigungen korrigiert"
fi

# Backups-Verzeichnis
if [ -d "$SCANDY_DIR/backups" ]; then
    chmod -R 777 "$SCANDY_DIR/backups"
    success "Backups-Verzeichnis-Berechtigungen korrigiert"
fi

# 3. Session-Verzeichnis (kritisch!)
log "Korrigiere Session-Verzeichnis..."
if [ -d "$SCANDY_DIR/app/flask_session" ]; then
    # Erstelle Verzeichnis falls es nicht existiert
    mkdir -p "$SCANDY_DIR/app/flask_session"
    
    # Setze Verzeichnisberechtigungen
    chown -R root:root "$SCANDY_DIR/app/flask_session/"
    chmod 755 "$SCANDY_DIR/app/flask_session/"
    
    # Setze Dateiberechtigungen für bestehende Dateien
    if [ "$(ls -A "$SCANDY_DIR/app/flask_session/" 2>/dev/null)" ]; then
        find "$SCANDY_DIR/app/flask_session/" -type f -exec chmod 644 {} \; 2>/dev/null || true
    fi
    
    # Erstelle .gitkeep mit korrekten Berechtigungen
    touch "$SCANDY_DIR/app/flask_session/.gitkeep"
    chown root:root "$SCANDY_DIR/app/flask_session/.gitkeep"
    chmod 644 "$SCANDY_DIR/app/flask_session/.gitkeep"
    
    success "Session-Verzeichnis-Berechtigungen korrigiert"
else
    warning "Session-Verzeichnis nicht gefunden - erstelle es..."
    mkdir -p "$SCANDY_DIR/app/flask_session"
    chown -R root:root "$SCANDY_DIR/app/flask_session/"
    chmod 755 "$SCANDY_DIR/app/flask_session/"
    touch "$SCANDY_DIR/app/flask_session/.gitkeep"
    chown root:root "$SCANDY_DIR/app/flask_session/.gitkeep"
    chmod 644 "$SCANDY_DIR/app/flask_session/.gitkeep"
    success "Session-Verzeichnis erstellt und Berechtigungen gesetzt"
fi

# 4. Python-Virtualenv
log "Korrigiere Python-Virtualenv-Berechtigungen..."
if [ -d "$SCANDY_DIR/venv" ]; then
    chown -R root:root "$SCANDY_DIR/venv"
    chmod -R 755 "$SCANDY_DIR/venv"
    
    # Setze ausführbare Berechtigungen für Python-Binaries
    find "$SCANDY_DIR/venv/bin" -type f -exec chmod +x {} \; 2>/dev/null || true
    
    success "Python-Virtualenv-Berechtigungen korrigiert"
fi

# 5. Konfigurationsdateien
log "Korrigiere Konfigurationsdatei-Berechtigungen..."
if [ -f "$SCANDY_DIR/.env" ]; then
    chown root:root "$SCANDY_DIR/.env"
    chmod 644 "$SCANDY_DIR/.env"
    success ".env-Datei-Berechtigungen korrigiert"
fi

# 6. Systemd-Service neu laden
log "Lade Systemd-Service neu..."
if [ -f "/etc/systemd/system/scandy.service" ]; then
    systemctl daemon-reload
    success "Systemd-Service neu geladen"
fi

# 7. Cron-Jobs korrigieren
log "Korrigiere Cron-Job-Berechtigungen..."
if [ -f "/etc/cron.d/scandy-session-cleanup" ]; then
    chmod 644 "/etc/cron.d/scandy-session-cleanup"
    success "Session-Cleanup Cron-Job-Berechtigungen korrigiert"
fi

if [ -f "/etc/cron.d/scandy-port80-monitor" ]; then
    chmod 644 "/etc/cron.d/scandy-port80-monitor"
    success "Port80-Monitor Cron-Job-Berechtigungen korrigiert"
fi

# 8. Service neu starten
log "Starte Scandy-Service neu..."
if systemctl is-active --quiet scandy.service 2>/dev/null; then
    systemctl restart scandy.service
    success "Scandy-Service neu gestartet"
else
    warning "Scandy-Service läuft nicht - starte ihn..."
    if systemctl start scandy.service; then
        success "Scandy-Service gestartet"
    else
        error "Fehler beim Starten des Scandy-Services"
        log "Prüfen Sie die Logs: journalctl -u scandy.service -f"
    fi
fi

# 9. Finale Berechtigungsprüfung
log "Führe finale Berechtigungsprüfung durch..."
sleep 3

# Prüfe Session-Verzeichnis nochmal
if [ -d "$SCANDY_DIR/app/flask_session" ]; then
    log "Session-Verzeichnis nach Service-Start:"
    ls -la "$SCANDY_DIR/app/flask_session/" | head -5
    
    # Korrigiere Berechtigungen für neue Dateien
    if [ "$(ls -A "$SCANDY_DIR/app/flask_session/" 2>/dev/null)" ]; then
        find "$SCANDY_DIR/app/flask_session/" -type f -exec chown root:root {} \; -exec chmod 644 {} \; 2>/dev/null || true
        chmod 755 "$SCANDY_DIR/app/flask_session/"
        success "Session-Berechtigungen final korrigiert"
    fi
fi

# 10. Service-Status anzeigen
log "Service-Status:"
systemctl status scandy.service --no-pager | head -10

echo
echo "========================================"
success "🎉 Berechtigungsreparatur abgeschlossen!"
echo "========================================"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Service-Status:   sudo systemctl status scandy.service"
echo "- Service-Logs:     sudo journalctl -u scandy.service -f"
echo "- Service-Neustart: sudo systemctl restart scandy.service"
echo "- Berechtigungen:   sudo ./fix_permissions.sh"
echo
echo -e "${BLUE}📁 Korrigierte Verzeichnisse:${NC}"
echo "- Hauptverzeichnis: $SCANDY_DIR"
echo "- Session:          $SCANDY_DIR/app/flask_session/"
echo "- Virtualenv:       $SCANDY_DIR/venv/"
echo "- Logs:             $SCANDY_DIR/logs/"
echo "- Backups:          $SCANDY_DIR/backups/"
echo "========================================"
