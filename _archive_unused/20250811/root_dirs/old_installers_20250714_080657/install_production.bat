@echo off
echo ========================================
echo Scandy Produktions-Installation
echo ========================================
echo.

echo Stoppe bestehende Container...
docker-compose down

echo.
echo Baue Container mit Produktionsserver...
docker-compose build --no-cache

echo.
echo Starte Container...
docker-compose up -d

echo.
echo Warte auf Container-Start...
timeout /t 10 /nobreak >nul

echo.
echo Pruefe Container-Status...
docker-compose ps

echo.
echo Pruefe Logs...
docker-compose logs --tail=20 scandy-app

echo.
echo ========================================
echo Installation abgeschlossen!
echo ========================================
echo.
echo Anwendung: http://localhost:5000
echo Mongo Express: http://localhost:8081
echo.
echo Logs anzeigen: docker-compose logs -f
echo Container stoppen: docker-compose down
echo.
pause 