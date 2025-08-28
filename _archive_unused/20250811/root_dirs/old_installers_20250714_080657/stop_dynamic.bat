@echo off
echo ========================================
echo Scandy - Stoppe alle Abteilungen
echo ========================================

echo.
echo Stoppe alle dynamisch erstellten Container...
echo.

python stop_dynamic.py

echo.
pause 