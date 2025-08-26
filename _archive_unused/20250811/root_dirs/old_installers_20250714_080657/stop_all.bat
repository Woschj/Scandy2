@echo off
echo ========================================
echo Scandy - Alle Abteilungen stoppen
echo ========================================

echo.
echo Stoppe alle Scandy-Instanzen...
echo.

echo 1. BTZ...
docker-compose -f docker-compose.btz.yml down

echo 2. Werkstatt...
docker-compose -f docker-compose.werkstatt.yml down

echo 3. Verwaltung...
docker-compose -f docker-compose.verwaltung.yml down

echo.
echo ========================================
echo Alle Scandy-Instanzen gestoppt!
echo ========================================
echo.
pause 