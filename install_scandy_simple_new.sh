#!/usr/bin/env bash
set -euo pipefail

# Scandy Simple Installer - Komplett neu und einfach
# Funktioniert immer - auch bei Problemen

echo "🚀 Scandy Simple Installer - Starte Installation..."

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

# Session-Wartungsfunktion
fix_sessions() {
    log "Behebe Session-Probleme..."
    if [ -d "/opt/scandy/app/flask_session" ]; then
        # Prüfe auf gemischte Berechtigungen und korrigiere sie
        log "Prüfe auf gemischte Session-Berechtigungen..."
        MIXED_PERMS=$(find /opt/scandy/app/flask_session/ -type f -not -user root -o -not -group root -o -not -perm 644 2>/dev/null | wc -l)
        if [ "$MIXED_PERMS" -gt 0 ]; then
            log "Gefunden: $MIXED_PERMS Dateien mit gemischten Berechtigungen - korrigiere..."
        fi
        
        # Lösche nur sehr alte Session-Dateien (älter als 7 Tage)
        log "Lösche alte Session-Dateien (älter als 7 Tage)..."
        find /opt/scandy/app/flask_session/ -type f -name "*.session" -mtime +7 -delete 2>/dev/null || true
        
        # Setze korrekte Berechtigungen für alle bestehenden Session-Dateien
        log "Setze Session-Datei-Berechtigungen..."
        find /opt/scandy/app/flask_session/ -type f -exec chown root:root {} \; 2>/dev/null || true
        find /opt/scandy/app/flask_session/ -type f -exec chmod 644 {} \; 2>/dev/null || true
        
        # Setze korrekte Berechtigungen für Session-Verzeichnis
        log "Setze Session-Verzeichnis-Berechtigungen..."
        chown -R root:root /opt/scandy/app/flask_session/
        chmod 755 /opt/scandy/app/flask_session/
        
        # Erstelle .gitkeep um das Verzeichnis zu erhalten
        touch /opt/scandy/app/flask_session/.gitkeep
        chown root:root /opt/scandy/app/flask_session/.gitkeep
        chmod 644 /opt/scandy/app/flask_session/.gitkeep
        
        success "Session-Probleme behoben"
    else
        # Erstelle Session-Verzeichnis falls es nicht existiert
        log "Erstelle Session-Verzeichnis..."
        mkdir -p /opt/scandy/app/flask_session
        chown -R root:root /opt/scandy/app/flask_session/
        chmod 755 /opt/scandy/app/flask_session/
        touch /opt/scandy/app/flask_session/.gitkeep
        chown root:root /opt/scandy/app/flask_session/.gitkeep
        chmod 644 /opt/scandy/app/flask_session/.gitkeep
        success "Session-Verzeichnis erstellt"
    fi
}

# Verbesserte Session-Berechtigungsfunktion
fix_session_permissions() {
    log "Korrigiere Session-Berechtigungen..."
    
    # Erstelle Session-Verzeichnis falls es nicht existiert
    mkdir -p /opt/scandy/app/flask_session
    
    # Setze korrekte Besitzer und Gruppe
    chown -R root:root /opt/scandy/app/flask_session/
    
    # Setze Verzeichnisberechtigungen
    chmod 755 /opt/scandy/app/flask_session/
    
    # Setze Dateiberechtigungen für bestehende Dateien
    if [ "$(ls -A /opt/scandy/app/flask_session/ 2>/dev/null)" ]; then
        find /opt/scandy/app/flask_session/ -type f -exec chmod 644 {} \; 2>/dev/null || true
    fi
    
    # Erstelle .gitkeep mit korrekten Berechtigungen
    touch /opt/scandy/app/flask_session/.gitkeep
    chown root:root /opt/scandy/app/flask_session/.gitkeep
    chmod 644 /opt/scandy/app/flask_session/.gitkeep
    
    # Setze umask für neue Dateien
    umask 022
    
    success "Session-Berechtigungen korrigiert"
}

