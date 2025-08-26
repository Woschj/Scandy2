@echo off
echo ========================================
echo Scandy BTZ - Start
echo ========================================

echo.
echo Starte BTZ-Scandy auf Port 5003...
echo MongoDB: Port 27020
echo Web-Interface: http://localhost:5003
echo.

docker-compose -f docker-compose.btz.yml up -d

echo.
echo BTZ-Scandy gestartet!
echo.
echo Zugriff:
echo - Web: http://localhost:5003
echo - MongoDB: localhost:27020
echo.
pause 