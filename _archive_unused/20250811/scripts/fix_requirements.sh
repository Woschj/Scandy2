#!/bin/bash

# Fix Requirements Script für Scandy
# Behebt fehlende Python-Pakete nach Updates

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

echo -e "${BLUE}🔧 Scandy Requirements Fix${NC}"
echo "================================"

# Installationsmodus erkennen
if [ -f "docker-compose.yml" ]; then
    log_info "Docker-Installation erkannt"
    MODE="docker"
elif systemctl list-units --type=service | grep -q scandy; then
    log_info "Native Installation erkannt"
    MODE="native"
elif [ -f "/opt/scandy/start_scandy.sh" ]; then
    log_info "LXC-Installation erkannt"
    MODE="lxc"
else
    log_error "Keine Scandy-Installation gefunden!"
    exit 1
fi

case $MODE in
    docker)
        log_step "Behebe Docker Requirements..."
        
        # Container stoppen
        log_info "Stoppe Container..."
        docker compose down
        
        # Images und Volumes komplett entfernen
        log_info "Entferne alte Images und Volumes..."
        docker compose down -v
        docker image rm scandy-local:dev-scandy 2>/dev/null || true
        
        # Requirements neu installieren
        log_info "Baue Images komplett neu..."
        docker compose build --no-cache --build-arg REBUILD_REQUIREMENTS=true
        
        # Container starten
        log_info "Starte Container..."
        docker compose up -d
        
        # Status prüfen
        log_info "Prüfe Container-Status..."
        sleep 15
        if docker compose ps | grep -q "Up"; then
            log_success "Docker-Container laufen"
            
            # Zusätzliche Prüfung der Logs
            log_info "Prüfe Application-Logs..."
            sleep 5
            if docker compose logs scandy-app-scandy | grep -q "Worker failed to boot"; then
                log_error "Application startet nicht - weitere Diagnose nötig"
                docker compose logs scandy-app-scandy --tail=20
            else
                log_success "Application startet erfolgreich"
            fi
        else
            log_error "Container konnten nicht gestartet werden"
            docker compose logs
        fi
        ;;
        
    native)
        log_step "Behebe Native Requirements..."
        
        # Service stoppen
        INSTANCE_NAME=$(grep "INSTANCE_NAME=" .env | cut -d'=' -f2 2>/dev/null || echo "scandy")
        log_info "Stoppe Service scandy-$INSTANCE_NAME..."
        sudo systemctl stop scandy-$INSTANCE_NAME
        
        # Requirements neu installieren
        log_info "Installiere Requirements neu..."
        cd /opt/scandy
        sudo -u scandy venv/bin/pip install --upgrade pip
        sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt
        
        # Service starten
        log_info "Starte Service..."
        sudo systemctl start scandy-$INSTANCE_NAME
        
        # Status prüfen
        sleep 5
        if systemctl is-active --quiet scandy-$INSTANCE_NAME; then
            log_success "Native Service läuft"
        else
            log_error "Service konnte nicht gestartet werden"
            sudo systemctl status scandy-$INSTANCE_NAME
        fi
        ;;
        
    lxc)
        log_step "Behebe LXC Requirements..."
        
        # Prozess stoppen
        log_info "Stoppe Scandy-Prozess..."
        pkill -f "gunicorn.*scandy" || true
        
        # Requirements neu installieren
        log_info "Installiere Requirements neu..."
        cd /opt/scandy
        sudo -u scandy venv/bin/pip install --upgrade pip
        sudo -u scandy venv/bin/pip install --upgrade -r requirements.txt
        
        # Service starten
        log_info "Starte Service..."
        sudo -u scandy ./start_scandy.sh &
        
        # Status prüfen
        sleep 5
        if pgrep -f "gunicorn.*scandy" > /dev/null; then
            log_success "LXC Service läuft"
        else
            log_error "Service konnte nicht gestartet werden"
        fi
        ;;
esac

log_success "Requirements-Fix abgeschlossen!"
echo
echo -e "${GREEN}✅ Nächste Schritte:${NC}"
echo "1. Prüfe die Anwendung: http://localhost:5000"
echo "2. Prüfe die Logs bei Problemen"
echo "3. Teste die Funktionalität" 