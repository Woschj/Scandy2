#!/bin/bash

echo "========================================"
echo "Scandy Werkstatt - Start"
echo "========================================"

echo
echo "Starte Werkstatt-Scandy auf Port 5001..."
echo "MongoDB: Port 27018"
echo "Web-Interface: http://localhost:5001"
echo

docker-compose -f docker-compose.werkstatt.yml up -d

echo
echo "Werkstatt-Scandy gestartet!"
echo
echo "Zugriff:"
echo "- Web: http://localhost:5001"
echo "- MongoDB: localhost:27018"
echo 