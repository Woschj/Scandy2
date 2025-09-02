#!/usr/bin/env bash

# ========================================
# Scandy Streamlined Installer v3.0.0
# ========================================
#
# Einfach, sicher und zuverlässig!
# Automatische Installation für Produktionsumgebungen
#
# ✨ Features:
#   🔒 Root-Rechte automatisch geprüft
#   🗄️  Lokale MongoDB bevorzugt (Port 27017)
#   🐳 Docker-MongoDB als Fallback
#   📁 Korrekte Berechtigungen automatisch
#   🚀 Systemd-Service automatisch konfiguriert
#   ✅ Einfache Fehlerbehandlung
#
# 📋 Verwendung:
#   sudo ./install_scandy.sh     # Automatische Produktionsinstallation
#   ./install_scandy.sh --help   # Hilfe
#
# ========================================

set -euo pipefail

# Farben und Symbole
RED='\033[0;31m' GREEN='\033[0;32m' YELLOW='\033[1;33m' BLUE='\033[0;34m' NC='\033[0m'
ERROR="❌" SUCCESS="✅" INFO="ℹ️" WARNING="⚠️" ROCKET="🚀" GEAR="⚙️"

# Logging-Funktionen
log() { echo -e "${BLUE}$(date '+%H:%M:%S') ${INFO} $*${NC}"; }
success() { echo -e "${GREEN}${SUCCESS} $*${NC}"; }
warning() { echo -e "${YELLOW}${WARNING} $*${NC}"; }
error() { echo -e "${RED}${ERROR} $*${NC}"; exit 1; }

# Prüfe Root-Rechte
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    error "Bitte als root ausführen (sudo ./install_scandy.sh)"
fi

# Konfiguration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/scandy"
BACKUP_DIR="/opt/scandy_backup_$(date +%Y%m%d_%H%M%S)"

# Hilfe-Funktion
show_help() {
    cat << EOF
Scandy Streamlined Installer v3.0.0

VERWENDUNG:
    sudo ./install_scandy.sh [OPTIONEN]

OPTIONEN:
    --dev          Entwicklungsumgebung installieren
    --test         Nur Tests ausführen
    --clean        Vorherige Installation entfernen
    --help         Diese Hilfe anzeigen

BEISPIELE:
    sudo ./install_scandy.sh          # Vollständige Produktionsinstallation
    sudo ./install_scandy.sh --dev    # Entwicklungsumgebung
    sudo ./install_scandy.sh --clean  # Vorherige Installation entfernen

SYSTEMVORAUSSETZUNGEN:
    - Ubuntu/Debian Linux
    - Root-Rechte (sudo)
    - Internet-Verbindung

EOF
}

# Hauptschritte des vereinfachten Installationsprozesses

step_1_backup_existing() {
    log "Sicherung vorhandener Installation..."
    if [ -d "$INSTALL_DIR" ]; then
        cp -r "$INSTALL_DIR" "$BACKUP_DIR"
        success "Backup erstellt: $BACKUP_DIR"
    fi
}

step_2_install_system_dependencies() {
    log "Installiere Systemabhängigkeiten..."
    apt-get update -qq

    # Installiere Python und grundlegende Tools
    apt-get install -y python3 python3-pip python3-venv git curl wget gnupg lsb-release

    # Füge MongoDB Repository hinzu und installiere MongoDB
    log "Installiere MongoDB..."
    if ! command -v mongod &> /dev/null; then
        # MongoDB GPG Key und Repository hinzufügen
        wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
        echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list
        apt-get update -qq
        apt-get install -y mongodb-org
        success "MongoDB installiert"
    else
        log "MongoDB bereits installiert"
    fi

    success "Systemabhängigkeiten installiert"
}

