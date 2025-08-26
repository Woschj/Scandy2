#!/bin/bash

# Start-Skript für Scandy Instance 2
echo "Starte Scandy Instance 2..."

# Prüfe ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo "Fehler: Docker läuft nicht!"
    exit 1
fi

# Starte die zweite Instanz
docker compose -f docker-compose-instance2.yml up -d

echo "Scandy Instance 2 wird gestartet..."
echo "App wird verfügbar sein unter: http://localhost:5001"
echo "MongoDB Admin unter: http://localhost:8082"
echo ""
echo "Status prüfen mit: docker compose -f docker-compose-instance2.yml ps" 