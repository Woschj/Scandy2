#!/bin/bash

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Scandy Upload-Problem Diagnose"
echo "========================================"
echo "Dieses Skript diagnostiziert Upload-Probleme:"
echo "- 🔍 Verzeichnis-Berechtigungen"
echo "- 🔍 Service-Status"
echo "- 🔍 Nginx-Konfiguration"
echo "- 🔍 Netzwerk-Verbindungen"
echo "- 🔍 Log-Dateien"
echo "========================================"
echo

# 1. Verzeichnis-Berechtigungen prüfen
echo -e "${BLUE}🔍 1. Prüfe Verzeichnis-Berechtigungen...${NC}"

UPLOAD_PATHS=(
    "/opt/scandy/app/uploads"
    "/opt/scandy/app/static/uploads"
    "/opt/scandy/data/uploads"
    "/opt/scandy/uploads"
    "/app/app/uploads"
    "/app/app/static/uploads"
    "/app/uploads"
    "/app/static/uploads"
)

for upload_path in "${UPLOAD_PATHS[@]}"; do
    if [ -d "$upload_path" ]; then
        echo -e "${BLUE}📁 Gefunden: $upload_path${NC}"
        
        # Prüfe Berechtigungen
        PERMS=$(stat -c "%a" "$upload_path" 2>/dev/null || stat -f "%Sp" "$upload_path" 2>/dev/null || echo "unbekannt")
        OWNER=$(stat -c "%U:%G" "$upload_path" 2>/dev/null || stat -f "%Su:%Sg" "$upload_path" 2>/dev/null || echo "unbekannt")
        
        echo -e "   Berechtigungen: $PERMS"
        echo -e "   Besitzer: $OWNER"
        
        # Prüfe ob schreibbar
        if [ -w "$upload_path" ]; then
            echo -e "${GREEN}   ✅ Verzeichnis ist schreibbar${NC}"
        else
            echo -e "${RED}   ❌ Verzeichnis ist NICHT schreibbar${NC}"
        fi
        
        # Prüfe Unterverzeichnisse
        SUBDIRS=("tickets" "jobs" "tools" "consumables")
        for subdir in "${SUBDIRS[@]}"; do
            if [ -d "$upload_path/$subdir" ]; then
                SUB_PERMS=$(stat -c "%a" "$upload_path/$subdir" 2>/dev/null || echo "unbekannt")
                echo -e "   📂 $subdir/: $SUB_PERMS"
            else
                echo -e "   📂 $subdir/: nicht vorhanden"
            fi
        done
        echo
    fi
done

# 2. Service-Status prüfen
echo -e "${BLUE}🔍 2. Prüfe Service-Status...${NC}"

# Prüfe Scandy Service
if systemctl is-active --quiet scandy; then
    echo -e "${GREEN}✅ Scandy Service läuft${NC}"
    
    # Prüfe Service-User
    SERVICE_USER=$(systemctl show scandy --property=User --value 2>/dev/null || echo "unbekannt")
    echo -e "   Service-User: $SERVICE_USER"
    
    # Prüfe Service-Logs
    echo -e "${BLUE}   📋 Letzte Service-Logs:${NC}"
    journalctl -u scandy --no-pager -n 5 2>/dev/null | tail -5 || echo "   Keine Logs verfügbar"
    
else
    echo -e "${RED}❌ Scandy Service läuft NICHT${NC}"
    echo -e "${BLUE}   📋 Service-Status:${NC}"
    systemctl status scandy --no-pager -l 2>/dev/null || echo "   Service-Status nicht verfügbar"
fi

# Prüfe Nginx Service
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx Service läuft${NC}"
else
    echo -e "${RED}❌ Nginx Service läuft NICHT${NC}"
fi

echo

# 3. Nginx-Konfiguration prüfen
echo -e "${BLUE}🔍 3. Prüfe Nginx-Konfiguration...${NC}"

if command -v nginx &> /dev/null; then
    # Prüfe Nginx-Konfiguration
    if nginx -t 2>/dev/null; then
        echo -e "${GREEN}✅ Nginx-Konfiguration ist gültig${NC}"
    else
        echo -e "${RED}❌ Nginx-Konfiguration hat Fehler${NC}"
        nginx -t 2>&1 | head -5
    fi
    
    # Prüfe Scandy-Konfiguration
    if [ -f "/etc/nginx/sites-available/scandy" ]; then
        echo -e "${BLUE}📄 Scandy Nginx-Konfiguration gefunden${NC}"
        
        # Prüfe Upload-Location
        if grep -q "location /uploads" /etc/nginx/sites-available/scandy; then
            echo -e "${GREEN}✅ Upload-Location konfiguriert${NC}"
            grep -A 3 "location /uploads" /etc/nginx/sites-available/scandy
        else
            echo -e "${YELLOW}⚠️  Upload-Location fehlt${NC}"
        fi
        
        # Prüfe Static-Location
        if grep -q "location /static" /etc/nginx/sites-available/scandy; then
            echo -e "${GREEN}✅ Static-Location konfiguriert${NC}"
        else
            echo -e "${YELLOW}⚠️  Static-Location fehlt${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Scandy Nginx-Konfiguration nicht gefunden${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Nginx nicht installiert${NC}"
fi

echo

# 4. Netzwerk-Verbindungen prüfen
echo -e "${BLUE}🔍 4. Prüfe Netzwerk-Verbindungen...${NC}"

