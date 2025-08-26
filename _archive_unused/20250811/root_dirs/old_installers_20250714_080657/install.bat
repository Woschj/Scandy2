@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ========================================
echo ========================================
echo Scandy Komplette Installation
echo ========================================
echo Dieses Skript installiert Scandy komplett neu:
echo - Scandy App
echo - MongoDB Datenbank
echo - Mongo Express (Datenbank-Verwaltung)
echo ========================================
echo.

REM Prüfe ob Docker installiert ist
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Docker ist nicht installiert oder nicht verfuegbar!
    echo Bitte installiere Docker und starte es neu.
    pause
    exit /b 1
)

REM Prüfe ob Docker läuft
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Docker läuft nicht!
    echo Bitte starte Docker und versuche es erneut.
    pause
    exit /b 1
)

echo ✅ Docker gefunden. Starte komplette Installation...
echo.

REM Prüfe ob .env existiert, falls nicht erstelle sie
if not exist ".env" (
    echo 📝 Erstelle .env-Datei aus env.example...
    copy env.example .env >nul
    echo ✅ .env-Datei erstellt!
    echo ⚠️  Bitte passe die Werte in .env an deine Umgebung an!
    echo.
) else (
    echo 📝 .env-Datei existiert bereits.
    echo ⚠️  Stelle sicher, dass alle MongoDB-Variablen korrekt gesetzt sind!
    echo.
)

REM Validiere wichtige .env-Variablen
echo 🔍 Validiere .env-Konfiguration...
if exist ".env" (
    REM Lade .env-Datei und prüfe wichtige Variablen
    set missing_vars=
    
    REM Prüfe MONGO_INITDB_ROOT_USERNAME
    findstr /C:"MONGO_INITDB_ROOT_USERNAME=" .env >nul 2>&1
    if %errorlevel% neq 0 (
        set missing_vars=!missing_vars! MONGO_INITDB_ROOT_USERNAME
    )
    
    REM Prüfe MONGO_INITDB_ROOT_PASSWORD
    findstr /C:"MONGO_INITDB_ROOT_PASSWORD=" .env >nul 2>&1
    if %errorlevel% neq 0 (
        set missing_vars=!missing_vars! MONGO_INITDB_ROOT_PASSWORD
    )
    
    REM Prüfe MONGO_INITDB_DATABASE
    findstr /C:"MONGO_INITDB_DATABASE=" .env >nul 2>&1
    if %errorlevel% neq 0 (
        set missing_vars=!missing_vars! MONGO_INITDB_DATABASE
    )
    
    REM Prüfe MONGODB_URI
    findstr /C:"MONGODB_URI=" .env >nul 2>&1
    if %errorlevel% neq 0 (
        set missing_vars=!missing_vars! MONGODB_URI
    )
    
    if not "!missing_vars!"=="" (
        echo ❌ Fehlende wichtige Umgebungsvariablen:!missing_vars!
        echo.
        echo ⚠️  Bitte passe die .env-Datei an und starte die Installation erneut!
        pause
        exit /b 1
    ) else (
        echo ✅ Alle wichtigen Umgebungsvariablen sind gesetzt!
    )
)

REM Prüfe ob bereits eine Installation existiert
if exist "docker-compose.yml" (
    echo ⚠️  Bestehende Installation gefunden!
    echo.
    echo Optionen:
    echo 1 = Abbrechen
    echo 2 = Komplett neu installieren (ALLE Daten gehen verloren!)
    echo 3 = Nur App neu installieren (Daten bleiben erhalten)
    echo.
    set /p choice="Wählen Sie (1-3): "
    if "!choice!"=="1" (
        echo Installation abgebrochen.
        pause
        exit /b 0
    ) else if "!choice!"=="2" (
        echo ⚠️  KOMPLETT NEU INSTALLIEREN - ALLE DATEN GEHEN VERLOREN!
        set /p confirm="Sind Sie sicher? (j/N): "
        if /i not "!confirm!"=="j" (
            echo Installation abgebrochen.
            pause
            exit /b 0
        )
        echo 🔄 Komplett neu installieren...
        
        REM Sichere Backups vor dem Löschen
        if exist "backups" (
            echo 💾 Sichere bestehende Backups...
            if not exist "backups_backup" (
                xcopy "backups" "backups_backup" /E /I /H /Y >nul 2>&1
                echo ✅ Backups gesichert in: backups_backup\
            ) else (
                echo ⚠️  Backup-Ordner existiert bereits: backups_backup\
            )
        )
        
        docker compose down -v
        docker system prune -f
        docker volume prune -f
        if exist "data" rmdir /s /q data
        if exist "backups" rmdir /s /q backups
        if exist "logs" rmdir /s /q logs
    ) else if "!choice!"=="3" (
        echo 🔄 Nur App neu installieren...
        echo Führe update.bat aus...
        call update.bat
        exit /b 0
    ) else (
        echo Ungueltige Auswahl. Installation abgebrochen.
        pause
        exit /b 1
    )
)