# Port-Freimachungsfunktion
free_port_80() {
    log "Mache Port 80 frei..."
    
    # Scandy-Service stoppen (falls läuft)
    if systemctl is-active --quiet scandy 2>/dev/null; then
        log "Stoppe laufenden Scandy-Service..."
        systemctl stop scandy 2>/dev/null || true
        systemctl disable scandy 2>/dev/null || true
    fi
    
    # Alle bekannten Webserver stoppen
    local webservers=("apache2" "nginx" "lighttpd" "httpd" "caddy" "traefik")
    
    for server in "${webservers[@]}"; do
        if systemctl is-active --quiet "$server" 2>/dev/null; then
            log "Stoppe $server..."
            systemctl stop "$server" 2>/dev/null || true
            systemctl disable "$server" 2>/dev/null || true
        fi
    done
    
    # Alle Webserver- und Scandy-Prozesse beenden
    pkill -f "apache2\|nginx\|lighttpd\|httpd\|caddy\|traefik\|python.*:80\|gunicorn.*:80\|scandy" 2>/dev/null || true
    
    # Warte bis alle Prozesse gestoppt sind
    sleep 3
    
    # Prüfe ob Port 80 jetzt frei ist
    if ! ss -H -ltn 2>/dev/null | grep -q ":80 "; then
        success "Port 80 erfolgreich freigemacht!"
        return 0
    else
        # Versuche hartnäckige Prozesse zu beenden
        log "Port 80 ist immer noch belegt - versuche hartnäckige Prozesse zu beenden..."
        
        # Finde alle Prozesse auf Port 80
        local port80_pids=$(ss -H -ltnp 2>/dev/null | grep ":80 " | awk '{print $7}' | cut -d',' -f1 | cut -d'=' -f2 | sort -u)
        
        for pid in $port80_pids; do
            if [ -n "$pid" ] && [ "$pid" != "-" ]; then
                log "Beende Prozess $pid auf Port 80..."
                kill -9 "$pid" 2>/dev/null || true
            fi
        done
        
        sleep 2
        
        # Finale Prüfung
        if ! ss -H -ltn 2>/dev/null | grep -q ":80 "; then
            success "Port 80 nach hartnäckiger Bereinigung freigemacht!"
            return 0
        else
            error "Port 80 konnte nicht freigemacht werden"
            return 1
        fi
    fi
}

# Webserver-Dienste dauerhaft deaktivieren
disable_webserver_services() {
    log "Deaktiviere Webserver-Dienste dauerhaft..."
    
    local webservers=("apache2" "nginx" "lighttpd" "httpd" "caddy" "traefik")
    
    for server in "${webservers[@]}"; do
        if systemctl is-enabled --quiet "$server" 2>/dev/null; then
            log "Deaktiviere $server dauerhaft..."
            systemctl disable "$server" 2>/dev/null || true
            systemctl mask "$server" 2>/dev/null || true
        fi
    done
    
    success "Webserver-Dienste dauerhaft deaktiviert"
}

# Alte Scandy-Prozesse bereinigen (für Neuinstallationen)
cleanup_old_scandy() {
    log "Bereinige alte Scandy-Prozesse für Neuinstallation..."
    
    # Scandy-Service stoppen und deaktivieren
    if systemctl is-active --quiet scandy 2>/dev/null; then
        log "Stoppe laufenden Scandy-Service..."
        systemctl stop scandy 2>/dev/null || true
        systemctl disable scandy 2>/dev/null || true
    fi
    
    # Alle Gunicorn-Prozesse beenden (sanft)
    log "Beende alle Gunicorn-Prozesse..."
    pkill -f "gunicorn" 2>/dev/null || true
    
    # Alle Scandy-bezogenen Prozesse beenden (sanft)
    log "Beende alle Scandy-bezogenen Prozesse..."
    pkill -f "scandy\|python.*scandy" 2>/dev/null || true
    
    # Warte bis alle Prozesse gestoppt sind
    sleep 3
    
    # Verwende einen einfacheren Ansatz: Beende alle Prozesse auf Port 80 direkt
    if ss -H -ltn 2>/dev/null | grep -q ":80 "; then
        log "Port 80 ist belegt - beende alle Prozesse direkt..."
        local port80_pids=$(ss -H -ltnp 2>/dev/null | grep ":80 " | awk '{print $7}' | cut -d',' -f1 | cut -d'=' -f2 | sort -u)
        for pid in $port80_pids; do
            if [ -n "$pid" ] && [ "$pid" != "-" ]; then
                log "Beende Prozess $pid auf Port 80..."
                # Verwende kill -9 direkt mit Timeout
                timeout 3s bash -c "kill -9 $pid" 2>/dev/null || true
            fi
        done
        sleep 2
    fi
    
    # Prüfe ob noch Prozesse laufen (nur für Logging)
    if pgrep -f "gunicorn\|scandy" >/dev/null 2>&1; then
        log "Warnung: Einige Prozesse laufen noch, aber Installation wird fortgesetzt..."
    fi
    
    success "Alte Scandy-Prozesse bereinigt"
}

