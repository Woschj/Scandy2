#!/usr/bin/env bash

# dpkg Reparatur-Script
# Behebt unterbrochene dpkg/apt-Prozesse

echo "🔧 dpkg Reparatur - Starte..."

if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte mit sudo ausführen"
    exit 1
fi

log() { echo "[$(date '+%H:%M:%S')] $*"; }
ok() { echo "✅ $*"; }

log "Schritt 1: Beende alle apt/dpkg Prozesse..."
pkill -9 apt 2>/dev/null || true
pkill -9 apt-get 2>/dev/null || true
pkill -9 dpkg 2>/dev/null || true
sleep 2
ok "Prozesse beendet"

log "Schritt 2: Entferne Lock-Dateien..."
rm -f /var/lib/apt/lists/lock 2>/dev/null || true
rm -f /var/lib/dpkg/lock 2>/dev/null || true
rm -f /var/lib/dpkg/lock-frontend 2>/dev/null || true
rm -f /var/cache/apt/archives/lock 2>/dev/null || true
ok "Lock-Dateien entfernt"

log "Schritt 3: Repariere dpkg..."
dpkg --configure -a 2>&1 || log "dpkg configure hatte Fehler (normal wenn nix zu tun)"
ok "dpkg repariert"

log "Schritt 4: Lösche deaktivierte Pakete..."
apt-get -yf install --fix-broken 2>&1 || log "fix-broken hatte Fehler"
ok "Deaktivierte Pakete behoben"

log "Schritt 5: Prüfe System..."
apt-get check 2>&1 || log "apt-get check hatte Warnungen"
ok "System geprüft"

log "Schritt 6: Aktualisiere Paketlisten..."
apt update -y 2>&1 | grep -v "^W:" || log "apt update hatte Warnungen"
ok "Paketlisten aktualisiert"

echo ""
echo "🎉 dpkg Reparatur abgeschlossen!"
echo ""
echo "Sie können jetzt die Installation starten:"
echo "  sudo bash install_scandy.sh"
echo ""

