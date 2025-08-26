#!/bin/bash

# Stopp-Skript für Scandy Standard-Instanz
echo "Stoppe Scandy Standard-Instanz..."

# Stoppe die Standard-Instanz
docker compose down

echo "Scandy Standard-Instanz wurde gestoppt." 