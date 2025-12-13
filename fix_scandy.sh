#!/usr/bin/env bash

echo "🔧 Scandy Reparatur - Starte..."
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte mit sudo ausführen"
    exit 1
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }
ok() { echo "✅ $*"; }

# 1. Stoppe alles
log "Stoppe Scandy und MongoDB..."
systemctl stop scandy 2>/dev/null || true
systemctl stop mongod 2>/dev/null || true
pkill -9 mongod 2>/dev/null || true
pkill -9 gunicorn 2>/dev/null || true
sleep 2
ok "Alles gestoppt"

# 2. Lösche altes venv
log "Lösche altes venv..."
rm -rf /opt/scandy/venv
ok "Altes venv gelöscht"

# 3. Erstelle neues venv
log "Erstelle neues venv..."
cd /opt/scandy
python3 -m venv venv
ok "Neues venv erstellt"

# 4. Installiere Requirements
log "Installiere Python-Pakete..."
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
deactivate
ok "Python-Pakete installiert"

# 5. Korrigiere Berechtigungen
log "Korrigiere Berechtigungen..."
chown -R root:root /opt/scandy
chmod -R 755 /opt/scandy
ok "Berechtigungen korrigiert"

# 6. Starte MongoDB
log "Starte MongoDB..."
# Erstelle Config falls nicht vorhanden
mkdir -p /var/lib/mongodb /var/log/mongodb

# Versuche systemd
if systemctl start mongod 2>/dev/null; then
    ok "MongoDB per systemd gestartet"
elif mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /var/lib/mongodb 2>/dev/null; then
    ok "MongoDB manuell gestartet"
else
    log "MongoDB konnte nicht gestartet werden"
fi

sleep 2

# 7. Starte Scandy
log "Starte Scandy..."
systemctl daemon-reload
systemctl restart scandy
sleep 3

# 8. Prüfe Status
log "Prüfe Status..."
if systemctl is-active --quiet scandy; then
    ok "Scandy läuft"
else
    echo "⚠️  Scandy läuft nicht - prüfe Logs:"
    journalctl -u scandy -n 20
fi

if pgrep mongod >/dev/null; then
    ok "MongoDB läuft"
else
    echo "⚠️  MongoDB läuft nicht"
fi

echo ""
echo "🎉 Reparatur abgeschlossen!"
echo "🌐 Zugriff: http://$(hostname -I | awk '{print $1}')"
echo "📝 Scandy-Logs: journalctl -u scandy -f"
echo ""

