#!/usr/bin/env bash

# Scandy Simplified Installer - Robuste Version
# Fokus auf Zuverlässigkeit statt Features

set -x  # Zeige alle Befehle
set -e  # Beende bei Fehlern

echo "🚀 Scandy Installer - Starte Installation..."

# Prüfe Root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte mit sudo ausführen"
    exit 1
fi

# Einfache Logging
log() { echo "[$(date '+%H:%M:%S')] $*"; }
ok() { echo "✅ $*"; }
err() { echo "❌ $*"; }

# Warte auf apt falls nötig
wait_apt() {
    for i in {1..30}; do
        if ! fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock 2>/dev/null; then
            return 0
        fi
        [ $i -eq 1 ] && log "Warte auf apt-Sperre..."
        sleep 1
    done
    
    # Aggressives Lösen der Sperre
    log "Löse apt-Sperre..."
    pkill -9 apt apt-get dpkg 2>/dev/null || true
    rm -f /var/lib/apt/lists/lock /var/lib/dpkg/lock* 2>/dev/null || true
    sleep 2
}

# ===== SCHRITT 1: System-Pakete =====
log "Schritt 1/7: Installiere System-Pakete..."

wait_apt

# Installiere nur essentielle Pakete einzeln
apt update -y
apt install -y python3 || { err "Python3 Installation fehlgeschlagen"; exit 1; }
apt install -y python3-pip || { err "pip Installation fehlgeschlagen"; exit 1; }
apt install -y python3-venv || { err "venv Installation fehlgeschlagen"; exit 1; }
apt install -y git curl wget rsync || { err "Tools Installation fehlgeschlagen"; exit 1; }

ok "System-Pakete installiert"

# ===== SCHRITT 2: MongoDB =====
log "Schritt 2/7: Installiere MongoDB..."

# Prüfe ob schon installiert
if command -v mongod >/dev/null 2>&1; then
    ok "MongoDB bereits installiert"
else
    # Installiere MongoDB mit einfachem Ansatz
    if ! apt install -y mongodb-server mongodb-clients 2>/dev/null; then
        err "MongoDB konnte nicht installiert werden"
        err "Bitte manuell installieren:"
        err "  sudo apt update"
        err "  sudo apt install -y mongodb-server"
        err "  sudo systemctl start mongod"
        exit 1
    fi
    ok "MongoDB installiert"
fi

# Starte MongoDB
log "Starte MongoDB..."
systemctl stop mongod 2>/dev/null || true
pkill -9 mongod 2>/dev/null || true
sleep 2

if ! systemctl start mongod; then
    # Fallback: Starte manuell
    mongod --fork --logpath /var/log/mongodb/mongod.log --dbpath /var/lib/mongodb 2>/dev/null || true
fi

# Warte auf MongoDB
log "Warte auf MongoDB..."
for i in {1..30}; do
    if pgrep mongod >/dev/null; then
        ok "MongoDB läuft"
        break
    fi
    sleep 1
done

# ===== SCHRITT 3: Scandy Code =====
log "Schritt 3/7: Kopiere Scandy Code..."

mkdir -p /opt/scandy

# Finde Quelle
SOURCE_DIR=""
if [ -d "/home/$(whoami)/Scandy2" ]; then
    SOURCE_DIR="/home/$(whoami)/Scandy2"
elif [ -d "/home/woschj/Scandy2" ]; then
    SOURCE_DIR="/home/woschj/Scandy2"
elif [ -d "$PWD/app" ]; then
    SOURCE_DIR="$PWD"
else
    err "Scandy Code nicht gefunden!"
    exit 1
fi

log "Kopiere von $SOURCE_DIR nach /opt/scandy..."

# Kopiere ohne venv
rsync -av --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.git' --exclude='node_modules' \
    "$SOURCE_DIR/" /opt/scandy/ 2>/dev/null || {
    # Fallback: cp ohne rsync
    find "$SOURCE_DIR" -maxdepth 1 ! -name "venv" ! -name "__pycache__" ! -name "*.pyc" \
        ! -name ".git" ! -name "node_modules" -exec cp -r {} /opt/scandy/ \; 2>/dev/null
}

ok "Code kopiert"

# ===== SCHRITT 4: Python venv =====
log "Schritt 4/7: Erstelle Python Umgebung..."

cd /opt/scandy
rm -rf venv  # Entferne altes venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
ok "Python Umgebung erstellt"

# ===== SCHRITT 5: Konfiguration =====
log "Schritt 5/7: Erstelle Konfiguration..."

cat > /opt/scandy/.env << EOF
WEB_PORT=80
MONGODB_URI=mongodb://localhost:27017/scandy
MONGODB_DB=scandy
SECRET_KEY=scandy_secret_key_change_in_production
FLASK_ENV=production
SESSION_TYPE=filesystem
EOF

ok "Konfiguration erstellt"

# ===== SCHRITT 6: Service =====
log "Schritt 6/7: Erstelle Systemd Service..."

mkdir -p /opt/scandy/bin

cat > /opt/scandy/bin/prestart.sh << 'EOFPRE'
#!/bin/bash
set -e
mkdir -p /opt/scandy/app/flask_session
chown -R root:root /opt/scandy/app/flask_session
chmod 755 /opt/scandy/app/flask_session
EOFPRE

cat > /opt/scandy/bin/start.sh << 'EOFSTART'
#!/bin/bash
set -e
cd /opt/scandy
source venv/bin/activate
export PATH="/opt/scandy/venv/bin:$PATH"
exec gunicorn --bind 0.0.0.0:80 --workers 2 --timeout 120 app.wsgi:app
EOFSTART

chmod +x /opt/scandy/bin/*.sh

cat > /etc/systemd/system/scandy.service << EOFSVC
[Unit]
Description=Scandy Application
After=network.target mongod.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/scandy
EnvironmentFile=/opt/scandy/.env
ExecStart=/opt/scandy/bin/start.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOFSVC

systemctl daemon-reload
systemctl enable scandy

ok "Service erstellt"

# ===== SCHRITT 7: Start =====
log "Schritt 7/7: Starte Services..."

systemctl restart mongod || true
sleep 2
systemctl restart scandy || true

log "Warte auf App-Start..."
for i in {1..30}; do
    if systemctl is-active --quiet scandy; then
        ok "Scandy läuft!"
        break
    fi
    sleep 1
done

# ===== FERTIG =====
echo ""
echo "🎉 Installation abgeschlossen!"
echo "🌐 Zugriff: http://$(hostname -I | awk '{print $1}')"
echo "📝 Logs: journalctl -u scandy -f"
echo ""

