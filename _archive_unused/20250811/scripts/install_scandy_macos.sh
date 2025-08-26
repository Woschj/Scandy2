#!/bin/bash
set -euo pipefail

# Scandy macOS Installer mit Docker Desktop
# Funktioniert auf macOS mit Docker Desktop

echo "🍎 Scandy macOS Installer - Starte Installation..."
echo ""

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging-Funktionen
log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $*"; }
success() { echo -e "${GREEN}✅${NC} $*"; }
error() { echo -e "${RED}❌${NC} $*"; }
info() { echo -e "${YELLOW}ℹ️${NC} $*"; }
warning() { echo -e "${YELLOW}⚠️${NC} $*"; }

# Prüfe macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    error "Dieses Skript ist nur für macOS gedacht!"
    exit 1
fi

# Prüfe Docker Desktop
log "Prüfe Docker Desktop..."
if ! command -v docker >/dev/null 2>&1; then
    error "Docker Desktop ist nicht installiert!"
    echo ""
    info "Bitte installiere Docker Desktop von: https://www.docker.com/products/docker-desktop/"
    echo "Nach der Installation starte Docker Desktop und führe dieses Skript erneut aus."
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info >/dev/null 2>&1; then
    error "Docker läuft nicht!"
    echo ""
    info "Bitte starte Docker Desktop und warte bis es vollständig geladen ist."
    info "Dann führe dieses Skript erneut aus."
    exit 1
fi

success "Docker Desktop läuft"

# Prüfe Docker Compose
if ! command -v docker-compose >/dev/null 2>&1; then
    error "Docker Compose ist nicht verfügbar!"
    echo ""
    info "Bitte stelle sicher, dass Docker Compose in Docker Desktop aktiviert ist."
    exit 1
fi

success "Docker Compose verfügbar"

# Port-Auswahl
echo ""
echo "🌐 Port-Auswahl für Scandy:"
echo "1) Port 5000 (Standard-Scandy-Port)"
echo "2) Port 8080 (Häufig verwendeter Port)"
echo "3) Port 3000 (Entwicklungsport)"
echo "4) Benutzerdefinierter Port"
echo ""
read -p "Wähle Port (1-4): " PORT_CHOICE

case $PORT_CHOICE in
    1)
        WEB_PORT=5000
        PORT_NAME="Standard-Scandy"
        ;;
    2)
        WEB_PORT=8080
        PORT_NAME="Häufig verwendet"
        ;;
    3)
        WEB_PORT=3000
        PORT_NAME="Entwicklung"
        ;;
    4)
        read -p "Gib benutzerdefinierten Port ein (z.B. 9000): " WEB_PORT
        PORT_NAME="Benutzerdefiniert"
        ;;
    *)
        WEB_PORT=5000
        PORT_NAME="Standard-Scandy (Standardauswahl)"
        ;;
esac

# Prüfe ob Port verfügbar ist
if lsof -Pi :$WEB_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    warning "Port $WEB_PORT ist bereits belegt!"
    info "Verwende stattdessen Port 5001"
    WEB_PORT=5001
    PORT_NAME="Alternative (Port $WEB_PORT belegt)"
fi

success "Verwende Port: $WEB_PORT ($PORT_NAME)"

# Aktuelles Verzeichnis speichern
CURRENT_DIR=$(pwd)
log "Aktuelles Verzeichnis: $CURRENT_DIR"

# Prüfe ob Scandy-Code im aktuellen Verzeichnis ist
if [ ! -d "$CURRENT_DIR/app" ] && [ ! -f "$CURRENT_DIR/docker-compose.yml" ]; then
    error "Kein Scandy-Code im aktuellen Verzeichnis gefunden!"
    echo ""
    info "Bitte führe dieses Skript im Scandy-Projektverzeichnis aus."
    info "Das Verzeichnis sollte eine 'app/' Ordner und 'docker-compose.yml' enthalten."
    exit 1
fi

success "Scandy-Code gefunden"

# 1. .env-Datei erstellen
log "Erstelle .env-Datei..."
if [ -f ".env" ]; then
    warning ".env-Datei existiert bereits - sichere sie ab"
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Generiere sichere Passwörter
MONGO_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)

