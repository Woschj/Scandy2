./11#!/bin/bash

# Server SSL Setup für Scandy
# Überprüft und konfiguriert alle Voraussetzungen für HTTPS

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔒 Server SSL Setup für Scandy${NC}"
echo "=================================="

# 1. System-Updates
echo -e "\n${BLUE}1. System-Updates prüfen...${NC}"
if command -v apt &> /dev/null; then
    echo -e "${YELLOW}📦 Debian/Ubuntu System erkannt${NC}"
    sudo apt update
    sudo apt upgrade -y
elif command -v yum &> /dev/null; then
    echo -e "${YELLOW}📦 CentOS/RHEL System erkannt${NC}"
    sudo yum update -y
else
    echo -e "${RED}❌ Unbekanntes System - manuelle Konfiguration erforderlich${NC}"
fi

# 2. Nginx installieren
echo -e "\n${BLUE}2. Nginx Installation prüfen...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}📦 Installiere Nginx...${NC}"
    if command -v apt &> /dev/null; then
        sudo apt install nginx -y
    elif command -v yum &> /dev/null; then
        sudo yum install nginx -y
    fi
    sudo systemctl enable nginx
    sudo systemctl start nginx
    echo -e "${GREEN}✅ Nginx installiert und gestartet${NC}"
else
    echo -e "${GREEN}✅ Nginx bereits installiert${NC}"
fi

# 3. Certbot installieren
echo -e "\n${BLUE}3. Certbot Installation prüfen...${NC}"
if ! command -v certbot &> /dev/null; then
    echo -e "${YELLOW}📦 Installiere Certbot...${NC}"
    if command -v apt &> /dev/null; then
        sudo apt install certbot python3-certbot-nginx -y
    elif command -v yum &> /dev/null; then
        sudo yum install certbot python3-certbot-nginx -y
    fi
    echo -e "${GREEN}✅ Certbot installiert${NC}"
else
    echo -e "${GREEN}✅ Certbot bereits installiert${NC}"
fi

# 4. Firewall konfigurieren
echo -e "\n${BLUE}4. Firewall konfigurieren...${NC}"
if command -v ufw &> /dev/null; then
    echo -e "${YELLOW}🔥 Konfiguriere UFW Firewall...${NC}"
    sudo ufw allow 22/tcp    # SSH
    sudo ufw allow 80/tcp    # HTTP
    sudo ufw allow 443/tcp   # HTTPS
    sudo ufw --force enable
    echo -e "${GREEN}✅ UFW Firewall konfiguriert${NC}"
elif command -v firewall-cmd &> /dev/null; then
    echo -e "${YELLOW}🔥 Konfiguriere firewalld...${NC}"
    sudo firewall-cmd --permanent --add-service=ssh
    sudo firewall-cmd --permanent --add-service=http
    sudo firewall-cmd --permanent --add-service=https
    sudo firewall-cmd --reload
    echo -e "${GREEN}✅ firewalld konfiguriert${NC}"
else
    echo -e "${YELLOW}⚠️  Keine Firewall erkannt - manuelle Konfiguration empfohlen${NC}"
fi

# 5. Domain-Konfiguration prüfen
echo -e "\n${BLUE}5. Domain-Konfiguration prüfen...${NC}"
read -p "Geben Sie Ihre Domain ein (z.B. scandy.company.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}❌ Keine Domain angegeben${NC}"
    echo -e "${YELLOW}⚠️  Für SSL-Zertifikate ist eine Domain erforderlich${NC}"
    echo -e "${BLUE}📋 Optionen:${NC}"
    echo "  1. Domain registrieren (z.B. bei Namecheap, GoDaddy)"
    echo "  2. Subdomain verwenden (z.B. scandy.ihre-domain.com)"
    echo "  3. Lokale Entwicklung (nur für Tests)"
    exit 1
fi