# Port-Status anzeigen
show_port_status() {
    log "Aktueller Port-Status:"
    echo "Port 80: $(ss -H -ltn 2>/dev/null | grep -q ':80 ' && echo '🔴 Belegt' || echo '🟢 Frei')"
    echo "Port 443: $(ss -H -ltn 2>/dev/null | grep -q ':443 ' && echo '🔴 Belegt' || echo '🟢 Frei')"
    echo "Port 5001: $(ss -H -ltn 2>/dev/null | grep -q ':5001 ' && echo '🔴 Belegt' || echo '🟢 Frei')"
    
    # Zeige welche Prozesse auf den Ports laufen
    echo ""
    log "Prozesse auf den Ports:"
    # Verwende eine einfachere Methode ohne while-Schleife
    local port_processes=$(ss -H -ltnp 2>/dev/null | grep -E ':(80|443|5001) ' || true)
    if [ -n "$port_processes" ]; then
        echo "$port_processes" | sed 's/^/  /'
    else
        echo "  Keine Prozesse auf den Ports gefunden"
    fi
}

# Alte Scandy-Prozesse VOR der Port-Prüfung bereinigen
log "Bereinige alte Scandy-Prozesse vor der Port-Prüfung..."
cleanup_old_scandy

# Port-Status anzeigen (nach der Bereinigung)
show_port_status

# Port-Auswahl
echo ""
# Non‑interactive/ENV‑Override
if [ -n "${SCANDY_WEB_PORT:-}" ]; then
    WEB_PORT="$SCANDY_WEB_PORT"
    PORT_NAME="ENV"
elif [ -n "${WEB_PORT:-}" ]; then
    PORT_NAME="ENV"
elif [ "${SCANDY_NONINTERACTIVE:-0}" = "1" ] || [ ! -t 0 ]; then
    WEB_PORT=5001
    PORT_NAME="Noninteractive"
fi

if [ -z "${WEB_PORT:-}" ]; then
    echo "🌐 Port-Auswahl für Scandy:"
    echo "1) Port 80 (Standard-HTTP, keine Port-Angabe in URL nötig)"
    echo "2) Port 443 (Standard-HTTPS, keine Port-Angabe in URL nötig)"
    echo "3) Port 5001 (Standard-Scandy-Port)"
    echo "4) Benutzerdefinierter Port"
    echo "5) Port 80 erzwingen (stoppt andere Webserver)"
    echo ""
    read -p "Wähle Port (1-5): " PORT_CHOICE

    case $PORT_CHOICE in
        1)
            WEB_PORT=80
            PORT_NAME="Standard-HTTP"
            ;;
        2)
            WEB_PORT=443
            PORT_NAME="Standard-HTTPS"
            ;;
        3)
            WEB_PORT=5001
            PORT_NAME="Standard-Scandy"
            ;;
        4)
            read -p "Gib benutzerdefinierten Port ein (z.B. 8080): " WEB_PORT
            PORT_NAME="Benutzerdefiniert"
            ;;
        5)
            WEB_PORT=80
            PORT_NAME="Port 80 erzwingen"
            # Sofort Port 80 freimachen
            log "Erzwinge Port 80 - stoppe alle Webserver..."
            if free_port_80; then
                success "Port 80 erfolgreich freigemacht!"
                # Deaktiviere Webserver-Dienste dauerhaft
                disable_webserver_services
            else
                error "Port 80 konnte nicht freigemacht werden - verwende Port 5001"
                WEB_PORT=5001
                PORT_NAME="Standard-Scandy (Port 80 nicht freizubekommen)"
            fi
            ;;
        *)
            WEB_PORT=80
            PORT_NAME="Standard-HTTP (Standardauswahl)"
            ;;
    esac
fi

# Prüfe ob Port verfügbar ist und mache ihn ggf. frei
if [ "$WEB_PORT" = "80" ] || [ "$WEB_PORT" = "443" ]; then
    if ss -H -ltn 2>/dev/null | grep -q ":$WEB_PORT "; then
        log "Port $WEB_PORT ist belegt - versuche ihn freizumachen..."
        
        if [ "$WEB_PORT" = "80" ]; then
            # Versuche Port 80 freizumachen
            if free_port_80; then
                success "Port 80 erfolgreich freigemacht!"
                PORT_NAME="Standard-HTTP (Port freigemacht)"
            else
                log "Port 80 konnte nicht freigemacht werden - verwende Port 5001"
                WEB_PORT=5001
                PORT_NAME="Standard-Scandy (Port 80 nicht freizubekommen)"
            fi
        else
            # Für Port 443: Verwende Port 5001
            log "Port 443 konnte nicht freigemacht werden - verwende Port 5001"
            WEB_PORT=5001
            PORT_NAME="Standard-Scandy (Port 443 nicht freizubekommen)"
        fi
    fi
