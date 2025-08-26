# LXC Container Update Anleitung

## Problem
Bei LXC-Container-Updates wird der Code nicht korrekt in das `/opt/scandy/app` Verzeichnis kopiert.

## Lösung

### Option 1: Einfache Code-Kopierung (empfohlen)

**Nach dem git pull im Container:**
```bash
./copy_code_to_scandy.sh
```

### Option 2: Vollständiges Update
```bash
./lxc_update.sh
```

### Option 3: Quick Update
```bash
./quick_update.sh
```

## Schritt-für-Schritt Anleitung

### 1. Code aktualisieren (im /Scandy2/ Verzeichnis)
```bash
cd /Scandy2
git pull origin IT-VW
```

### 2. Code kopieren
```bash
./update_scandy_lxc.sh
```

### Alternative: Einfache Code-Kopierung
```bash
./copy_code_to_scandy.sh
```

### 3. Service prüfen
```bash
curl http://localhost:5000/health
```

## Was macht copy_code_to_scandy.sh?

1. ✅ **Prozess stoppen:** Stoppt Scandy-Prozesse
2. ✅ **Backup erstellen:** Sichert alten Code
3. ✅ **Code kopieren:** `app/*` → `/opt/scandy/app/`
4. ✅ **Berechtigungen:** Setzt korrekte Berechtigungen
5. ✅ **Dependencies:** Aktualisiert Python-Pakete
6. ✅ **Service starten:** Startet Scandy neu
7. ✅ **Status prüfen:** Wartet auf Service-Bereitschaft

## Debugging

### Prüfe ob Code kopiert wurde:
```bash
ls -la /opt/scandy/app/
```

### Prüfe Logs:
```bash
tail -f /opt/scandy/logs/app.log
```

### Prüfe Prozesse:
```bash
ps aux | grep scandy
```

## Häufige Probleme

### 1. Berechtigungen
```bash
sudo chown -R scandy:scandy /opt/scandy/app/
```

### 2. Service startet nicht
```bash
cd /opt/scandy
sudo -u scandy ./start_scandy.sh
```

### 3. Code wird nicht kopiert
```bash
# Manuell kopieren
cp -r app/* /opt/scandy/app/
```

## Verzeichnisstruktur

```
/Scandy2/                   # ← Quellverzeichnis (Git)
├── app/                    # ← Hier ist der Code von GitHub
├── copy_code_to_scandy.sh  # ← Code-Kopierung Script
└── update_scandy_lxc.sh    # ← Vollständiges Update Script

/opt/scandy/                # ← Zielverzeichnis (Installation)
├── app/                    # ← Hier muss der Code hin
├── venv/                   # Python Virtual Environment
├── logs/                   # Log-Dateien
├── start_scandy.sh         # Start-Script
└── requirements.txt        # Python-Dependencies
``` 