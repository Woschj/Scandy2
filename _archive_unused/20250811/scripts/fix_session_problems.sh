#!/usr/bin/env bash
set -euo pipefail

# Scandy Session-Reparatur-Script
# Behebt alle Login- und Session-Probleme

echo "🔧 Scandy Session-Reparatur - Behebe Login-Probleme..."

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

# 1. Stoppe alle Services
log "Stoppe alle Services..."
systemctl stop scandy 2>/dev/null || true
pkill -f gunicorn 2>/dev/null || true
sleep 3

# 2. Prüfe Verzeichnis
if [ ! -d "/opt/scandy" ]; then
    error "Scandy ist nicht installiert!"
    exit 1
fi

cd /opt/scandy

# 3. Erstelle Session-Verzeichnis
log "Erstelle Session-Verzeichnis..."
mkdir -p app/flask_session
chmod 755 app/flask_session
chown -R root:root app/flask_session

# 4. Korrigiere .env-Datei
log "Korrigiere .env-Datei..."
if [ -f ".env" ]; then
    # Backup erstellen
    cp .env .env.backup.session_fix
    
    # Session-Einstellungen korrigieren
    sed -i 's/FLASK_ENV=.*/FLASK_ENV=production/' .env
    sed -i 's/SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=false/' .env
    sed -i 's/REMEMBER_COOKIE_SECURE=.*/REMEMBER_COOKIE_SECURE=false/' .env
    sed -i 's/SESSION_COOKIE_SAMESITE=.*/SESSION_COOKIE_SAMESITE=Lax/' .env
    sed -i 's/REMEMBER_COOKIE_SAMESITE=.*/REMEMBER_COOKIE_SAMESITE=Lax/' .env
    
    # Fehlende Einstellungen hinzufügen
    if ! grep -q "SESSION_COOKIE_HTTPONLY" .env; then
        echo "SESSION_COOKIE_HTTPONLY=true" >> .env
    fi
    if ! grep -q "REMEMBER_COOKIE_HTTPONLY" .env; then
        echo "REMEMBER_COOKIE_HTTPONLY=true" >> .env
    fi
    if ! grep -q "SESSION_TYPE" .env; then
        echo "SESSION_TYPE=filesystem" >> .env
    fi
    if ! grep -q "PERMANENT_SESSION_LIFETIME" .env; then
        echo "PERMANENT_SESSION_LIFETIME=604800" >> .env
    fi
    
    success ".env-Datei korrigiert"
else
    error ".env-Datei nicht gefunden!"
    exit 1
fi

# 5. Lösche alte Session-Dateien
log "Lösche alte Session-Dateien..."
rm -rf app/flask_session/*
rm -rf instance/flask_session/* 2>/dev/null || true
success "Alte Sessions gelöscht"

# 6. Aktiviere Virtualenv
if [ ! -d "venv" ]; then
    error "Virtualenv nicht gefunden!"
    exit 1
fi

source venv/bin/activate

# 7. Teste Session-Konfiguration
log "Teste Session-Konfiguration..."
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()

print(f'FLASK_ENV: {os.getenv(\"FLASK_ENV\")}')
print(f'SESSION_COOKIE_SECURE: {os.getenv(\"SESSION_COOKIE_SECURE\")}')
print(f'SESSION_COOKIE_SAMESITE: {os.getenv(\"SESSION_COOKIE_SAMESITE\")}')
print(f'SESSION_TYPE: {os.getenv(\"SESSION_TYPE\")}')
"

# 8. Starte App mit Session-Debug
log "Starte App mit Session-Debug..."
nohup venv/bin/gunicorn --bind 0.0.0.0:80 --workers 2 --timeout 120 --chdir /opt/scandy app.wsgi:app > /var/log/scandy_session_fix.log 2>&1 &
SCANDY_PID=$!
echo $SCANDY_PID > /var/run/scandy_session_fix.pid

# 9. Warte und prüfe
log "Warte auf App-Start..."
sleep 5

if kill -0 $SCANDY_PID 2>/dev/null; then
    success "Scandy läuft mit Session-Fix (PID: $SCANDY_PID)"
    
    # Prüfe Port
    if ss -H -ltn 2>/dev/null | grep -q ":80 "; then
        success "Port 80 ist aktiv"
    else
        error "Port 80 ist nicht aktiv"
    fi
    
    # Zeige Logs
    log "Aktuelle Logs:"
    tail -10 /var/log/scandy_session_fix.log 2>/dev/null || echo "Keine Logs verfügbar"
    
    echo ""
    success "Session-Probleme behoben!"
    echo "🌐 Web-App: http://$(hostname -I | awk '{print $1}'):80"
    echo "📝 Logs: tail -f /var/log/scandy_session_fix.log"
    echo "🔄 Neustart: kill $SCANDY_PID && ./fix_session_problems.sh"
    echo ""
    echo "Jetzt sollte der Login funktionieren! 🎯"
    
else
    error "App startet nicht"
    log "Logs:"
    tail -20 /var/log/scandy_session_fix.log 2>/dev/null || echo "Keine Logs verfügbar"
    exit 1
fi
