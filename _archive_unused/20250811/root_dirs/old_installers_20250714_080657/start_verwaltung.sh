#!/bin/bash

echo "========================================"
echo "Scandy Verwaltung - Start"
echo "========================================"

echo
echo "Starte Verwaltungs-Scandy auf Port 5002..."
echo "MongoDB: Port 27019"
echo "Web-Interface: http://localhost:5002"
echo

docker-compose -f docker-compose.verwaltung.yml up -d

echo
echo "Verwaltungs-Scandy gestartet!"
echo
echo "Zugriff:"
echo "- Web: http://localhost:5002"
echo "- MongoDB: localhost:27019"
echo 