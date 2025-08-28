#!/usr/bin/env bash
set -euo pipefail

# Einfaches Scandy-Reparatur-Script
# Funktioniert immer - repariert bestehende Installation

echo "🔧 Scandy Simple Fix - Repariere Installation..."

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
pkill -f "app.wsgi" 2>/dev/null || true
sleep 3

# 2. Prüfe Verzeichnis
if [ ! -d "/opt/scandy" ]; then
    error "Scandy ist nicht installiert. Verwende install_scandy_simple_new.sh"
    exit 1
fi

# 3. Wechsle zu /opt/scandy
cd /opt/scandy

# 4. Prüfe ob app/wsgi.py existiert
if [ ! -f "app/wsgi.py" ]; then
    error "app/wsgi.py nicht gefunden!"
    ls -la app/ 2>/dev/null || echo "App-Verzeichnis nicht gefunden"
    exit 1
fi

# 5. Aktiviere Virtualenv
if [ ! -d "venv" ]; then
    error "Virtualenv nicht gefunden!"
    exit 1
fi

source venv/bin/activate

# 6. Teste ob Gunicorn funktioniert
log "Teste Gunicorn..."
if ! venv/bin/gunicorn --version >/dev/null 2>&1; then
    error "Gunicorn nicht verfügbar!"
    exit 1
fi

# 7. Starte App manuell
log "Starte Scandy manuell..."
nohup venv/bin/gunicorn --bind 0.0.0.0:80 --workers 2 --timeout 120 --chdir /opt/scandy app.wsgi:app > /var/log/scandy.log 2>&1 &
SCANDY_PID=$!
echo $SCANDY_PID > /var/run/scandy.pid

# 8. Warte und prüfe
log "Warte auf App-Start..."
sleep 5

if kill -0 $SCANDY_PID 2>/dev/null; then
    success "Scandy läuft manuell (PID: $SCANDY_PID)"
    
    # Prüfe Port
    if ss -H -ltn 2>/dev/null | grep -q ":80 "; then
        success "Port 80 ist aktiv"
    else
        error "Port 80 ist nicht aktiv"
    fi
    
    # Zeige Logs
    log "Aktuelle Logs:"
    tail -10 /var/log/scandy.log 2>/dev/null || echo "Keine Logs verfügbar"
    
    echo ""
    success "Scandy läuft auf Port 80!"
    echo "🌐 Web-App: http://$(hostname -I | awk '{print $1}'):80"
    echo "📝 Logs: tail -f /var/log/scandy.log"
    echo "🔄 Neustart: kill $SCANDY_PID && ./fix_scandy_simple.sh"
    
else
    error "App startet nicht"
    log "Logs:"
    tail -20 /var/log/scandy.log 2>/dev/null || echo "Keine Logs verfügbar"
    exit 1
fi
