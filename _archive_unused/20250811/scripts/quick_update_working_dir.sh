#!/bin/bash

# Schnelles Scandy Update aus Arbeitsverzeichnis
# Kopiert Code von /home/woschj/Scandy2 nach /opt/scandy und startet Service neu

set -e  # Beende bei Fehlern

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "========================================"
echo "Schnelles Scandy Update aus Arbeitsverzeichnis"
echo "========================================"

# Verzeichnisse definieren
WORKING_DIR="/home/woschj/Scandy2"
SCANDY_DIR="/opt/scandy"

# Verzeichnisse prüfen
if [ ! -d "$WORKING_DIR" ]; then
    print_error "Arbeitsverzeichnis $WORKING_DIR nicht gefunden!"
    exit 1
fi

if [ ! -d "$SCANDY_DIR" ]; then
    print_error "Scandy-Installationsverzeichnis $SCANDY_DIR nicht gefunden!"
    exit 1
fi

print_status "Arbeitsverzeichnis: $WORKING_DIR"
print_status "Installationsverzeichnis: $SCANDY_DIR"

# Aktuelle Änderungen anzeigen
print_status "Aktuelle Änderungen im Arbeitsverzeichnis:"
cd "$WORKING_DIR"
git status --short || print_warning "Git-Status konnte nicht abgerufen werden"

echo
read -p "Möchten Sie fortfahren? (j/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Jj]$ ]]; then
    print_warning "Update abgebrochen"
    exit 0
fi

# Scandy Service stoppen
print_status "Stoppe Scandy Service..."
if sudo systemctl is-active --quiet scandy.service 2>/dev/null; then
    sudo systemctl stop scandy.service || print_warning "Service konnte nicht gestoppt werden"
else
    print_warning "Service läuft nicht oder existiert nicht"
fi

# Code kopieren
print_status "Kopiere Code von $WORKING_DIR nach $SCANDY_DIR..."

# Wichtige Verzeichnisse und Dateien kopieren
print_status "Kopiere App-Code..."
if ! rsync -av --exclude='venv' --exclude='.git' --exclude='logs' --exclude='backups' --exclude='*.log' --exclude='node_modules' "$WORKING_DIR/" "$SCANDY_DIR/"; then
    print_error "Fehler beim Kopieren des Codes!"
    exit 1
fi

print_success "Code erfolgreich kopiert"

# Berechtigungen korrigieren
print_status "Korrigiere Berechtigungen..."
sudo chown -R root:root "$SCANDY_DIR"
sudo chmod -R 755 "$SCANDY_DIR"

# Spezielle Berechtigungen für bestimmte Verzeichnisse
if [ -d "$SCANDY_DIR/logs" ]; then
    sudo chmod -R 777 "$SCANDY_DIR/logs"
    print_success "Log-Verzeichnis Berechtigungen korrigiert"
fi

if [ -d "$SCANDY_DIR/backups" ]; then
    sudo chmod -R 777 "$SCANDY_DIR/backups"
    print_success "Backup-Verzeichnis Berechtigungen korrigiert"
fi

# Session-Verzeichnis korrigieren
if [ -d "$SCANDY_DIR/app/flask_session" ]; then
    sudo chmod -R 777 "$SCANDY_DIR/app/flask_session"
    print_success "Session-Verzeichnis Berechtigungen korrigiert"
fi

print_success "Berechtigungen korrigiert"

# Service-PATH korrigieren VOR dem Start
print_status "Korrigiere Service-PATH falls nötig..."
SERVICE_FILE="/etc/systemd/system/scandy.service"

if [ -f "$SERVICE_FILE" ]; then
    # Prüfe ob der Service bereits den korrekten PATH hat
    if sudo grep -q "Environment=PATH=/opt/scandy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" "$SERVICE_FILE"; then
        print_success "Service-PATH ist bereits korrekt"
    else
        print_status "Service-PATH wird korrigiert..."
        
        # Ersetze den alten PATH mit dem korrekten
        if sudo grep -q "Environment=PATH=" "$SERVICE_FILE"; then
            sudo sed -i 's|Environment=PATH=.*|Environment=PATH=/opt/scandy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin|' "$SERVICE_FILE"
        else
            # Füge den PATH hinzu falls er nicht existiert
            sudo sed -i '/\[Service\]/a Environment=PATH=/opt/scandy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin' "$SERVICE_FILE"
        fi
        
        sudo systemctl daemon-reload
        print_success "Service-PATH korrigiert und daemon neu geladen"
    fi
else
    print_warning "Service-Datei $SERVICE_FILE nicht gefunden"
fi

# Scandy Service starten
print_status "Starte Scandy Service..."
if ! sudo systemctl start scandy.service; then
    print_error "Fehler beim Starten des Services!"
    print_error "Prüfen Sie die Logs: sudo journalctl -u scandy.service -f"
    exit 1
fi

print_status "Warte auf Service-Start..."
sleep 3

# Service-Status prüfen
print_status "Prüfe Service-Status..."
sudo systemctl status scandy.service --no-pager

echo
echo "========================================"
print_success "✅ SCHNELLES UPDATE ABGESCHLOSSEN!"
echo "========================================"
echo
print_success "🎉 Code wurde erfolgreich kopiert und Service neu gestartet!"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Service-Status:   sudo systemctl status scandy.service"
echo "- Service-Logs:     sudo journalctl -u scandy.service -f"
echo "- Service-Neustart: sudo systemctl restart scandy.service"
echo
echo -e "${BLUE}📁 Kopierte Verzeichnisse:${NC}"
echo "- App-Code:         $SCANDY_DIR/app/"
echo "- Templates:        $SCANDY_DIR/app/templates/"
echo "- Static Files:     $SCANDY_DIR/app/static/"
echo "- Utils:            $SCANDY_DIR/app/utils/"
echo "========================================"
