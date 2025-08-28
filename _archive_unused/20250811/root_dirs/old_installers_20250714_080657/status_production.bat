@echo off
echo ========================================
echo Scandy Produktions-Status
echo ========================================
echo.

echo Container-Status:
docker-compose ps

echo.
echo Letzte Logs:
docker-compose logs --tail=10 scandy-app

echo.
echo Speicherplatz:
docker system df

echo.
echo ========================================
echo Status-Check abgeschlossen
echo ========================================
echo.
pause 