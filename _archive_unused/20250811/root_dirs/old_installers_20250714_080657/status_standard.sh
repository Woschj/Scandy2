#!/bin/bash

# Status-Skript für Scandy Standard-Instanz
echo "Status von Scandy Standard-Instanz:"
echo "=================================="

# Zeige Container-Status
docker compose ps

echo ""
echo "Logs der letzten 20 Zeilen:"
echo "============================"
docker compose logs --tail=20 