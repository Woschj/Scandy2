#!/bin/bash

# Scandy HTTP Switch Script
# Wechselt zurück zu HTTP

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

echo -e "${BLUE}📱 Scandy HTTP Switch${NC}"
echo "================================"

# Stoppe aktuelle Container
log_step "Stoppe aktuelle Container..."
docker compose -f docker-compose.https.yml down 2>/dev/null || true
docker compose down 2>/dev/null || true

# Baue und starte HTTP-Version
log_step "Starte HTTP-Version..."
docker compose build --no-cache
docker compose up -d

# Warte auf Start
log_info "Warte auf Container-Start..."
sleep 10

# Prüfe Status
if docker compose ps | grep -q "Up"; then
    log_success "HTTP-System läuft!"
    echo
    echo -e "${GREEN}✅ HTTP aktiviert!${NC}"
    echo "📱 HTTP:  http://localhost:5000"
    echo
    echo -e "${YELLOW}⚠️  Hinweis:${NC}"
    echo "• System läuft jetzt ohne SSL"
    echo "• Für Produktion: Verwenden Sie HTTPS"
else
    log_error "Container konnten nicht gestartet werden"
    docker compose logs
    exit 1
fi 