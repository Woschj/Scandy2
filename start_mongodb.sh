#!/usr/bin/env bash

echo "🔧 MongoDB Start-Script..."
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte mit sudo ausführen: sudo bash start_mongodb.sh"
    exit 1
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }
ok() { echo "✅ $*"; }

# 1. Stoppe alle MongoDB-Prozesse
log "Stoppe alle MongoDB-Prozesse..."
pkill -9 mongod 2>/dev/null || true
pkill -9 mongo 2>/dev/null || true
sleep 2
ok "Alle Prozesse gestoppt"

# 2. Entferne Lockfiles
log "Entferne Lockfiles..."
rm -f /var/lib/mongodb/mongod.lock 2>/dev/null || true
rm -f /var/lib/mongodb/WiredTiger.lock 2>/dev/null || true
ok "Lockfiles entfernt"

# 3. Stelle sicher dass Verzeichnisse existieren
log "Prüfe Verzeichnisse..."
mkdir -p /var/lib/mongodb
mkdir -p /var/log/mongodb
chown -R mongodb:mongodb /var/lib/mongodb
chown -R mongodb:mongodb /var/log/mongodb
ok "Verzeichnisse bereit"

# 4. Versuche systemd Start
log "Versuche systemd Start..."
if systemctl start mongod 2>&1; then
    ok "MongoDB per systemd gestartet"
    sleep 2
    
    if systemctl is-active --quiet mongod; then
        ok "MongoDB läuft (via systemd)"
        exit 0
    fi
fi

# 5. Fallback: Manueller Start
log "Systemd Start fehlgeschlagen - starte manuell..."
log "Starte mongod im Hintergrund..."

# Finde mongod
MONGODB_BIN=$(which mongod)
if [ -z "$MONGODB_BIN" ]; then
    echo "❌ mongod wurde nicht gefunden!"
    echo "Bitte installieren: apt install -y mongodb-server"
    exit 1
fi

# Starte manuell
nohup "$MONGODB_BIN" \
    --fork \
    --logpath /var/log/mongodb/mongod.log \
    --dbpath /var/lib/mongodb \
    --bind_ip 0.0.0.0 \
    2>&1 &

sleep 3

# Prüfe ob läuft
if pgrep mongod >/dev/null 2>&1; then
    ok "MongoDB läuft manuell"
    
    PID=$(pgrep mongod)
    echo "MongoDB PID: $PID"
    
    # Zeige ob Port offen ist
    if ss -tln | grep -q ':27017 '; then
        ok "MongoDB hört auf Port 27017"
    else
        echo "⚠️  Port 27017 nicht offen"
    fi
else
    echo "❌ MongoDB konnte nicht gestartet werden"
    echo "Logs:"
    tail -30 /var/log/mongodb/mongod.log 2>&1 || echo "Keine Logs verfügbar"
    exit 1
fi

# 6. Teste Verbindung
log "Teste MongoDB Verbindung..."
sleep 1
if mongosh --quiet --eval "db.adminCommand('ping')" 2>/dev/null | grep -q "ok"; then
    ok "MongoDB reagiert auf Ping"
else
    echo "⚠️  MongoDB läuft, aber Ping fehlgeschlagen"
fi

echo ""
echo "🎉 MongoDB sollte jetzt laufen!"
echo "Status:"
echo "  - PID: $(pgrep mongod)"
echo "  - Port: $(ss -tln | grep ':27017 ' || echo 'nicht geöffnet')"
echo ""

