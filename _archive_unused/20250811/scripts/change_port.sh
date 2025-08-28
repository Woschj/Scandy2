#!/usr/bin/env bash
set -euo pipefail

# Scandy Port-Änderung - Ändert den Port einer bestehenden Installation
# Funktioniert ohne Neustart der gesamten Installation

echo "🔌 Scandy Port-Änderung - Ändere Port..."

# Prüfe Root-Rechte
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "❌ Bitte als root ausführen (sudo)"
    exit 1
fi

# Einfache Logging-Funktionen
log() { echo "[$(date '+%H:%M:%S')] $*"; }
success() { echo "✅ $*"; }
error() { echo "❌ $*"; }
info() { echo "ℹ️  $*"; }

# Prüfe ob Scandy installiert ist
if [ ! -d "/opt/scandy" ]; then
    error "Scandy ist nicht installiert!"
    exit 1
fi

if [ ! -f "/etc/systemd/system/scandy.service" ]; then
    error "Scandy-Service nicht gefunden!"
    exit 1
fi

# Aktuellen Port aus .env lesen
CURRENT_PORT="5001"
if [ -f "/opt/scandy/.env" ]; then
    if grep -q "WEB_PORT=" /opt/scandy/.env; then
        CURRENT_PORT=$(grep "WEB_PORT=" /opt/scandy/.env | cut -d'=' -f2)
    fi
fi

success "Aktueller Port: $CURRENT_PORT"

# Port-Auswahl
echo ""
echo "🌐 Neuer Port für Scandy:"
echo "1) Port 80 (Standard-HTTP, keine Port-Angabe in URL nötig)"
echo "2) Port 443 (Standard-HTTPS, keine Port-Angabe in URL nötig)"
echo "3) Port 5001 (Standard-Scandy-Port)"
echo "4) Benutzerdefinierter Port"
echo ""
read -p "Wähle neuen Port (1-4): " PORT_CHOICE

case $PORT_CHOICE in
    1)
        NEW_PORT=80
        PORT_NAME="Standard-HTTP"
        ;;
    2)
        NEW_PORT=443
        PORT_NAME="Standard-HTTPS"
        ;;
    3)
        NEW_PORT=5001
        PORT_NAME="Standard-Scandy"
        ;;
    4)
        read -p "Gib benutzerdefinierten Port ein (z.B. 8080): " NEW_PORT
        PORT_NAME="Benutzerdefiniert"
        ;;
    *)
        NEW_PORT=80
        PORT_NAME="Standard-HTTP (Standardauswahl)"
        ;;
esac

# Prüfe ob Port verfügbar ist
if [ "$NEW_PORT" = "80" ] || [ "$NEW_PORT" = "443" ]; then
    if ss -H -ltn 2>/dev/null | grep -q ":$NEW_PORT "; then
        error "Port $NEW_PORT ist bereits belegt!"
        info "Verwende stattdessen Port 5001"
        NEW_PORT=5001
        PORT_NAME="Standard-Scandy (Port 80/443 belegt)"
    fi
fi

if [ "$NEW_PORT" = "$CURRENT_PORT" ]; then
    info "Port ist bereits auf $NEW_PORT gesetzt - keine Änderung nötig"
    exit 0
fi

success "Ändere Port von $CURRENT_PORT auf $NEW_PORT ($PORT_NAME)"

# 1. Service stoppen
log "Stoppe Scandy-Service..."
systemctl stop scandy
sleep 2

# 2. .env aktualisieren
log "Aktualisiere .env-Datei..."
cd /opt/scandy

if [ -f ".env" ]; then
    if grep -q "WEB_PORT=" .env; then
        sed -i "s/WEB_PORT=.*/WEB_PORT=$NEW_PORT/" .env
        success "WEB_PORT in .env auf $NEW_PORT aktualisiert"
    else
        echo "WEB_PORT=$NEW_PORT" >> .env
        success "WEB_PORT=$NEW_PORT zu .env hinzugefügt"
    fi
else
    # Erstelle .env neu falls nicht vorhanden
            cat > .env << EOF
# Scandy - Einfache Konfiguration
WEB_PORT=$NEW_PORT
MONGODB_URI=mongodb://localhost:27017/scandy
MONGODB_DB=scandy
SECRET_KEY=scandy_secret_key_123
FLASK_ENV=production
SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
EOF
        success ".env-Datei erstellt mit WEB_PORT=$NEW_PORT"
fi

# 3. Firewall aktualisieren
log "Aktualisiere Firewall..."
if command -v ufw >/dev/null 2>&1; then
    # Alten Port schließen
    ufw deny $CURRENT_PORT/tcp >/dev/null 2>&1 || true
    info "Port $CURRENT_PORT geschlossen"
    
    # Neuen Port öffnen
    ufw allow $NEW_PORT/tcp >/dev/null 2>&1 || true
    success "Port $NEW_PORT freigegeben"
fi

# 4. Service neu starten
log "Starte Service mit neuem Port..."
systemctl daemon-reload
systemctl restart scandy

# 5. Warten auf App-Start
log "Warte auf App-Start auf Port $NEW_PORT..."
for i in {1..30}; do
    if ss -H -ltn 2>/dev/null | grep -q ":$NEW_PORT "; then
        success "Scandy läuft auf Port $NEW_PORT"
        break
    fi
    
    if [ $i -eq 30 ]; then
        error "App startet nicht auf Port $NEW_PORT"
        
        # Rollback
        log "Rollback auf Port $CURRENT_PORT..."
        sed -i "s/WEB_PORT=.*/WEB_PORT=$CURRENT_PORT/" .env
        ufw deny $NEW_PORT/tcp >/dev/null 2>&1 || true
        ufw allow $CURRENT_PORT/tcp >/dev/null 2>&1 || true
        systemctl restart scandy
        error "Rollback abgeschlossen - App läuft wieder auf Port $CURRENT_PORT"
        exit 1
    fi
    
    sleep 2
done

# 6. Fertig!
echo ""
success "Port-Änderung abgeschlossen!"
echo "🌐 Web-App: http://$(hostname -I | awk '{print $1}'):$NEW_PORT"
echo "📝 Logs: journalctl -u scandy -f"
echo ""
echo "Port erfolgreich von $CURRENT_PORT auf $NEW_PORT geändert! 🎯" 