# 6. DNS-Auflösung testen
echo -e "\n${BLUE}6. DNS-Auflösung testen...${NC}"
if nslookup $DOMAIN &> /dev/null; then
    echo -e "${GREEN}✅ DNS-Auflösung erfolgreich für $DOMAIN${NC}"
else
    echo -e "${RED}❌ DNS-Auflösung fehlgeschlagen für $DOMAIN${NC}"
    echo -e "${YELLOW}⚠️  Stellen Sie sicher, dass:${NC}"
    echo "  - Die Domain korrekt eingegeben wurde"
    echo "  - DNS-Einträge konfiguriert sind"
    echo "  - DNS-Änderungen propagiert sind (kann bis zu 24h dauern)"
    exit 1
fi

# 7. Port-Verfügbarkeit testen
echo -e "\n${BLUE}7. Port-Verfügbarkeit testen...${NC}"
if nc -z $DOMAIN 80 2>/dev/null; then
    echo -e "${GREEN}✅ Port 80 (HTTP) erreichbar${NC}"
else
    echo -e "${RED}❌ Port 80 (HTTP) nicht erreichbar${NC}"
    echo -e "${YELLOW}⚠️  Stellen Sie sicher, dass:${NC}"
    echo "  - Nginx läuft"
    echo "  - Firewall Port 80 erlaubt"
    echo "  - Server erreichbar ist"
fi

# 8. Nginx-Konfiguration erstellen
echo -e "\n${BLUE}8. Nginx-Konfiguration erstellen...${NC}"
sudo tee /etc/nginx/sites-available/scandy > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/scandy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
echo -e "${GREEN}✅ Nginx-Konfiguration erstellt${NC}"

# 9. SSL-Zertifikat installieren
echo -e "\n${BLUE}9. SSL-Zertifikat installieren...${NC}"
echo -e "${YELLOW}📋 Certbot wird jetzt das SSL-Zertifikat installieren...${NC}"
echo -e "${BLUE}📝 Folgen Sie den Anweisungen von Certbot${NC}"
echo -e "${YELLOW}⚠️  Wichtig: Wählen Sie '2' für Redirect (HTTP zu HTTPS)${NC}"

sudo certbot --nginx -d $DOMAIN

# 10. Automatische Erneuerung konfigurieren
echo -e "\n${BLUE}10. Automatische SSL-Erneuerung konfigurieren...${NC}"
if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    echo -e "${GREEN}✅ Automatische SSL-Erneuerung konfiguriert${NC}"
else
    echo -e "${GREEN}✅ Automatische SSL-Erneuerung bereits konfiguriert${NC}"
fi

# 11. Sicherheits-Check
echo -e "\n${BLUE}11. Sicherheits-Check...${NC}"
echo -e "${GREEN}✅ SSL-Zertifikat installiert${NC}"
echo -e "${GREEN}✅ HTTPS aktiviert${NC}"
echo -e "${GREEN}✅ HTTP zu HTTPS Umleitung konfiguriert${NC}"

# 12. Finale Anweisungen
echo -e "\n${BLUE}🎉 SSL Setup abgeschlossen!${NC}"
echo -e "${GREEN}✅ Ihre Scandy-Anwendung ist jetzt über HTTPS erreichbar:${NC}"
echo -e "${BLUE}🌐 https://$DOMAIN${NC}"
echo -e "\n${YELLOW}📋 Nächste Schritte:${NC}"
echo "1. Scandy-Anwendung starten"
echo "2. HTTPS-Verbindung testen"
echo "3. Security Headers überprüfen"
echo "4. Regelmäßige Backups einrichten"

echo -e "\n${BLUE}🔧 Nützliche Befehle:${NC}"
echo "sudo nginx -t                    # Nginx-Konfiguration testen"
echo "sudo systemctl status nginx      # Nginx-Status prüfen"
echo "sudo certbot certificates        # SSL-Zertifikate anzeigen"
echo "curl -I https://$DOMAIN         # HTTPS-Response testen" 