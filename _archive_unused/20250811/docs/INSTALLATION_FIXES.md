# 🔧 Installationsskript-Behebungen

## ✅ Behobene Probleme

### 1. **macOS-Kompatibilität**
- **Problem**: `df -BG` funktioniert nicht auf macOS
- **Lösung**: OS-spezifische df-Befehle implementiert
  - macOS: `df -g` für GB
  - Linux: `df -BG` für GB

### 2. **Docker Compose V2 Support**
- **Problem**: Skript verwendete nur `docker compose` (V2), aber V1 nicht unterstützt
- **Lösung**: Automatische Erkennung und Fallback
  - Prüft `docker compose version` für V2
  - Fallback auf `docker-compose` für V1
  - Globale Variable `DOCKER_COMPOSE_CMD` für Konsistenz

### 3. **Systemd-Kompatibilität**
- **Problem**: Systemd ist auf macOS nicht verfügbar
- **Lösung**: OS-spezifische Prüfung
  - Nur auf Linux wird systemctl geprüft
  - macOS zeigt Info-Meldung statt Warnung

### 4. **Speicherplatz-Prüfung**
- **Problem**: `df -BG` Fehler auf macOS
- **Lösung**: Robuste Speicherplatz-Erkennung
  - Prüft ob Ergebnis eine Zahl ist
  - Zeigt Warnung bei unklaren Werten

## 🔧 Technische Details

### Docker Compose Erkennung
```bash
# Prüft Docker Compose V2
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE_V2=true
    DOCKER_COMPOSE_CMD="$DOCKER_CMD compose"
else
    DOCKER_COMPOSE_V2=false
    DOCKER_COMPOSE_CMD="$DOCKER_CMD-compose"
fi
```

### OS-spezifische df-Befehle
```bash
if [[ "$OS_TYPE" == "macos" ]]; then
    # macOS: df -g für GB
    AVAILABLE_SPACE=$(df -g . | tail -1 | awk '{print $4}' | sed 's/Gi//')
else
    # Linux: df -BG für GB
    AVAILABLE_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
fi
```

## 🧪 Getestete Umgebungen

### ✅ Funktioniert
- **macOS** (Docker Desktop)
- **Linux** (Ubuntu/Debian)
- **Docker Compose V2**
- **Docker Compose V1** (Fallback)

### ⚠️ Bekannte Einschränkungen
- **Windows**: Nicht unterstützt (WSL2 empfohlen)
- **Systemd**: Nur auf Linux verfügbar
- **Native Installation**: Benötigt Root-Rechte auf Linux

## 🚀 Verwendung

### System-Kompatibilität prüfen
```bash
./install_scandy_universal.sh --check-system
```

### Automatische Installation
```bash
./install_scandy_universal.sh --auto
```

### Docker-Installation
```bash
./install_scandy_universal.sh --docker
```

### Mit SSL/HTTPS
```bash
./install_scandy_universal.sh --docker --ssl --domain scandy.local
```

## 📝 Changelog

### Version 1.0.1
- ✅ macOS-Kompatibilität hinzugefügt
- ✅ Docker Compose V1/V2 Support
- ✅ Robuste Speicherplatz-Erkennung
- ✅ OS-spezifische Systemd-Prüfung
- ✅ Verbesserte Fehlerbehandlung

### Version 1.0.0
- 🎉 Erste Version des Universal Installers
- 🐳 Docker, LXC und Native Installation
- 🔒 SSL/HTTPS Support
- 📦 Automatische Backup-Funktionalität 