cat > .env << EOF
# ========================================
# SCANDY - Umgebungsvariablen für macOS
# ========================================
# 
# ⚠️  SICHERHEITSWARNUNG ⚠️
# 
# WICHTIG: Ändere diese Passwörter nach der Installation!
# - MONGO_INITDB_ROOT_PASSWORD
# - SECRET_KEY  
# - ME_CONFIG_BASICAUTH_PASSWORD
# - Admin-Passwort in der Web-App
#
# ========================================

# === MONGODB DATENBANK ===
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=$MONGO_PASSWORD
MONGO_INITDB_DATABASE=scandy
MONGODB_DB=scandy
MONGODB_COLLECTION_PREFIX=

# Verbindungs-URI für die App
MONGODB_URI=mongodb://admin:${MONGO_PASSWORD}@scandy-mongodb-scandy:27017/scandy?authSource=admin

# === SICHERHEIT ===
SECRET_KEY=$SECRET_KEY

# === SYSTEMNAMEN ===
SYSTEM_NAME=Scandy
TICKET_SYSTEM_NAME=Aufgaben
TOOL_SYSTEM_NAME=Werkzeuge
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter
CONTAINER_NAME=scandy-app-scandy

# === SESSION COOKIES ===
SESSION_COOKIE_SECURE=False
REMEMBER_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
REMEMBER_COOKIE_HTTPONLY=True

# === MONGO EXPRESS ===
ME_CONFIG_BASICAUTH_USERNAME=admin
ME_CONFIG_BASICAUTH_PASSWORD=$MONGO_PASSWORD

# === RATE LIMITING ===
RATELIMIT_ENABLED=True
RATELIMIT_STORAGE_URL=memory://

# === SSL/HTTPS KONFIGURATION ===
FORCE_HTTPS=False

# === FEATURE-FLAGS ===
ENABLE_TICKET_SYSTEM=true
ENABLE_JOB_BOARD=false
ENABLE_WEEKLY_REPORTS=true

# === PRODUKTIONS-EINSTELLUNGEN ===
FLASK_ENV=production
FLASK_DEBUG=0
TESTING=False

# === NOTFALLFUNKTIONEN ===
ENABLE_EMERGENCY_ADMIN=false
EOF

success ".env-Datei erstellt"
info "MongoDB Passwort: $MONGO_PASSWORD"
info "Secret Key: $SECRET_KEY"

# 2. Docker Compose anpassen
log "Passe Docker Compose für macOS an..."

# Erstelle eine macOS-spezifische docker-compose.yml
cat > docker-compose.macos.yml << EOF
version: '3.8'

services:
  scandy-mongodb-scandy:
    image: mongo:7
    container_name: scandy-mongodb-scandy
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      MONGO_INITDB_DATABASE: \${MONGO_INITDB_ROOT_DATABASE}
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data_scandy:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - scandy-network-scandy
    command: mongod --bind_ip_all
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 10s
      retries: 15
      start_period: 30s
    env_file:
      - .env

  scandy-mongo-express-scandy:
    image: mongo-express:1.0.0
    container_name: scandy-mongo-express-scandy
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
      ME_CONFIG_MONGODB_URL: mongodb://admin:\${MONGO_INITDB_ROOT_PASSWORD}@scandy-mongodb-scandy:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: \${MONGO_INITDB_ROOT_PASSWORD}
    ports:
      - "8081:8081"
    depends_on:
      scandy-mongodb-scandy:
        condition: service_healthy
    networks:
      - scandy-network-scandy
    env_file:
      - .env

  scandy-app-scandy:
    build:
      context: .
      dockerfile: Dockerfile
    image: scandy-local:dev-scandy
    container_name: scandy-app-scandy
    restart: unless-stopped
    environment:
      - DATABASE_MODE=mongodb
      - MONGODB_URI=\${MONGODB_URI}
      - MONGODB_DB=\${MONGODB_DB}
      - FLASK_ENV=\${FLASK_ENV}
      - SECRET_KEY=\${SECRET_KEY}
      - SYSTEM_NAME=\${SYSTEM_NAME}
      - TICKET_SYSTEM_NAME=\${TICKET_SYSTEM_NAME}
      - TOOL_SYSTEM_NAME=\${TOOL_SYSTEM_NAME}
      - CONSUMABLE_SYSTEM_NAME=\${CONSUMABLE_SYSTEM_NAME}
      - CONTAINER_NAME=\${CONTAINER_NAME}
      - TZ=Europe/Berlin
      - SESSION_COOKIE_SECURE=\${SESSION_COOKIE_SECURE}
      - REMEMBER_COOKIE_SECURE=\${REMEMBER_COOKIE_SECURE}
    ports:
      - "$WEB_PORT:5000"
    volumes:
      - ./app:/app/app
      - app_uploads_scandy:/app/app/uploads
      - app_backups_scandy:/app/app/backups
      - app_logs_scandy:/app/app/logs
      - app_sessions_scandy:/app/app/flask_session
    depends_on:
      scandy-mongodb-scandy:
        condition: service_healthy
    networks:
      - scandy-network-scandy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    env_file:
      - .env

