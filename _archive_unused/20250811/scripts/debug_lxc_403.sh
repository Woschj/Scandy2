#!/bin/bash

echo "=== DEBUG LXC 403 FEHLER ==="
echo "Zeit: $(date)"
echo ""

echo "=== 1. SYSTEMD SERVICE STATUS ==="
systemctl status scandy --no-pager
echo ""

echo "=== 2. SYSTEMD SERVICE LOGS (letzte 20 Zeilen) ==="
journalctl -u scandy -n 20 --no-pager
echo ""

echo "=== 3. ANWENDUNGS-LOGS ==="
if [ -f "/opt/scandy/logs/app.log" ]; then
    echo "--- /opt/scandy/logs/app.log (letzte 20 Zeilen) ---"
    tail -n 20 /opt/scandy/logs/app.log
else
    echo "❌ /opt/scandy/logs/app.log nicht gefunden"
fi

if [ -f "/opt/scandy/app/logs/app.log" ]; then
    echo "--- /opt/scandy/app/logs/app.log (letzte 20 Zeilen) ---"
    tail -n 20 /opt/scandy/app/logs/app.log
else
    echo "❌ /opt/scandy/app/logs/app.log nicht gefunden"
fi
echo ""

echo "=== 4. ERROR LOGS ==="
if [ -f "/opt/scandy/logs/error.log" ]; then
    echo "--- /opt/scandy/logs/error.log (letzte 20 Zeilen) ---"
    tail -n 20 /opt/scandy/logs/error.log
else
    echo "❌ /opt/scandy/logs/error.log nicht gefunden"
fi

if [ -f "/opt/scandy/app/logs/error.log" ]; then
    echo "--- /opt/scandy/app/logs/error.log (letzte 20 Zeilen) ---"
    tail -n 20 /opt/scandy/app/logs/error.log
else
    echo "❌ /opt/scandy/app/logs/error.log nicht gefunden"
fi
echo ""

echo "=== 5. WEB SERVER LOGS ==="
if [ -f "/var/log/nginx/error.log" ]; then
    echo "--- Nginx Error Log (letzte 10 Zeilen) ---"
    tail -n 10 /var/log/nginx/error.log
else
    echo "❌ Nginx error.log nicht gefunden"
fi

if [ -f "/var/log/apache2/error.log" ]; then
    echo "--- Apache Error Log (letzte 10 Zeilen) ---"
    tail -n 10 /var/log/apache2/error.log
else
    echo "❌ Apache error.log nicht gefunden"
fi
echo ""

echo "=== 6. DOCKER LOGS (falls Docker verwendet) ==="
if command -v docker &> /dev/null; then
    if docker ps | grep -q scandy; then
        echo "--- Docker Logs (letzte 20 Zeilen) ---"
        docker logs scandy --tail 20
    else
        echo "❌ Scandy Docker Container nicht gefunden"
    fi
else
    echo "❌ Docker nicht installiert"
fi
echo ""

echo "=== 7. PROZESS STATUS ==="
echo "--- Python Prozesse ---"
ps aux | grep python | grep -v grep
echo ""

echo "=== 8. PORT STATUS ==="
echo "--- Offene Ports ---"
netstat -tlnp | grep :5000
netstat -tlnp | grep :80
netstat -tlnp | grep :443
echo ""

echo "=== 9. DATEI BERECHTIGUNGEN ==="
echo "--- Scandy Verzeichnis ---"
ls -la /opt/scandy/ 2>/dev/null || echo "❌ /opt/scandy/ nicht gefunden"
echo ""

echo "=== 10. ENVIRONMENT VARIABLES ==="
echo "--- FLASK_ENV ---"
echo "FLASK_ENV: $FLASK_ENV"
echo "FLASK_DEBUG: $FLASK_DEBUG"
echo ""

echo "=== DEBUG ABGESCHLOSSEN ===" 