fi

success "Verwende Port: $WEB_PORT ($PORT_NAME)"

# 1. System-Pakete installieren
log "Installiere System-Pakete..."
apt update -y >/dev/null 2>&1
apt install -y python3 python3-pip python3-venv git curl gnupg lsb-release bc >/dev/null 2>&1
success "System-Pakete installiert"

# 2. MongoDB installieren (einfach)
log "Installiere MongoDB..."
if ! command -v mongod >/dev/null 2>&1; then
    # MongoDB-Repository hinzufügen
    curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-7.0.list
    apt update -y >/dev/null 2>&1
    apt install -y mongodb-org >/dev/null 2>&1
    success "MongoDB installiert"
else
    info "MongoDB bereits installiert"
fi

# 3. MongoDB starten (ohne Auth - einfach)
log "Starte MongoDB..."

# MongoDB komplett stoppen und aufräumen
log "Stoppe alle MongoDB-Prozesse..."
systemctl stop mongod 2>/dev/null || true
systemctl disable mongod 2>/dev/null || true
pkill -f mongod 2>/dev/null || true
pkill -f mongo 2>/dev/null || true

# Warte bis alle Prozesse gestoppt sind
for i in {1..10}; do
    if ! pgrep -f mongod >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Prüfe ob Port 27017 frei ist
if ss -H -ltn 2>/dev/null | grep -q ':27017 '; then
    log "Port 27017 ist noch belegt - warte..."
    sleep 5
fi

sleep 3

# Verzeichnisse erstellen
mkdir -p /var/lib/mongodb /var/log/mongodb
chown mongodb:mongodb /var/lib/mongodb /var/log/mongodb 2>/dev/null || true

