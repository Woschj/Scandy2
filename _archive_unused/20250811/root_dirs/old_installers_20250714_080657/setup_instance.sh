#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy Instance Setup"
echo "========================================"
echo

# Prüfe ob Docker installiert ist
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker ist nicht installiert!${NC}"
    exit 1
fi

# Prüfe ob Docker läuft
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ ERROR: Docker läuft nicht!${NC}"
    exit 1
fi

# Eingabe für Instance-Name
echo -e "${BLUE}📝 Instance-Konfiguration${NC}"
echo

read -p "Name der Instance (z.B. 'verwaltung', 'produktion', 'test'): " INSTANCE_NAME
if [ -z "$INSTANCE_NAME" ]; then
    echo -e "${RED}❌ ERROR: Name ist erforderlich!${NC}"
    exit 1
fi

# Berechne Ports basierend auf Instance-Name
INSTANCE_NUMBER=$(echo "$INSTANCE_NAME" | tr -cd '0-9' | sed 's/^0*//')
if [ -z "$INSTANCE_NUMBER" ]; then
    INSTANCE_NUMBER=1
fi

# Berechne Ports (5000 + Instance-Nummer, 27017 + Instance-Nummer, 8081 + Instance-Nummer)
WEB_PORT=$((5000 + INSTANCE_NUMBER))
MONGODB_PORT=$((27017 + INSTANCE_NUMBER))
MONGO_EXPRESS_PORT=$((8081 + INSTANCE_NUMBER))

echo
echo -e "${BLUE}📊 Automatisch berechnete Ports:${NC}"
echo "- Web-App:     http://localhost:$WEB_PORT"
echo "- MongoDB:     localhost:$MONGODB_PORT"
echo "- Mongo Express: http://localhost:$MONGO_EXPRESS_PORT"
echo

read -p "Möchten Sie die Ports anpassen? (j/N): " CUSTOM_PORTS
if [[ $CUSTOM_PORTS =~ ^[Jj]$ ]]; then
    read -p "Web-Port (Standard: $WEB_PORT): " CUSTOM_WEB_PORT
    if [ ! -z "$CUSTOM_WEB_PORT" ]; then
        WEB_PORT=$CUSTOM_WEB_PORT
    fi
    
    read -p "MongoDB-Port (Standard: $MONGODB_PORT): " CUSTOM_MONGODB_PORT
    if [ ! -z "$CUSTOM_MONGODB_PORT" ]; then
        MONGODB_PORT=$CUSTOM_MONGODB_PORT
    fi
    
    read -p "Mongo Express-Port (Standard: $MONGO_EXPRESS_PORT): " CUSTOM_MONGO_EXPRESS_PORT
    if [ ! -z "$CUSTOM_MONGO_EXPRESS_PORT" ]; then
        MONGO_EXPRESS_PORT=$CUSTOM_MONGO_EXPRESS_PORT
    fi
fi

# Erstelle Verzeichnis
INSTANCE_DIR="scandy-$INSTANCE_NAME"
echo
echo -e "${BLUE}📁 Erstelle Verzeichnis für $INSTANCE_NAME...${NC}"

if [ -d "$INSTANCE_DIR" ]; then
    echo -e "${YELLOW}⚠️  Verzeichnis $INSTANCE_DIR existiert bereits!${NC}"
    read -p "Möchten Sie es überschreiben? (j/N): " confirm
    if [[ ! $confirm =~ ^[Jj]$ ]]; then
        echo "Setup abgebrochen."
        exit 0
    fi
    rm -rf "$INSTANCE_DIR"
fi

mkdir -p "$INSTANCE_DIR"
cd "$INSTANCE_DIR"

# Kopiere alle notwendigen Dateien
echo -e "${BLUE}📋 Kopiere Dateien...${NC}"
cp -r ../app .
cp ../Dockerfile .
cp ../requirements.txt .
cp ../package.json .
cp ../tailwind.config.js .
cp ../postcss.config.js .
cp ../env.example .

# Erstelle .env
echo -e "${BLUE}⚙️  Erstelle .env...${NC}"
cat > .env << EOF
# $INSTANCE_NAME Konfiguration
DEPARTMENT=$INSTANCE_NAME
DEPARTMENT_NAME=$INSTANCE_NAME
WEB_PORT=$WEB_PORT
MONGODB_PORT=$MONGODB_PORT

# MongoDB Konfiguration
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=${INSTANCE_NAME}Password123
MONGO_INITDB_DATABASE=${INSTANCE_NAME}_scandy

# System-Namen
SYSTEM_NAME=Scandy $INSTANCE_NAME
TICKET_SYSTEM_NAME=Aufgaben $INSTANCE_NAME
TOOL_SYSTEM_NAME=Werkzeuge $INSTANCE_NAME
CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter $INSTANCE_NAME

# Sicherheit
SECRET_KEY=${INSTANCE_NAME}SecretKey123456789
SESSION_COOKIE_SECURE=False
REMEMBER_COOKIE_SECURE=False
EOF

