#!/bin/bash

# Scandy Update Skript für Linux Mint (ohne LXC)
# Aktualisiert Scandy von Git oder kopiert Code aus Arbeitsverzeichnis

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

# Wechsel ins Installationsverzeichnis, damit alle folgenden Schritte dort ausgeführt werden
SCANDY_DIR="/opt/scandy"
if [ ! -d "$SCANDY_DIR" ]; then
    print_error "Scandy-Installationsverzeichnis $SCANDY_DIR nicht gefunden! Bitte zuerst installieren."
    exit 1
fi
cd "$SCANDY_DIR"
print_status "Arbeitsverzeichnis gewechselt nach $SCANDY_DIR"

# Update-Modus auswählen
echo "========================================"
echo "Scandy Update für Linux Mint"
echo "========================================"
echo "Wählen Sie den Update-Modus:"
echo "1) Git Update (Standard)"
echo "2) Code aus Arbeitsverzeichnis kopieren"
echo "3) Beide (Git + Kopieren)"
echo "========================================"

read -p "Wählen Sie Option (1-3, Standard: 1): " UPDATE_MODE
UPDATE_MODE=${UPDATE_MODE:-1}

echo
print_status "Gewählter Update-Modus: $UPDATE_MODE"

# Git Update durchführen
if [[ "$UPDATE_MODE" == "1" || "$UPDATE_MODE" == "3" ]]; then
    echo "========================================"
    echo "Git Update wird durchgeführt..."
    echo "========================================"
    
    print_status "Prüfe aktuellen Git-Status..."
    git status --short

    print_status "Sichere lokale Änderungen (falls vorhanden)..."
    if [[ -n $(git status --porcelain) ]]; then
        print_warning "Lokale Änderungen gefunden - erstelle Backup..."
        git stash push -m "Auto-stash vor Update $(date)"
        print_success "Lokale Änderungen gesichert"
    fi

    print_status "Hole neueste Version vom aktuellen Branch..."
    git pull origin $(git branch --show-current)

    if [ $? -ne 0 ]; then
        print_error "Git pull fehlgeschlagen!"
        exit 1
    fi

    print_success "Code über Git aktualisiert"
fi

# Code aus Arbeitsverzeichnis kopieren
if [[ "$UPDATE_MODE" == "2" || "$UPDATE_MODE" == "3" ]]; then
    echo "========================================"
    echo "Code aus Arbeitsverzeichnis wird kopiert..."
    echo "========================================"
    
    # Arbeitsverzeichnis bestimmen
    WORKING_DIR="/home/woschj/Scandy2"
    SCANDY_DIR="/opt/scandy"
    
    if [ ! -d "$WORKING_DIR" ]; then
        print_error "Arbeitsverzeichnis $WORKING_DIR nicht gefunden!"
        exit 1
    fi
    
    if [ ! -d "$SCANDY_DIR" ]; then
        print_error "Scandy-Installationsverzeichnis $SCANDY_DIR nicht gefunden!"
        exit 1
    fi
    
    print_status "Kopiere Code von $WORKING_DIR nach $SCANDY_DIR..."
    
    # Wichtige Verzeichnisse und Dateien kopieren
    print_status "Kopiere App-Code..."
    rsync -av --exclude='venv' --exclude='.git' --exclude='logs' --exclude='backups' --exclude='*.log' "$WORKING_DIR/" "$SCANDY_DIR/"
    
    if [ $? -ne 0 ]; then
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
    
    print_success "Berechtigungen korrigiert"
fi

print_status "Stoppe Scandy Service..."
sudo systemctl stop scandy.service || print_warning "Service konnte nicht gestoppt werden (möglicherweise nicht aktiv)"

if [ $? -ne 0 ]; then
    print_warning "Service konnte nicht gestoppt werden (möglicherweise nicht aktiv)"
fi

print_status "Aktiviere Virtual Environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    print_success "Virtual Environment aktiviert"
else
    print_warning "Virtual Environment 'venv' nicht gefunden – erstelle neu..."
    python3 -m venv venv
    source venv/bin/activate
    print_success "Virtual Environment neu erstellt und aktiviert"
fi

print_status "Aktualisiere Python-Pakete..."
pip install -r requirements.txt --upgrade || print_warning "Python-Pakete konnten nicht vollständig aktualisiert werden"