step_3_setup_mongodb() {
    log "Konfiguriere MongoDB..."

    # MongoDB Service starten und aktivieren
    systemctl enable mongod
    systemctl start mongod

    # Warte bis MongoDB bereit ist
    log "Warte auf MongoDB..."
    local retries=30
    local count=0
    while ! mongosh --eval "db.adminCommand('ping')" --quiet > /dev/null 2>&1; do
        if [ $count -ge $retries ]; then
            error "MongoDB konnte nicht gestartet werden"
        fi
        sleep 2
        count=$((count + 1))
        log "Versuche MongoDB zu erreichen... ($count/$retries)"
    done

    # Erstelle Datenbank für Scandy (ohne Authentifizierung für einfachere Einrichtung)
    log "Erstelle Scandy-Datenbank..."
    mongosh --eval "
        use scandy;
        db.test.insertOne({test: 'connection'});
        db.test.deleteOne({test: 'connection'});
    " --quiet

    MONGO_URI="mongodb://localhost:27017/scandy"
    success "MongoDB konfiguriert: $MONGO_URI"
}

step_4_copy_files() {
    log "Kopiere Scandy-Dateien..."
    mkdir -p "$INSTALL_DIR"

    # Kopiere alle Dateien mit rsync
    rsync -a --exclude='venv/' --exclude='__pycache__/' --exclude='.git/' \
          --exclude='node_modules/' --exclude='*.log' --exclude='.env' \
          "$SCRIPT_DIR/" "$INSTALL_DIR/"

    success "Dateien kopiert nach $INSTALL_DIR"
}

step_4_1_set_permissions() {
    log "Setze Berechtigungen..."

    # Erstelle notwendige Verzeichnisse
    mkdir -p "$INSTALL_DIR/app/uploads"
    mkdir -p "$INSTALL_DIR/app/backups"
    mkdir -p "$INSTALL_DIR/app/logs"
    mkdir -p "$INSTALL_DIR/app/flask_session"

    # Setze Berechtigungen basierend auf dem Modus
    if [[ "${MODE:-production}" == "development" ]]; then
        # Im Entwicklungsmodus: Eigentümer ist der aktuelle Benutzer
        local current_user=$(whoami)
        chown -R "$current_user:$current_user" "$INSTALL_DIR"
        chmod -R 755 "$INSTALL_DIR"
        log "Entwicklungsmodus: Berechtigungen für Benutzer $current_user gesetzt"
    else
        # Im Produktionsmodus: Eigentümer ist root
        chown -R root:root "$INSTALL_DIR"
        chmod -R 755 "$INSTALL_DIR"
    fi

    # Setze spezifische Berechtigungen für beschreibbare Verzeichnisse
    chmod -R 775 "$INSTALL_DIR/app/uploads"
    chmod -R 775 "$INSTALL_DIR/app/backups"
    chmod -R 775 "$INSTALL_DIR/app/logs"
    chmod -R 775 "$INSTALL_DIR/app/flask_session"

    success "Berechtigungen gesetzt"
}

step_5_setup_python() {
    log "Richte Python-Umgebung ein..."
    cd "$INSTALL_DIR"

    # Virtual Environment
    python3 -m venv venv
    source venv/bin/activate

    # Abhängigkeiten installieren
    pip install --upgrade pip
    pip install -r requirements.txt

    success "Python-Umgebung eingerichtet"
}

step_6_configure_environment() {
    log "Konfiguriere Umgebung..."

    # .env Datei
    cat > .env << EOF
# Webserver Konfiguration
WEB_PORT=5000
HOST=0.0.0.0

# MongoDB Konfiguration
MONGODB_URI=$MONGO_URI
MONGODB_DB=scandy

# Flask Konfiguration
SECRET_KEY=$(openssl rand -hex 32)
FLASK_ENV=production
FLASK_CONFIG=production

# Session Konfiguration
SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
SESSION_COOKIE_HTTPONLY=true
REMEMBER_COOKIE_HTTPONLY=true
SESSION_TYPE=filesystem
PERMANENT_SESSION_LIFETIME=7

# System Konfiguration
SYSTEM_NAME=Scandy
TICKET_SYSTEM_NAME=Aufgaben
TOOL_SYSTEM_NAME=Werkzeuge
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
BASE_URL=http://localhost:5000

# Logging
LOG_LEVEL=INFO
LOG_FILE=/opt/scandy/app/logs/scandy.log

# Sicherheit
ENABLE_CSRF=true
EOF

    success "Umgebung konfiguriert"
}