# Erstelle .gitignore
echo -e "${BLUE}📝 Erstelle .gitignore...${NC}"
cat > .gitignore << 'EOF'
# Instance spezifische Dateien
.env
logs/
backups/
uploads/
data/
tmp/

# Docker
docker-compose.override.yml

# System
.DS_Store
Thumbs.db
EOF

# Erstelle docker-compose.yml
echo -e "${BLUE}🐳 Erstelle docker-compose.yml...${NC}"
cat > docker-compose.yml << EOF
services:
  scandy-mongodb-$INSTANCE_NAME:
    image: mongo:7
    container_name: scandy-mongodb-$INSTANCE_NAME
    restart: unless-stopped
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: ${INSTANCE_NAME}Password123
      MONGO_INITDB_DATABASE: ${INSTANCE_NAME}_scandy
    ports:
      - "$MONGODB_PORT:27017"
    volumes:
      - mongodb_data_$INSTANCE_NAME:/data/db
      - ./mongo-init:/docker-entrypoint-initdb.d
    networks:
      - scandy-network-$INSTANCE_NAME
    command: mongod --bind_ip_all
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 10s
      retries: 15
      start_period: 30s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    ulimits:
      nproc: 64000
      nofile:
        soft: 65536
        hard: 65536

  scandy-mongo-express-$INSTANCE_NAME:
    image: mongo-express:1.0.0
    container_name: scandy-mongo-express-$INSTANCE_NAME
    restart: unless-stopped
    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: admin
      ME_CONFIG_MONGODB_ADMINPASSWORD: ${INSTANCE_NAME}Password123
      ME_CONFIG_MONGODB_URL: mongodb://admin:${INSTANCE_NAME}Password123@scandy-mongodb-$INSTANCE_NAME:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: ${INSTANCE_NAME}Password123
    ports:
      - "$MONGO_EXPRESS_PORT:8081"
    depends_on:
      scandy-mongodb-$INSTANCE_NAME:
        condition: service_healthy
    networks:
      - scandy-network-$INSTANCE_NAME
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  scandy-app-$INSTANCE_NAME:
    build:
      context: .
      dockerfile: Dockerfile
    image: scandy-local:dev-$INSTANCE_NAME
    container_name: scandy-app-$INSTANCE_NAME
    restart: unless-stopped
    environment:
      - MONGODB_URI=mongodb://admin:${INSTANCE_NAME}Password123@scandy-mongodb-$INSTANCE_NAME:27017/${INSTANCE_NAME}_scandy?authSource=admin
      - SECRET_KEY=${INSTANCE_NAME}SecretKey123456789
      - SYSTEM_NAME=Scandy $INSTANCE_NAME
      - TICKET_SYSTEM_NAME=Aufgaben $INSTANCE_NAME
      - TOOL_SYSTEM_NAME=Werkzeuge $INSTANCE_NAME
      - CONSUMABLE_SYSTEM_NAME=Verbrauchsgüter $INSTANCE_NAME
      - SESSION_COOKIE_SECURE=False
      - REMEMBER_COOKIE_SECURE=False
    volumes:
      - ./app:/app/app
      - ./data/$INSTANCE_NAME:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
      - ./uploads:/app/uploads
      - ./app/static:/app/app/static
      - ./app/templates:/app/app/templates
    ports:
      - "$WEB_PORT:5000"
    depends_on:
      scandy-mongodb-$INSTANCE_NAME:
        condition: service_healthy
    networks:
      - scandy-network-$INSTANCE_NAME
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  mongodb_data_$INSTANCE_NAME:

networks:
  scandy-network-$INSTANCE_NAME:
    driver: bridge
EOF

# Erstelle mongo-init Verzeichnis
mkdir -p mongo-init

# Erstelle einziges Management-Skript
echo -e "${BLUE}🔧 Erstelle Management-Skript...${NC}"
cat > manage.sh << 'EOF'
#!/bin/bash

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Instance-Name aus Verzeichnis extrahieren
INSTANCE_NAME=$(basename "$PWD" | sed 's/scandy-//')

show_help() {
    echo "========================================"
    echo "Scandy $INSTANCE_NAME - Management"
    echo "========================================"
    echo
    echo "Verwendung: ./manage.sh [BEFEHL]"
    echo
    echo "Befehle:"
    echo "  start     - Container starten"
    echo "  stop      - Container stoppen"
    echo "  restart   - Container neustarten"
    echo "  status    - Status anzeigen"
    echo "  logs      - Logs anzeigen"
    echo "  update    - App aktualisieren"
    echo "  backup    - Backup erstellen"
    echo "  shell     - In App-Container wechseln"
    echo "  help      - Diese Hilfe anzeigen"
    echo
    echo "Beispiele:"
    echo "  ./manage.sh start"
    echo "  ./manage.sh status"
    echo "  ./manage.sh logs"
}