if [ $? -ne 0 ]; then
    print_error "Fehler beim Installieren der Python-Pakete!"
    exit 1
fi

print_success "Python-Pakete aktualisiert"

# CSS Build (falls Node.js verfügbar)
if command -v npm &> /dev/null; then
    print_status "Baue CSS neu (Tailwind)..."
    if [ -f "package.json" ]; then
        npm install
        npm run build 2>/dev/null || print_warning "CSS Build nicht verfügbar"
    fi
fi

print_status "Korrigiere Berechtigungen..."
if [ -d "app/static" ]; then
    chmod -R 755 app/static/
    print_success "Static Files Berechtigungen korrigiert"
fi

if [ -d "logs" ]; then
    chmod -R 755 logs/
    print_success "Log-Verzeichnis Berechtigungen korrigiert"
fi

print_status "Starte Scandy Service..."
sudo systemctl start scandy.service

if [ $? -ne 0 ]; then
    print_error "Fehler beim Starten des Services!"
    print_error "Prüfen Sie die Logs: sudo journalctl -u scandy.service -f"
    exit 1
fi

print_status "Warte auf Service-Start..."
sleep 5

print_status "Prüfe Service-Status..."
sudo systemctl status scandy.service --no-pager

# Service-PATH korrigieren falls nötig
print_status "Korrigiere Service-PATH falls nötig..."
if sudo grep -q "Environment=PATH=/opt/scandy/venv/bin$" /etc/systemd/system/scandy.service; then
    print_status "Service-PATH wird korrigiert..."
    sudo sed -i 's|Environment=PATH=/opt/scandy/venv/bin|Environment=PATH=/opt/scandy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin|' /etc/systemd/system/scandy.service
    sudo systemctl daemon-reload
    print_status "Service neu gestartet..."
    sudo systemctl restart scandy.service
    sleep 3
    print_status "Service-Status nach Korrektur:"
    sudo systemctl status scandy.service --no-pager
elif sudo grep -q "Environment=PATH=/opt/scandy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" /etc/systemd/system/scandy.service; then
    print_success "Service-PATH ist bereits korrekt"
else
    print_status "Unbekannter Service-PATH gefunden - korrigiere auf Standard..."
    sudo sed -i 's|Environment=PATH=.*|Environment=PATH=/opt/scandy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin|' /etc/systemd/system/scandy.service
    sudo systemctl daemon-reload
    print_status "Service neu gestartet..."
    sudo systemctl restart scandy.service
    sleep 3
    print_status "Service-Status nach Korrektur:"
    sudo systemctl status scandy.service --no-pager
fi

print_status "Aktiviere Service für Autostart..."
sudo systemctl enable scandy.service

echo
echo "========================================"
print_success "✅ SCANDY UPDATE ABGESCHLOSSEN!"
echo "========================================"
echo
print_success "🎉 Scandy wurde erfolgreich aktualisiert!"
echo

# Update-Modus-spezifische Informationen
case $UPDATE_MODE in
    1)
        echo -e "${BLUE}📥 Update-Modus: Git Update${NC}"
        ;;
    2)
        echo -e "${BLUE}📁 Update-Modus: Code aus Arbeitsverzeichnis kopiert${NC}"
        ;;
    3)
        echo -e "${BLUE}🔄 Update-Modus: Git Update + Code kopiert${NC}"
        ;;
esac

echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Service-Status:   sudo systemctl status scandy.service"
echo "- Service-Logs:     sudo journalctl -u scandy.service -f"
echo "- Service-Neustart: sudo systemctl restart scandy.service"
echo "- Service stoppen:  sudo systemctl stop scandy.service"
echo
echo -e "${BLUE}📁 Wichtige Verzeichnisse:${NC}"
echo "- Logs:    ./logs/"
echo "- Backups: ./backups/"
echo "- Static:  ./app/static/"
echo
if [[ "$UPDATE_MODE" == "1" || "$UPDATE_MODE" == "3" ]]; then
    if [[ -n $(git stash list) ]]; then
        echo -e "${YELLOW}💾 Git Stash verfügbar:${NC}"
        echo "- Lokale Änderungen wiederherstellen: git stash pop"
        echo "- Stash anzeigen: git stash list"
    fi
fi
echo "========================================"
