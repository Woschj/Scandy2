#!/bin/bash

# Scandy HTTPS Switch Script
# Wechselt zwischen HTTP und HTTPS

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

echo -e "${BLUE}🔒 Scandy HTTPS Switch${NC}"
echo "================================"

# Prüfe ob SSL-Zertifikate existieren
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    log_warning "SSL-Zertifikate nicht gefunden, erstelle neue..."
    mkdir -p ssl
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=DE/ST=NRW/L=Dortmund/O=Scandy/CN=localhost"
    log_success "SSL-Zertifikate erstellt"
fi

# Stoppe aktuelle Container
log_step "Stoppe aktuelle Container..."
docker compose down 2>/dev/null || true

# Baue und starte HTTPS-Version
log_step "Starte HTTPS-Version..."
docker compose -f docker-compose.https.yml build --no-cache
docker compose -f docker-compose.https.yml up -d

# Warte auf Start
log_info "Warte auf Container-Start..."
sleep 10

# Prüfe Status
if docker compose -f docker-compose.https.yml ps | grep -q "Up"; then
    log_success "HTTPS-System läuft!"
    echo
    echo -e "${GREEN}✅ HTTPS aktiviert!${NC}"
    echo "📱 HTTP:  http://localhost:5000"
    echo "🔒 HTTPS: https://localhost:5001"
    echo
    echo -e "${YELLOW}⚠️  Wichtige Hinweise:${NC}"
    echo "• Das ist ein selbst-signiertes Zertifikat"
    echo "• Browser werden eine Sicherheitswarnung anzeigen"
    echo "• Klicken Sie auf 'Erweitert' → 'Trotzdem fortfahren'"
    echo "• Für Produktion: Verwenden Sie echte SSL-Zertifikate"
else
    log_error "Container konnten nicht gestartet werden"
    docker compose -f docker-compose.https.yml logs
    exit 1
fi 