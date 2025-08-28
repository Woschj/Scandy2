#!/bin/bash

# Start-Skript für Scandy Standard-Instanz
echo "Starte Scandy Standard-Instanz..."

# Prüfe ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo "Fehler: Docker läuft nicht!"
    exit 1
fi

# Starte die Standard-Instanz
docker compose up -d

echo "Scandy Standard-Instanz wird gestartet..."
echo "App wird verfügbar sein unter: http://localhost:5000"
echo "MongoDB Admin unter: http://localhost:8081"
echo ""
echo "Status prüfen mit: docker compose ps" 