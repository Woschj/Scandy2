#!/bin/bash

# Lokales SSL Setup für Scandy (ohne Domain)
# Erstellt selbst-signierte Zertifikate für lokale Entwicklung

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔒 Lokales SSL Setup für Scandy${NC}"
echo "======================================"

# 1. Verzeichnisse erstellen
echo -e "\n${BLUE}1. SSL-Verzeichnisse erstellen...${NC}"
sudo mkdir -p /etc/ssl/scandy
sudo mkdir -p /etc/nginx/sites-available
sudo mkdir -p /etc/nginx/sites-enabled

# 2. Selbst-signiertes Zertifikat erstellen
echo -e "\n${BLUE}2. Selbst-signiertes SSL-Zertifikat erstellen...${NC}"

# Server-IP ermitteln
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "${YELLOW}📋 Server-IP: $SERVER_IP${NC}"

# Zertifikat erstellen
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/scandy/scandy.key \
    -out /etc/ssl/scandy/scandy.crt \
    -subj "/C=DE/ST=Germany/L=Local/O=Scandy/OU=IT/CN=$SERVER_IP" \
    -addext "subjectAltName=DNS:localhost,DNS:$SERVER_IP,IP:$SERVER_IP,IP:127.0.0.1"

echo -e "${GREEN}✅ SSL-Zertifikat erstellt${NC}"

# 3. Nginx installieren (falls nicht vorhanden)
echo -e "\n${BLUE}3. Nginx Installation prüfen...${NC}"
if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}📦 Installiere Nginx...${NC}"
    if command -v apt &> /dev/null; then
        sudo apt update
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

# 4. Nginx-Konfiguration für lokales HTTPS
echo -e "\n${BLUE}4. Nginx-Konfiguration für lokales HTTPS...${NC}"

sudo tee /etc/nginx/sites-available/scandy-local > /dev/null <<EOF
# HTTP zu HTTPS Umleitung
server {
    listen 80;
    server_name $SERVER_IP localhost;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS Server mit selbst-signiertem Zertifikat
server {
    listen 443 ssl http2;
    server_name $SERVER_IP localhost;
    
    # SSL-Konfiguration
    ssl_certificate /etc/ssl/scandy/scandy.crt;
    ssl_certificate_key /etc/ssl/scandy/scandy.key;
    
    # SSL-Sicherheitseinstellungen
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'" always;
    # Kamera erlauben
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=(self)" always;
    
    # Proxy-Einstellungen für Scandy
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        
        # Timeout-Einstellungen
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer-Einstellungen
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Static Files (mit Cache)
    location /static/ {
        proxy_pass http://localhost:5000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Uploads (mit Sicherheitseinschränkungen)
    location /uploads/ {
        proxy_pass http://localhost:5000;
        # Verhindere Ausführung von Dateien
        location ~* \.(php|pl|py|jsp|asp|sh|cgi)$ {
            deny all;
        }
    }
    
    # Health Check (ohne Security Headers)
    location /health {
        proxy_pass http://localhost:5000;
        access_log off;
    }
    
    # Verstecke Server-Informationen
    server_tokens off;
    
    # Rate Limiting
    limit_req_zone \$binary_remote_addr zone=scandy:10m rate=10r/s;
    limit_req zone=scandy burst=20 nodelay;
    
    # Logging
    access_log /var/log/nginx/scandy_access.log;
    error_log /var/log/nginx/scandy_error.log;
}
EOF

# 5. Nginx-Konfiguration aktivieren
echo -e "\n${BLUE}5. Nginx-Konfiguration aktivieren...${NC}"
sudo ln -sf /etc/nginx/sites-available/scandy-local /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
echo -e "${GREEN}✅ Nginx-Konfiguration aktiviert${NC}"

# 6. Firewall konfigurieren
echo -e "\n${BLUE}6. Firewall konfigurieren...${NC}"
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

# 7. Zertifikat in Browser importieren (Anleitung)
echo -e "\n${BLUE}7. Browser-Zertifikat Setup...${NC}"
echo -e "${YELLOW}📋 WICHTIG: Sie müssen das Zertifikat in Ihrem Browser importieren${NC}"
echo -e "${BLUE}📝 Anleitung:${NC}"
echo "1. Öffnen Sie: https://$SERVER_IP"
echo "2. Klicken Sie auf 'Erweitert' → 'Zur Website'"
echo "3. Klicken Sie auf das Schloss-Symbol → 'Zertifikat anzeigen'"
echo "4. Exportieren Sie das Zertifikat als .crt Datei"
echo "5. Importieren Sie es in Ihren Browser unter 'Vertrauenswürdige Zertifikate'"

# 8. Scandy-Konfiguration anpassen
echo -e "\n${BLUE}8. Scandy-Konfiguration anpassen...${NC}"
echo -e "${YELLOW}📋 Passen Sie die PHP-Dateien an:${NC}"
echo "Ändern Sie in allen PHP-Dateien:"
echo "  \$scandy_api_url = 'https://$SERVER_IP';"

# 9. Finale Anweisungen
echo -e "\n${BLUE}🎉 Lokales SSL Setup abgeschlossen!${NC}"
echo -e "${GREEN}✅ Ihre Scandy-Anwendung ist jetzt über HTTPS erreichbar:${NC}"
echo -e "${BLUE}🌐 https://$SERVER_IP${NC}"
echo -e "${BLUE}🌐 https://localhost${NC}"

echo -e "\n${YELLOW}⚠️  WICHTIGE HINWEISE:${NC}"
echo "1. Das Zertifikat ist selbst-signiert - Browser zeigen Warnung"
echo "2. Importieren Sie das Zertifikat in Ihren Browser"
echo "3. Für Produktion: Verwenden Sie eine echte Domain mit Let's Encrypt"

echo -e "\n${BLUE}🔧 Nützliche Befehle:${NC}"
echo "sudo nginx -t                    # Nginx-Konfiguration testen"
echo "sudo systemctl status nginx      # Nginx-Status prüfen"
echo "curl -k https://$SERVER_IP       # HTTPS-Response testen (mit -k für selbst-signiert)"
echo "sudo tail -f /var/log/nginx/error.log  # Nginx-Logs anzeigen"

echo -e "\n${GREEN}✅ Setup abgeschlossen!${NC}" 