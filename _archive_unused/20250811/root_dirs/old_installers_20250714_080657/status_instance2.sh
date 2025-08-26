#!/bin/bash

# Status-Skript für Scandy Instance 2
echo "Status von Scandy Instance 2:"
echo "================================"

# Zeige Container-Status
docker compose -f docker-compose-instance2.yml ps

echo ""
echo "Logs der letzten 20 Zeilen:"
echo "================================"
docker compose -f docker-compose-instance2.yml logs --tail=20 