# Prüfe Port 5000 (Flask)
if netstat -tlnp 2>/dev/null | grep -q ":5000"; then
    echo -e "${GREEN}✅ Port 5000 ist aktiv${NC}"
    netstat -tlnp 2>/dev/null | grep ":5000"
else
    echo -e "${RED}❌ Port 5000 ist NICHT aktiv${NC}"
fi

# Prüfe Port 80 (HTTP)
if netstat -tlnp 2>/dev/null | grep -q ":80"; then
    echo -e "${GREEN}✅ Port 80 ist aktiv${NC}"
    netstat -tlnp 2>/dev/null | grep ":80"
else
    echo -e "${RED}❌ Port 80 ist NICHT aktiv${NC}"
fi

# Prüfe HTTP-Verbindung
if command -v curl &> /dev/null; then
    echo -e "${BLUE}🌐 Teste HTTP-Verbindung...${NC}"
    
    # Teste localhost:5000
    if curl -s -I http://localhost:5000/health 2>/dev/null | grep -q "200"; then
        echo -e "${GREEN}✅ Flask-App erreichbar (localhost:5000)${NC}"
    else
        echo -e "${RED}❌ Flask-App NICHT erreichbar (localhost:5000)${NC}"
    fi
    
    # Teste localhost:80
    if curl -s -I http://localhost:80/ 2>/dev/null | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✅ Nginx erreichbar (localhost:80)${NC}"
    else
        echo -e "${RED}❌ Nginx NICHT erreichbar (localhost:80)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  curl nicht verfügbar - kann HTTP-Tests nicht durchführen${NC}"
fi

echo

# 5. Log-Dateien prüfen
echo -e "${BLUE}🔍 5. Prüfe Log-Dateien...${NC}"

# Prüfe Nginx-Logs
if [ -f "/var/log/nginx/error.log" ]; then
    echo -e "${BLUE}📋 Letzte Nginx-Fehler:${NC}"
    tail -5 /var/log/nginx/error.log 2>/dev/null || echo "   Keine Nginx-Fehler"
else
    echo -e "${YELLOW}⚠️  Nginx-Log nicht gefunden${NC}"
fi

# Prüfe Scandy-Logs
SCANDY_LOGS=(
    "/opt/scandy/app/logs"
    "/app/app/logs"
    "/var/log/scandy"
)

for log_dir in "${SCANDY_LOGS[@]}"; do
    if [ -d "$log_dir" ]; then
        echo -e "${BLUE}📋 Scandy-Logs in: $log_dir${NC}"
        find "$log_dir" -name "*.log" -type f -exec tail -3 {} \; 2>/dev/null | head -10 || echo "   Keine Logs gefunden"
    fi
done

echo

# 6. Docker-Container prüfen (falls verwendet)
echo -e "${BLUE}🔍 6. Prüfe Docker-Container...${NC}"

if command -v docker &> /dev/null && docker info &> /dev/null; then
    echo -e "${BLUE}🐳 Docker verfügbar${NC}"
    
    # Prüfe laufende Container
    RUNNING_CONTAINERS=$(docker ps --format "{{.Names}}" 2>/dev/null | grep scandy || echo "")
    if [ -n "$RUNNING_CONTAINERS" ]; then
        echo -e "${GREEN}✅ Laufende Scandy-Container:${NC}"
        echo "$RUNNING_CONTAINERS"
        
        # Prüfe Container-Logs
        for container in $RUNNING_CONTAINERS; do
            echo -e "${BLUE}📋 Logs für $container:${NC}"
            docker logs "$container" --tail 5 2>/dev/null || echo "   Keine Logs verfügbar"
        done
    else
        echo -e "${YELLOW}⚠️  Keine Scandy-Container laufen${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker nicht verfügbar${NC}"
fi

echo

# 7. System-Informationen
echo -e "${BLUE}🔍 7. System-Informationen...${NC}"

echo -e "${BLUE}📊 Speicherplatz:${NC}"
df -h /opt/scandy 2>/dev/null || df -h /app 2>/dev/null || echo "   Speicherplatz-Info nicht verfügbar"

echo -e "${BLUE}👤 Aktuelle Benutzer:${NC}"
id 2>/dev/null || echo "   Benutzer-Info nicht verfügbar"

echo -e "${BLUE}🐧 Betriebssystem:${NC}"
cat /etc/os-release 2>/dev/null | head -3 || echo "   OS-Info nicht verfügbar"

echo -e "${BLUE}🔧 Kernel:${NC}"
uname -a 2>/dev/null || echo "   Kernel-Info nicht verfügbar"

echo

# 8. Abschluss
echo -e "${GREEN}========================================"
echo -e "✅ Diagnose abgeschlossen!"
echo -e "========================================"
echo
echo -e "${BLUE}📋 Empfohlene Lösungen:${NC}"
echo -e "1. Führe das Upload-Fix-Skript aus: sudo ./fix_lxc_upload_permissions.sh"
echo -e "2. Starte Services neu: sudo systemctl restart scandy nginx"
echo -e "3. Prüfe Firewall-Einstellungen"
echo -e "4. Prüfe SELinux/AppArmor-Status"
echo -e "5. Prüfe Container-Netzwerk-Konfiguration"
echo
echo -e "${YELLOW}💡 Weitere Debug-Schritte:${NC}"
echo -e "   - Teste Upload mit curl: curl -X POST -F 'file=@test.jpg' http://localhost:5000/media/tickets/test/upload"
echo -e "   - Prüfe Flask-Logs: journalctl -u scandy -f"
echo -e "   - Prüfe Nginx-Logs: tail -f /var/log/nginx/error.log"
echo 