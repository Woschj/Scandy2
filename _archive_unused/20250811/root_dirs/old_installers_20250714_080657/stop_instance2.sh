#!/bin/bash

# Stopp-Skript für Scandy Instance 2
echo "Stoppe Scandy Instance 2..."

# Stoppe die zweite Instanz
docker compose -f docker-compose-instance2.yml down

echo "Scandy Instance 2 wurde gestoppt." 