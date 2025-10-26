#!/usr/bin/env bash
set -euo pipefail

# Scandy venv Reparatur-Script
# Behebt das Problem mit Symlink-venvs

echo "🔧 Scandy venv Reparatur - Starte Reparatur..."

# Prüfe Root-Rechte
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    echo "❌ Bitte als root ausführen (sudo ./fix_scandy_venv.sh)"
    exit 1
fi

echo ""
echo "📋 Das aktuelle venv wird überprüft..."
echo ""

# Prüfe ob venv existiert
if [ -d "/opt/scandy/venv" ]; then
    echo "✓ venv-Verzeichnis gefunden in /opt/scandy"
    
    # Prüfe auf Symlinks
    PYTHON_PATH=$(readlink -f /opt/scandy/venv/bin/python3 2>/dev/null || echo "")
    if [[ "$PYTHON_PATH" == *"/home"* ]]; then
        echo "⚠️  Problem gefunden: venv enthält Symlinks auf Home-Verzeichnis"
        echo "   Python-Pfad: $PYTHON_PATH"
        echo ""
        
        echo "🗑️  Lösche altes venv..."
        rm -rf /opt/scandy/venv
        echo "✓ Altes venv gelöscht"
    else
        echo "✓ venv scheint korrekt zu sein (keine Home-Symlinks)"
        echo "   Python-Pfad: $PYTHON_PATH"
        
        # Frage ob trotzdem neu erstellt werden soll
        read -p "Trotzdem neu erstellen? (j/N): " REINSTALL
        if [[ "$REINSTALL" != "j" ]]; then
            echo "❌ Abgebrochen"
            exit 0
        fi
        
        echo "🗑️  Lösche altes venv..."
        rm -rf /opt/scandy/venv
        echo "✓ Altes venv gelöscht"
    fi
else
    echo "⚠️  Kein venv gefunden in /opt/scandy"
    echo "   Das ist ungewöhnlich."
    echo ""
fi

# Stoppe Scandy-Service
echo ""
echo "🛑 Stoppe Scandy-Service..."
if systemctl is-active --quiet scandy 2>/dev/null; then
    systemctl stop scandy
    echo "✓ Service gestoppt"
else
    echo "⚠️  Service läuft bereits nicht"
fi

# Erstelle neues venv
echo ""
echo "🐍 Erstelle neues venv in /opt/scandy..."
cd /opt/scandy

# Erstelle venv
python3 -m venv venv
echo "✓ venv erstellt"

# Aktiviere venv
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrade pip..."
pip install --upgrade pip >/dev/null 2>&1
echo "✓ pip aktualisiert"

# Installiere Requirements
if [ -f "requirements.txt" ]; then
    echo "📦 Installiere Requirements..."
    pip install -r requirements.txt >/dev/null 2>&1
    echo "✓ Requirements installiert"
else
    echo "⚠️  requirements.txt nicht gefunden"
    exit 1
fi

# Setze Berechtigungen
echo ""
echo "🔐 Setze Berechtigungen..."
chown -R root:root /opt/scandy/venv 2>/dev/null || true
echo "✓ Berechtigungen gesetzt"

# Zeige venv-Status
echo ""
echo "📊 Neues venv-Status:"
PYTHON_PATH=$(readlink -f /opt/scandy/venv/bin/python3 2>/dev/null || echo "")
echo "   Python-Pfad: $PYTHON_PATH"

GUNICORN_PATH=$(which gunicorn 2>/dev/null || echo "nicht gefunden")
echo "   Gunicorn-Pfad: $GUNICORN_PATH"

# Starte Scandy-Service
echo ""
echo "▶️  Starte Scandy-Service..."
if systemctl start scandy; then
    echo "✓ Service gestartet"
    
    # Warte kurz
    sleep 3
    
    # Prüfe Status
    if systemctl is-active --quiet scandy; then
        echo "✓ Service läuft erfolgreich"
    else
        echo "⚠️  Service läuft nicht - prüfe Logs:"
        echo "   journalctl -u scandy -n 20"
    fi
else
    echo "❌ Service konnte nicht gestartet werden"
    echo "   Prüfe Logs: journalctl -u scandy -n 20"
    exit 1
fi

# Zeige finale Infos
echo ""
echo "✅ Reparatur abgeschlossen!"
echo ""
echo "📊 Service-Status:"
systemctl status scandy --no-pager | head -15
echo ""
echo "🌐 Web-App: http://$(hostname -I | awk '{print $1}'):$(grep WEB_PORT /opt/scandy/.env 2>/dev/null | cut -d'=' -f2 || echo '80')"
echo "📝 Logs: journalctl -u scandy -f"