# MongoDB-Version erkennen und passende Konfiguration erstellen
log "Erstelle MongoDB-Konfiguration..."
if command -v mongod >/dev/null 2>&1; then
    MONGO_VERSION=$(mongod --version | head -1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
    log "MongoDB Version: $MONGO_VERSION"
    
    if [ -n "$MONGO_VERSION" ] && [ "$(echo "$MONGO_VERSION >= 4.0" | bc -l 2>/dev/null || echo "0")" = "1" ]; then
        # Moderne MongoDB (4.0+)
        cat > /etc/mongod.conf << 'EOF'
# MongoDB 4.0+ Konfiguration
storage:
  dbPath: /var/lib/mongodb

systemLog:
  destination: file
  logAppend: true
  path: /var/log/mongodb/mongod.log

net:
  port: 27017
  bindIp: 0.0.0.0
EOF
        log "Moderne MongoDB-Konfiguration erstellt"
    else
        # Ältere MongoDB oder unbekannte Version
        cat > /etc/mongod.conf << 'EOF'
# Einfache MongoDB-Konfiguration (kompatibel)
dbpath=/var/lib/mongodb
logpath=/var/log/mongodb/mongod.log
logappend=true
port=27017
bind_ip=0.0.0.0
EOF
        log "Kompatible MongoDB-Konfiguration erstellt"
    fi
else
    # Fallback-Konfiguration
    cat > /etc/mongod.conf << 'EOF'
# Fallback MongoDB-Konfiguration
dbpath=/var/lib/mongodb
logpath=/var/log/mongodb/mongod.log
logappend=true
port=27017
bind_ip=0.0.0.0
EOF
    log "Fallback MongoDB-Konfiguration erstellt"
fi

# MongoDB starten
log "Starte MongoDB-Service..."
if systemctl start mongod; then
    success "MongoDB-Service gestartet"
else
    error "MongoDB-Service startet nicht - versuche manuellen Start"
    
    # Manueller Start als Fallback
    log "Starte MongoDB manuell..."
    nohup mongod --config /etc/mongod.conf > /var/log/mongodb/mongod.log 2>&1 &
    MONGODB_PID=$!
    echo $MONGODB_PID > /var/run/mongod.pid
    sleep 3
    
    if kill -0 $MONGODB_PID 2>/dev/null; then
        success "MongoDB läuft manuell (PID: $MONGODB_PID)"
    else
        error "Auch manueller Start fehlgeschlagen"
        exit 1
    fi
fi

# Prüfen ob MongoDB läuft
log "Prüfe MongoDB-Verbindung..."
for i in {1..30}; do
    if mongosh --quiet --eval "db.runCommand('ping')" >/dev/null 2>&1; then
        success "MongoDB läuft auf Port 27017"
        break
    fi
    if [ $i -eq 30 ]; then
        error "MongoDB-Verbindung nach 30 Versuchen fehlgeschlagen"
        
        # Zeige MongoDB-Status und Logs
        log "MongoDB-Status:"
        systemctl status mongod --no-pager 2>/dev/null || echo "Service-Status nicht verfügbar"
        
        log "MongoDB-Logs:"
        tail -20 /var/log/mongodb/mongod.log 2>/dev/null || echo "Keine Logs verfügbar"
        
        exit 1
    fi
    sleep 1
done

# 4. Scandy-Verzeichnis einrichten
log "Richte Scandy ein..."
mkdir -p /opt/scandy

# Code kopieren (robust)
log "Kopiere Scandy-Code..."
CURRENT_DIR=$(pwd)
log "Aktuelles Verzeichnis: $CURRENT_DIR"

if [ -d "/home/$(logname)/Scandy2" ]; then
    cp -r /home/$(logname)/Scandy2/* /opt/scandy/ 2>/dev/null || true
    success "Code von /home/$(logname)/Scandy2 kopiert"
elif [ -d "/home/woschj/Scandy2" ]; then
    cp -r /home/woschj/Scandy2/* /opt/scandy/ 2>/dev/null || true
    success "Code von /home/woschj/Scandy2 kopiert"
elif [ -d "$CURRENT_DIR/app" ] || [ -f "$CURRENT_DIR/app.py" ] || [ -f "$CURRENT_DIR/requirements.txt" ]; then
    # Aktuelles Verzeichnis enthält Scandy-Code
    log "Scandy-Code im aktuellen Verzeichnis gefunden - kopiere nach /opt/scandy"
    cp -r "$CURRENT_DIR"/* /opt/scandy/ 2>/dev/null || true
    success "Code vom aktuellen Verzeichnis ($CURRENT_DIR) kopiert"
else
    error "Kein Scandy-Code gefunden!"
    log "Verfügbare Verzeichnisse:"
    ls -la /home/ 2>/dev/null || echo "Keine /home Verzeichnisse"
    log "Aktuelles Verzeichnis Inhalt:"
    ls -la "$CURRENT_DIR" | head -10
    exit 1
fi

# Wechsle zu /opt/scandy für den Rest des Scripts
cd /opt/scandy

# Prüfe welche App-Dateien existieren
log "Prüfe verfügbare App-Dateien..."
log "Verzeichnis /opt/scandy nach dem Kopieren:"
ls -la /opt/scandy/ | head -10

if [ -d "/opt/scandy/app" ]; then
    log "App-Verzeichnis in /opt/scandy:"
    ls -la /opt/scandy/app/ | head -10
    log "Python-Dateien im app/ Verzeichnis:"
    find /opt/scandy/app/ -name "*.py" -maxdepth 1 2>/dev/null || echo "Keine Python-Dateien im app/ Verzeichnis"
fi

# Berechtigungen setzen
chown -R root:root /opt/scandy 2>/dev/null || true
chmod -R 755 /opt/scandy

# 5. Python-Umgebung einrichten
log "Erstelle Python-Umgebung..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1

# Requirements installieren
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt >/dev/null 2>&1
    success "Python-Abhängigkeiten installiert"
else
    info "requirements.txt nicht gefunden"
fi

# 6. Einfache .env-Datei erstellen
log "Erstelle .env-Datei..."
cat > .env << EOF
# Scandy - Einfache Konfiguration
WEB_PORT=$WEB_PORT
MONGODB_URI=mongodb://localhost:27017/scandy
MONGODB_DB=scandy
SECRET_KEY=scandy_secret_key_123
FLASK_ENV=production
SESSION_COOKIE_SECURE=false
REMEMBER_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SAMESITE=Lax
SESSION_COOKIE_HTTPONLY=true
REMEMBER_COOKIE_HTTPONLY=true
SESSION_TYPE=filesystem
PERMANENT_SESSION_LIFETIME=604800
EOF
success ".env-Datei erstellt"

# 6.1 Wrapper-Skripte für robusten Start erstellen
log "Erzeuge Wrapper-Skripte..."
install -d -m 755 /opt/scandy/bin

# Platzhalter – wird nach Bestimmung von APP_FILE/MODULE_NAME unten überschrieben
cat > /opt/scandy/bin/prestart.sh << 'EOF'
#!/usr/bin/env bash
set -e
DIR=/opt/scandy/app/flask_session
mkdir -p "$DIR"
chown -R root:root "$DIR" || true
chmod 755 "$DIR" || true
find "$DIR" -type f -exec chmod 644 {} + 2>/dev/null || true
exit 0
EOF
chmod +x /opt/scandy/bin/prestart.sh

# 7. Systemd-Service erstellen
log "Erstelle Systemd-Service..."

# Finde die richtige App-Datei
log "Finde App-Datei..."
APP_FILE=""

# Prüfe zuerst das app/ Verzeichnis (Hauptanwendung)
if [ -d "/opt/scandy/app" ]; then
    log "App-Verzeichnis gefunden - suche nach Hauptanwendung..."
    
    # Suche nach wsgi.py (Standard für Produktion)
    if [ -f "/opt/scandy/app/wsgi.py" ]; then
        APP_FILE="app/wsgi.py"
        log "WSGI-Entrypoint gefunden: app/wsgi.py (Produktionsstandard)"
    elif [ -f "/opt/scandy/app/wsgi_https.py" ]; then
        APP_FILE="app/wsgi_https.py"
        log "HTTPS-WSGI-Entrypoint gefunden: app/wsgi_https.py"
    elif [ -f "/opt/scandy/app/app.py" ]; then
        APP_FILE="app/app.py"
        log "App-Datei gefunden: app/app.py"
    elif [ -f "/opt/scandy/app/run.py" ]; then
        APP_FILE="app/run.py"
        log "App-Datei gefunden: app/run.py"
    elif [ -f "/opt/scandy/app/__init__.py" ]; then
        # Flask-App mit __init__.py (nur als Fallback)
        APP_FILE="app"
        log "Flask-App mit __init__.py gefunden: app (Fallback)"
    fi
fi

# Fallback: Prüfe Root-Verzeichnis
if [ -z "$APP_FILE" ]; then
    if [ -f "/opt/scandy/app.py" ]; then
        APP_FILE="app.py"
        log "App-Datei im Root gefunden: app.py"
    elif [ -f "/opt/scandy/run.py" ]; then
        APP_FILE="run.py"
        log "App-Datei im Root gefunden: run.py"
    elif [ -f "/opt/scandy/wsgi.py" ]; then
        APP_FILE="wsgi.py"
        log "App-Datei im Root gefunden: wsgi.py"
    fi
fi

# Letzter Fallback: Suche nach Python-Dateien (aber ignoriere Wartungsscripts)
if [ -z "$APP_FILE" ]; then
    log "Suche nach Python-App-Dateien..."
    PY_FILES=$(find /opt/scandy -maxdepth 1 -name "*.py" | grep -v "fix_" | grep -v "cleanup_" | grep -v "create_" | grep -v "migrate_" | head -5)
    if [ -n "$PY_FILES" ]; then
        APP_FILE=$(basename "$(echo "$PY_FILES" | head -1)")
        log "Verwende gefundene App-Datei: $APP_FILE"
    else
        error "Keine Python-App-Datei gefunden!"
        exit 1
    fi
fi

if [ -z "$APP_FILE" ]; then
    error "Keine App-Datei gefunden!"
    exit 1
fi

log "Verwende App-Datei: $APP_FILE"

# Entscheide ob Gunicorn oder Python direkt verwenden
if [[ "$APP_FILE" == *"wsgi.py" ]]; then
    # WSGI-Datei gefunden - verwende Gunicorn
    # Extrahiere den Modulnamen ohne .py
    MODULE_NAME=$(echo "$APP_FILE" | sed 's/\.py$//' | sed 's/\//\./g')
    # Scandy verwendet 'app' als Variable, nicht 'application'
    EXEC_START="/opt/scandy/venv/bin/gunicorn --bind 0.0.0.0:\${WEB_PORT} --workers 2 --timeout 120 --chdir /opt/scandy $MODULE_NAME:app"
    log "Verwende Gunicorn für WSGI-App: $MODULE_NAME:app"
else
    # Normale Python-Datei - verwende Python direkt
    EXEC_START="/opt/scandy/venv/bin/python3 $APP_FILE"
    log "Verwende Python direkt für App"
fi

# Wrapper-Startkommando (Shell löst WEB_PORT zur Laufzeit auf)
if [[ "$APP_FILE" == *"wsgi.py" ]]; then
    WRAP_CMD="/opt/scandy/venv/bin/gunicorn --bind \"0.0.0.0:\${WEB_PORT:-$WEB_PORT}\" --workers 2 --timeout 120 --chdir /opt/scandy $MODULE_NAME:app"
else
    WRAP_CMD="/opt/scandy/venv/bin/python3 $APP_FILE"
fi

# Start-Wrapper erzeugen
cat > /opt/scandy/bin/start_scandy.sh << EOF
#!/usr/bin/env bash
set -e
cd /opt/scandy
set -a
[ -f /opt/scandy/.env ] && . /opt/scandy/.env
set +a
exec $WRAP_CMD
EOF
chmod +x /opt/scandy/bin/start_scandy.sh

cat > /etc/systemd/system/scandy.service << EOF
[Unit]
Description=Scandy Application
After=network.target mongod.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/scandy
Environment=PATH=/opt/scandy/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/scandy
EnvironmentFile=/opt/scandy/.env
ExecStart=/opt/scandy/bin/start_scandy.sh
ExecStartPre=/opt/scandy/bin/prestart.sh
ExecStartPost=/opt/scandy/bin/prestart.sh
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable scandy >/dev/null 2>&1
success "Systemd-Service erstellt"

# 8. Firewall öffnen
log "Öffne Firewall..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow $WEB_PORT/tcp >/dev/null 2>&1 || true
    info "Port $WEB_PORT freigegeben"
fi

# 8.1. Cron-Job für Session-Wartung einrichten
log "Richte Cron-Job für Session-Wartung ein..."
cat > /etc/cron.d/scandy-session-cleanup << EOF
# Scandy Session-Wartung - läuft alle 5 Minuten
*/5 * * * * root /bin/bash -c 'if [ -d "/opt/scandy/app/flask_session" ]; then find /opt/scandy/app/flask_session -type f -mtime +7 -delete 2>/dev/null || true; find /opt/scandy/app/flask_session -type f -exec chown root:root {} \; -exec chmod 644 {} \; 2>/dev/null || true; chmod 755 /opt/scandy/app/flask_session 2>/dev/null || true; chown root:root /opt/scandy/app/flask_session/ 2>/dev/null || true; fi'
EOF

# Setze Berechtigungen für Cron-Job
chmod 644 /etc/cron.d/scandy-session-cleanup
success "Cron-Job für Session-Wartung eingerichtet"

# 8.1.1. Systemstart-Script für Session-Berechtigungen
log "Richte Systemstart-Script für Session-Berechtigungen ein..."
cat > /etc/systemd/system/scandy-session-fix.service << EOF
[Unit]
Description=Fix Scandy Session Permissions on Boot
After=network.target
Before=scandy.service

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'if [ -d "/opt/scandy/app/flask_session" ]; then find /opt/scandy/app/flask_session -type f -exec chown root:root {} \; -exec chmod 644 {} \; 2>/dev/null || true; chmod 755 /opt/scandy/app/flask_session 2>/dev/null || true; chown root:root /opt/scandy/app/flask_session/ 2>/dev/null || true; fi'
RemainAfterExit=yes
User=root

[Install]
WantedBy=multi-user.target
EOF

# Aktiviere den Service
systemctl daemon-reload
systemctl enable scandy-session-fix.service >/dev/null 2>&1
success "Systemstart-Script für Session-Berechtigungen eingerichtet"

# 8.2. Webserver-Dienste dauerhaft deaktivieren wenn Port 80 verwendet wird
if [ "$WEB_PORT" = "80" ]; then
    log "Port 80 wird verwendet - deaktiviere Webserver-Dienste dauerhaft..."
    disable_webserver_services
    
    # Erstelle auch einen Cron-Job der alle 10 Minuten prüft ob Port 80 frei ist
    log "Richte Cron-Job für Port 80-Überwachung ein..."
    cat > /etc/cron.d/scandy-port80-monitor << EOF
# Scandy Port 80 Überwachung - läuft alle 10 Minuten
*/10 * * * * root /bin/bash -c 'if ss -H -ltn 2>/dev/null | grep -q ":80 " && ! ss -H -ltn 2>/dev/null | grep -q ":80 .*scandy"; then /opt/scandy/venv/bin/python3 -c "import subprocess; subprocess.run([\"pkill\", \"-f\", \"apache2|nginx|lighttpd|httpd|caddy|traefik\"], capture_output=True)" 2>/dev/null || true; fi'
EOF
    
    chmod 644 /etc/cron.d/scandy-port80-monitor
    success "Cron-Job für Port 80-Überwachung eingerichtet"
fi

# 9. Session-System prophylaktisch einrichten
log "Richte Session-System prophylaktisch ein..."
fix_sessions
fix_session_permissions

success "Session-System prophylaktisch eingerichtet"

# 10. Services starten
log "Starte Services..."
systemctl restart mongod

# Starte Scandy mit besserer Fehlerbehandlung
log "Starte Scandy-Service..."

# Finale Session-Berechtigungsprüfung vor dem Start
log "Führe finale Session-Berechtigungsprüfung durch..."
fix_session_permissions

if systemctl restart scandy; then
    success "Scandy-Service gestartet"
    
    # Warte kurz und prüfe dann Session-Status
    sleep 3
    if [ -d "/opt/scandy/app/flask_session" ]; then
        log "Prüfe Session-Verzeichnis nach Service-Start..."
        ls -la /opt/scandy/app/flask_session/ | head -5
        
        # Stelle sicher, dass neue Session-Dateien die richtigen Berechtigungen haben
        log "Korrigiere Berechtigungen für neue Session-Dateien..."
        fix_session_permissions
    fi
else
    error "Fehler beim Starten des Scandy-Services"
    log "Service-Status:"
    systemctl status scandy --no-pager 2>/dev/null || echo "Service-Status nicht verfügbar"
    
    # Versuche manuellen Start
    log "Versuche manuellen Start..."
    cd /opt/scandy
    source venv/bin/activate
    if [ -f "app/wsgi.py" ]; then
        log "Starte manuell mit Gunicorn..."
        nohup venv/bin/gunicorn --bind 0.0.0.0:$WEB_PORT --workers 2 --timeout 120 app.wsgi:app > /var/log/scandy.log 2>&1 &
        SCANDY_PID=$!
        echo $SCANDY_PID > /var/run/scandy.pid
        sleep 3
        
        if kill -0 $SCANDY_PID 2>/dev/null; then
            success "Scandy läuft manuell (PID: $SCANDY_PID)"
        else
            error "Auch manueller Start fehlgeschlagen"
            log "Logs:"
            tail -20 /var/log/scandy.log 2>/dev/null || echo "Keine Logs verfügbar"
        fi
    fi
fi

# 12. Warten auf App-Start
log "Warte auf App-Start..."
for i in {1..60}; do
    # Prüfe sowohl Systemd-Service als auch manuellen Prozess
    if ss -H -ltn 2>/dev/null | grep -q ":$WEB_PORT " || [ -f "/var/run/scandy.pid" ]; then
        success "Scandy läuft auf Port $WEB_PORT"
        break
    fi
    
    # Zeige Fortschritt alle 10 Sekunden
    if [ $((i % 5)) -eq 0 ]; then
        log "Warte auf App-Start... ($i/60)"
        
        # Zeige Service-Status alle 10 Sekunden
        log "Service-Status:"
        systemctl status scandy --no-pager 2>/dev/null | head -10 || echo "Service-Status nicht verfügbar"
        
        # Prüfe manuellen Prozess
        if [ -f "/var/run/scandy.pid" ]; then
            MANUAL_PID=$(cat /var/run/scandy.pid)
            if kill -0 $MANUAL_PID 2>/dev/null; then
                log "Manueller Prozess läuft (PID: $MANUAL_PID)"
            fi
        fi
        
        # Prüfe Port
        log "Port-Status:"
        ss -H -ltn 2>/dev/null | grep ":$WEB_PORT " || echo "Port $WEB_PORT nicht aktiv"
    fi
    
    if [ $i -eq 60 ]; then
        error "App startet nicht nach 2 Minuten"
        
        # Detaillierte Fehlerdiagnose
        log "Fehlerdiagnose:"
        log "Systemd-Status:"
        systemctl status scandy --no-pager 2>/dev/null || echo "Service-Status nicht verfügbar"
        
        log "App-Logs:"
        journalctl -u scandy --no-pager -n 20 2>/dev/null || echo "Journalctl nicht verfügbar"
        
        log "Manuelle Logs:"
        if [ -f "/var/log/scandy.log" ]; then
            tail -20 /var/log/scandy.log
        else
            echo "Keine manuellen Logs verfügbar"
        fi
        
        log "Verfügbare Dateien in /opt/scandy:"
        ls -la /opt/scandy/ | head -10
        
        log "Python-Dateien:"
        find /opt/scandy -name "*.py" -maxdepth 1
        
        log "Gunicorn-Konfiguration:"
        echo "APP_FILE: $APP_FILE"
        echo "MODULE_NAME: $MODULE_NAME"
        echo "EXEC_START: $EXEC_START"
        
        info "Prüfe Logs: journalctl -u scandy -f"
        info "Oder manuelle Logs: tail -f /var/log/scandy.log"
        exit 1
    fi
    sleep 2
done

# 13. Fertig!
echo ""
success "Installation abgeschlossen!"
echo "🌐 Web-App: http://$(hostname -I | awk '{print $1}'):$WEB_PORT"
echo "📊 MongoDB: mongodb://localhost:27017/scandy"
echo "📝 Logs: journalctl -u scandy -f"
echo ""
echo "Das war's! Einfach und robust. 🎯"
