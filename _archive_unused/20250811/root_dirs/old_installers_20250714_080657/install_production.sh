#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy Produktions-Installation"
echo "========================================"
echo

# Prüfe ob .env existiert
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ ERROR: .env-Datei nicht gefunden!${NC}"
    echo "Bitte erstelle eine .env-Datei basierend auf env.example"
    exit 1
fi

echo -e "${BLUE}🛑 Stoppe bestehende Container...${NC}"
docker compose down

echo
echo -e "${BLUE}🔨 Baue Container mit Produktionsserver...${NC}"
docker compose build --no-cache

echo
echo -e "${BLUE}🚀 Starte Container...${NC}"
docker compose up -d

echo
echo -e "${BLUE}⏳ Warte auf Container-Start...${NC}"
sleep 10

echo
echo -e "${BLUE}🔍 Pruefe Container-Status...${NC}"
docker compose ps

echo
echo -e "${BLUE}📋 Pruefe Logs...${NC}"
docker compose logs --tail=20 scandy-app

echo
echo "========================================"
echo -e "${GREEN}✅ Installation abgeschlossen!${NC}"
echo "========================================"
echo
echo -e "${BLUE}🌐 Verfügbare Services:${NC}"
echo "- Anwendung:      http://localhost:5000"
echo "- Mongo Express:  http://localhost:8081"
echo
echo -e "${BLUE}🔧 Nützliche Befehle:${NC}"
echo "- Logs anzeigen:  docker compose logs -f"
echo "- Container stoppen: docker compose down"
echo "- Status:         docker compose ps"
echo 