volumes:
  mongodb_data_scandy:
    driver: local
  app_uploads_scandy:
    driver: local
  app_backups_scandy:
    driver: local
  app_logs_scandy:
    driver: local
  app_sessions_scandy:
    driver: local

networks:
  scandy-network-scandy:
    driver: bridge
EOF

success "Docker Compose für macOS angepasst"

# 3. Docker Images bauen und starten
log "Baue Docker Images..."
docker-compose -f docker-compose.macos.yml build

success "Docker Images gebaut"

log "Starte Services..."
docker-compose -f docker-compose.macos.yml up -d

success "Services gestartet"

# 4. Warten auf App-Start
log "Warte auf App-Start..."
for i in {1..60}; do
    if curl -f "http://localhost:$WEB_PORT/health" >/dev/null 2>&1 || curl -f "http://localhost:$WEB_PORT/" >/dev/null 2>&1; then
        success "Scandy läuft auf Port $WEB_PORT"
        break
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        log "Warte auf App-Start... ($i/60)"
        
        # Zeige Container-Status
        log "Container-Status:"
        docker-compose -f docker-compose.macos.yml ps
    fi
    
    if [ $i -eq 60 ]; then
        error "App startet nicht nach 2 Minuten"
        
        # Detaillierte Fehlerdiagnose
        log "Fehlerdiagnose:"
        log "Container-Logs:"
        docker-compose -f docker-compose.macos.yml logs --tail=20
        
        log "Container-Status:"
        docker-compose -f docker-compose.macos.yml ps
        
        info "Prüfe Logs: docker-compose -f docker-compose.macos.yml logs -f"
        exit 1
    fi
    sleep 2
done

# 5. Admin-Benutzer erstellen
log "Erstelle Admin-Benutzer..."
if [ -f "create_admin.py" ]; then
    log "Verwende vorhandenes create_admin.py Skript..."
    docker-compose -f docker-compose.macos.yml exec scandy-app-scandy python create_admin.py
else
    log "Erstelle Admin-Benutzer über die Web-Oberfläche..."
    info "Öffne http://localhost:$WEB_PORT/setup im Browser"
    info "Erstelle dort den ersten Admin-Benutzer"
fi

# 6. Fertig!
echo ""
success "Installation abgeschlossen!"
echo ""
echo "🌐 Web-App: http://localhost:$WEB_PORT"
echo "📊 MongoDB: mongodb://localhost:27017/scandy"
echo "🔧 Mongo Express: http://localhost:8081"
echo "👤 Admin: admin / $MONGO_PASSWORD"
echo ""
echo "📝 Nützliche Befehle:"
echo "  Status anzeigen: docker-compose -f docker-compose.macos.yml ps"
echo "  Logs anzeigen: docker-compose -f docker-compose.macos.yml logs -f"
echo "  Stoppen: docker-compose -f docker-compose.macos.yml down"
echo "  Neustarten: docker-compose -f docker-compose.macos.yml restart"
echo ""
echo "🎯 Das war's! Scandy läuft jetzt mit Docker auf deinem MacBook."
echo ""
echo "⚠️  WICHTIG: Ändere die Standard-Passwörter in der .env-Datei!"
echo "   - MONGO_INITDB_ROOT_PASSWORD"
echo "   - SECRET_KEY"
echo "   - ME_CONFIG_BASICAUTH_PASSWORD"