REM Erstelle Datenverzeichnisse
echo 📁 Erstelle Datenverzeichnisse...
if not exist "data" mkdir data
if not exist "data\backups" mkdir data\backups
if not exist "data\logs" mkdir data\logs
if not exist "data\static" mkdir data\static
if not exist "data\uploads" mkdir data\uploads
if not exist "backups" mkdir backups
if not exist "logs" mkdir logs

REM Stoppe laufende Container falls vorhanden
echo 🛑 Stoppe laufende Container...
docker compose down -v >nul 2>&1

REM Entferne alte Images
echo 🗑️  Entferne alte Images...
docker images | findstr scandy >nul 2>&1 && for /f "tokens=3" %%i in ('docker images ^| findstr scandy') do docker rmi -f %%i >nul 2>&1
docker images | findstr mongo >nul 2>&1 && for /f "tokens=3" %%i in ('docker images ^| findstr mongo') do docker rmi -f %%i >nul 2>&1

REM Baue und starte alle Container
echo 🔨 Baue und starte alle Container...
docker compose up -d --build
if %errorlevel% neq 0 (
    echo ❌ ERROR: Fehler beim Bauen der Container!
    echo Versuche es mit einfachem Build...
    docker compose build --no-cache
    docker compose up -d
)
if %errorlevel% neq 0 (
    echo ❌ ERROR: Installation fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo ⏳ Warte auf Start aller Services...
REM Warte auf MongoDB Health Status
set /a retries=0
:wait_for_mongo
REM Prüfe ob MongoDB Container läuft
docker ps | findstr scandy-mongodb >nul 2>&1
if %errorlevel% neq 0 (
    echo ⏳ MongoDB Container startet noch...
    timeout /t 5 >nul
    set /a retries+=1
    if !retries! geq 12 (
        echo ❌ MongoDB Container startet nicht!
        echo Container Status:
        docker compose ps
        echo.
        echo MongoDB Logs:
        docker compose logs --tail=20 scandy-mongodb
        echo.
        echo ⚠️  Installation trotzdem fortgesetzt - MongoDB startet möglicherweise später...
        goto continue_installation
    )
    goto wait_for_mongo
)

REM Prüfe Health Status von MongoDB
set health_retries=0
:wait_for_health
for /f "delims=" %%H in ('docker inspect -f "{{.State.Health.Status}}" scandy-mongodb 2^>nul') do set HEALTH=%%H
if not "!HEALTH!"=="healthy" (
    set /a health_retries+=1
    if !health_retries! geq 15 (
        echo ⚠️  MongoDB wird nicht healthy - fahre trotzdem fort...
        echo Letzte MongoDB Logs:
        docker compose logs --tail=10 scandy-mongodb
        echo.
        goto continue_installation
    )
    echo ⏳ Warte auf MongoDB Health... (!health_retries!/15)
    timeout /t 6 >nul
    goto wait_for_health
)
echo ✅ MongoDB ist healthy und bereit!

:continue_installation
echo 🔍 Prüfe Container-Status...
docker compose ps

echo 🔍 Prüfe Service-Verfügbarkeit...
REM Prüfe Mongo Express
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:8081' -UseBasicParsing -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Mongo Express läuft
) else (
    echo ⚠️  Mongo Express startet noch...
)
REM Prüfe Scandy App
powershell -Command "try { Invoke-WebRequest -Uri 'http://localhost:5000' -UseBasicParsing -TimeoutSec 5 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Scandy App läuft
) else (
    echo ⚠️  Scandy App startet noch...
)

echo.
echo ========================================
echo ✅ KOMPLETTE INSTALLATION ABGESCHLOSSEN!
echo ========================================
echo.
echo 🎉 Alle Services sind installiert und verfügbar:
echo.
echo 🌐 Web-Anwendungen:
echo - Scandy App:     http://localhost:5000
echo - Mongo Express:  http://localhost:8081
echo.
echo 🔐 Standard-Zugangsdaten:
echo - Admin: admin / admin123
echo - Teilnehmer: teilnehmer / admin123
echo.
echo 📊 Datenbank-Zugang (Mongo Express):
echo - Benutzer: admin
echo - Passwort: [aus Umgebungsvariable MONGO_INITDB_ROOT_PASSWORD]
echo.
echo 📁 Datenverzeichnisse:
echo - Backups: .\backups\
echo - Logs:    .\logs\
echo - Uploads: .\data\uploads\
echo.
echo 🔧 Nützliche Befehle:
echo - Status aller Container: docker compose ps
echo - Logs anzeigen:         docker compose logs -f
echo - Stoppen:               docker compose down
echo - Neustart:              docker compose restart
echo - Nur App updaten:       update.bat
echo.
echo ⚠️  WICHTIG: Für Updates verwenden Sie update.bat
echo    Das schont die Datenbank und ist schneller!
echo.
echo ========================================
pause 