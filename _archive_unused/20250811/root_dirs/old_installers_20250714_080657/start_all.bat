@echo off
echo ========================================
echo Scandy - Alle Abteilungen starten
echo ========================================

echo.
echo Starte alle Scandy-Instanzen...
echo.

echo 1. BTZ (Port 5003)...
docker-compose -f docker-compose.btz.yml up -d

echo 2. Werkstatt (Port 5001)...
docker-compose -f docker-compose.werkstatt.yml up -d

echo 3. Verwaltung (Port 5002)...
docker-compose -f docker-compose.verwaltung.yml up -d

echo.
echo ========================================
echo Alle Scandy-Instanzen gestartet!
echo ========================================
echo.
echo Zugriff:
echo - BTZ: http://localhost:5003
echo - Werkstatt: http://localhost:5001
echo - Verwaltung: http://localhost:5002
echo.
echo MongoDB-Ports:
echo - BTZ: localhost:27020
echo - Werkstatt: localhost:27018
echo - Verwaltung: localhost:27019
echo.
pause 