step_7_create_service() {
    log "Erstelle Systemd-Service..."

    # Wrapper-Scripts
    mkdir -p bin

    cat > bin/start_scandy.sh << 'EOF'
#!/bin/bash
cd /opt/scandy
source venv/bin/activate
export PYTHONPATH=/opt/scandy

# Lade Umgebungsvariablen aus .env Datei
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Stelle sicher, dass MongoDB läuft
if ! systemctl is-active --quiet mongod; then
    echo "Starte MongoDB..."
    systemctl start mongod
    sleep 5
fi

exec python app/wsgi.py
EOF
    chmod +x bin/start_scandy.sh

    # Systemd-Service
    cat > /etc/systemd/system/scandy.service << EOF
[Unit]
Description=Scandy Application
After=network.target mongod.service
Requires=mongod.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/scandy
Environment=PYTHONPATH=/opt/scandy
EnvironmentFile=/opt/scandy/.env
ExecStart=/opt/scandy/bin/start_scandy.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable scandy
    success "Systemd-Service erstellt und aktiviert"
}

step_8_test_installation() {
    log "Teste Installation..."
    cd "$INSTALL_DIR"
    source venv/bin/activate

    # Vollständiger Test der Anwendung
    log "Teste Anwendungs-Import..."
    if python -c "import sys; sys.path.insert(0, '.'); from app import create_app; print('✅ App kann importiert werden')"; then
        success "Anwendung kann erfolgreich importiert werden"
    else
        error "Anwendung hat Import-Probleme"
    fi

    # Teste Datenbankverbindung
    log "Teste Datenbankverbindung..."
    if python -c "
import sys
sys.path.insert(0, '.')
from app import create_app
from pymongo import MongoClient
import os

app = create_app()
mongo_uri = app.config.get('MONGODB_URI', '$MONGO_URI')
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print('✅ Datenbankverbindung erfolgreich')
except Exception as e:
    print(f'❌ Datenbankverbindung fehlgeschlagen: {e}')
    sys.exit(1)
"; then
        success "Datenbankverbindung funktioniert"
    else
        error "Datenbankverbindung fehlgeschlagen"
    fi
}

step_9_start_service() {
    log "Starte Scandy-Service..."
    systemctl start scandy

    # Warte bis der Service bereit ist
    log "Warte auf Service..."
    local retries=30
    local count=0
    while ! curl -f http://localhost:5000/health > /dev/null 2>&1; do
        if [ $count -ge $retries ]; then
            warning "Service konnte nicht gestartet werden - bitte manuell prüfen"
            return 1
        fi
        sleep 3
        count=$((count + 1))
        log "Warte auf Service... ($count/$retries)"
    done

    success "Scandy-Service erfolgreich gestartet"
}

# Hauptfunktion
main() {
    echo "=================================================="
    echo "🚀 $ROCKET Scandy Streamlined Installer v3.0.0"
    echo "=================================================="
    echo

    # Parameter verarbeiten
    MODE="production"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev)
                MODE="development"
                shift
                ;;
            --test)
                MODE="test"
                shift
                ;;
            --clean)
                MODE="clean"
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Unbekannte Option: $1"
                ;;
        esac
    done

    case $MODE in
        "test")
            log "Führe nur Tests aus..."
            step_8_test_installation
            ;;
        "clean")
            log "Entferne vorhandene Installation..."
            if [ -d "$INSTALL_DIR" ]; then
                rm -rf "$INSTALL_DIR"
                success "Vorhandene Installation entfernt"
            fi
            ;;
        *)
            # Vollständige Installation
            log "Starte vollständige Installation..."
            step_1_backup_existing
            step_2_install_system_dependencies
            step_3_setup_mongodb
            step_4_copy_files
            step_4_1_set_permissions
            step_5_setup_python
            step_6_configure_environment
            step_7_create_service
            step_8_test_installation
            step_9_start_service

            echo
            echo "=================================================="
            success "Installation abgeschlossen!"
            echo
            echo "🌐 Web-Interface: http://localhost:5000"
            echo "📊 MongoDB: $MONGO_URI"
            echo
            echo "🚀 Service starten: sudo systemctl start scandy"
            echo "📋 Status prüfen: sudo systemctl status scandy"
            echo "📝 Logs anzeigen: sudo journalctl -u scandy -f"
            echo
            echo "=================================================="
            ;;
    esac
}

# Script starten
main "$@"
