#!/bin/bash

# Schnelles Docker-Build für Scandy
# Optimiert für bessere Cache-Nutzung

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

echo -e "${BLUE}🚀 Schnelles Scandy Build${NC}"
echo "================================"

# Prüfe ob HTTPS gewünscht ist
HTTPS_MODE=false
if [ "$1" = "--https" ]; then
    HTTPS_MODE=true
    log_info "HTTPS-Modus aktiviert"
fi

# Container stoppen
log_info "Stoppe Container..."
docker compose down 2>/dev/null || true

# Docker-Cache leeren (optional)
if [ "$2" = "--no-cache" ]; then
    log_info "Leere Docker-Cache..."
    docker builder prune -f
fi

# Build mit optimierten Einstellungen
log_info "Starte optimiertes Build..."
if [ "$HTTPS_MODE" = true ]; then
    log_info "Baue HTTPS-Version..."
    docker compose -f docker-compose.https.yml build --parallel --compress
    log_success "HTTPS-Build abgeschlossen"
    
    log_info "Starte HTTPS-Container..."
    docker compose -f docker-compose.https.yml up -d
    
    log_success "HTTPS-System läuft!"
    echo "🔒 HTTPS: https://localhost:5000"
else
    log_info "Baue HTTP-Version..."
    docker compose build --parallel --compress
    log_success "HTTP-Build abgeschlossen"
    
    log_info "Starte HTTP-Container..."
    docker compose up -d
    
    log_success "HTTP-System läuft!"
    echo "📱 HTTP: http://localhost:5000"
fi

# Status prüfen
log_info "Prüfe Container-Status..."
sleep 5
if docker compose ps | grep -q "Up"; then
    log_success "Alle Container laufen!"
else
    log_error "Container konnten nicht gestartet werden"
    docker compose logs --tail=20
    exit 1
fi

echo
echo -e "${GREEN}✅ Build erfolgreich!${NC}"
echo "🌐 Zugang: http://localhost:5000"
echo "📊 Mongo Express: http://localhost:8081" 