case "$1" in
    start)
        echo -e "${BLUE}🚀 Starte $INSTANCE_NAME...${NC}"
        docker compose up -d
        echo
        echo -e "${GREEN}✅ $INSTANCE_NAME gestartet!${NC}"
        echo
        echo "🌐 Verfügbare Services:"
        echo "- Web-App:     http://localhost:$WEB_PORT"
        echo "- Mongo Express: http://localhost:$MONGO_EXPRESS_PORT"
        echo
        echo "🔐 Standard-Zugangsdaten:"
        echo "- Benutzer: admin"
        echo "- Passwort: admin123"
        ;;
    stop)
        echo -e "${BLUE}🛑 Stoppe $INSTANCE_NAME...${NC}"
        docker compose down
        echo -e "${GREEN}✅ $INSTANCE_NAME gestoppt!${NC}"
        ;;
    restart)
        echo -e "${BLUE}🔄 Starte $INSTANCE_NAME neu...${NC}"
        docker compose restart
        echo -e "${GREEN}✅ $INSTANCE_NAME neugestartet!${NC}"
        ;;
    status)
        echo -e "${BLUE}📊 Status von $INSTANCE_NAME:${NC}"
        docker compose ps
        ;;
    logs)
        echo -e "${BLUE}📋 Logs von $INSTANCE_NAME:${NC}"
        docker compose logs -f
        ;;
    update)
        echo -e "${BLUE}🔄 Update $INSTANCE_NAME...${NC}"
        docker compose down
        docker compose build --no-cache
        docker compose up -d
        echo -e "${GREEN}✅ Update abgeschlossen!${NC}"
        ;;
    backup)
        echo -e "${BLUE}💾 Backup erstellen...${NC}"
        docker compose exec scandy-mongodb-$INSTANCE_NAME mongodump --out /backup
        echo -e "${GREEN}✅ Backup erstellt!${NC}"
        ;;
    shell)
        echo -e "${BLUE}🐚 Wechsle in App-Container...${NC}"
        docker compose exec scandy-app-$INSTANCE_NAME bash
        ;;
    help|*)
        show_help
        ;;
esac
EOF

chmod +x manage.sh

# Erstelle README
echo -e "${BLUE}📖 Erstelle README...${NC}"
cat > README.md << EOF
# Scandy $INSTANCE_NAME

## Übersicht
Dies ist die $INSTANCE_NAME-Instanz von Scandy mit eigener Datenbank und Konfiguration.

## Services
- **Scandy App**: http://localhost:$WEB_PORT
- **Mongo Express**: http://localhost:$MONGO_EXPRESS_PORT
- **MongoDB**: localhost:$MONGODB_PORT

## Standard-Zugangsdaten
- **Benutzer**: admin
- **Passwort**: admin123

## Management

### Starten
\`\`\`bash
./manage.sh start
\`\`\`

### Stoppen
\`\`\`bash
./manage.sh stop
\`\`\`

### Status prüfen
\`\`\`bash
./manage.sh status
\`\`\`

### Logs anzeigen
\`\`\`bash
./manage.sh logs
\`\`\`

### Update
\`\`\`bash
./manage.sh update
\`\`\`

### Backup erstellen
\`\`\`bash
./manage.sh backup
\`\`\`

### In Container wechseln
\`\`\`bash
./manage.sh shell
\`\`\`

## Konfiguration
Die Konfiguration erfolgt über die \`.env\`-Datei.

## Daten
- **Datenbank**: ${INSTANCE_NAME}_scandy
- **Backups**: ./backups/
- **Logs**: ./logs/
- **Uploads**: ./uploads/

## Sicherheit
⚠️ **Wichtig**: Ändern Sie die Standard-Passwörter in der \`.env\`-Datei!
EOF

echo
echo "========================================"
echo -e "${GREEN}✅ $INSTANCE_NAME Setup abgeschlossen!${NC}"
echo "========================================"
echo
echo -e "${BLUE}📁 Verzeichnis:${NC} $INSTANCE_DIR"
echo -e "${BLUE}🌐 Web-App:${NC} http://localhost:$WEB_PORT"
echo -e "${BLUE}🗄️  MongoDB:${NC} localhost:$MONGODB_PORT"
echo -e "${BLUE}📊 Mongo Express:${NC} http://localhost:$MONGO_EXPRESS_PORT"
echo
echo -e "${BLUE}🚀 Nächste Schritte:${NC}"
echo "1. cd $INSTANCE_DIR"
echo "2. ./manage.sh start"
echo "3. Öffne http://localhost:$WEB_PORT"
echo
echo -e "${BLUE}📋 Management-Befehle:${NC}"
echo "- ./manage.sh start    # Starten"
echo "- ./manage.sh stop     # Stoppen"
echo "- ./manage.sh status   # Status"
echo "- ./manage.sh logs     # Logs"
echo "- ./manage.sh update   # Update"
echo
echo -e "${YELLOW}⚠️  Wichtig: Ändere die Passwörter in .env!${NC}" 