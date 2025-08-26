# Docker Update Problem - Lösung

## Problem
Bei Docker-Installationen wird der Code über ein Volume gemountet:
```yaml
volumes:
  - ./app:/app/app
```

Bei Updates wird nur das Docker-Image neu gebaut, aber der gemountete Code wird nicht automatisch aktualisiert.

## Lösung

### 1. Aktualisiertes Update-Script
Das `update_scandy_universal.sh` Script wurde erweitert:
- Container wird nach dem Build neu gestartet
- Gemountete Volumes werden aktualisiert

### 2. Quick Update Script
Neues `quick_update.sh` Script für schnelle Code-Updates:
```bash
./quick_update.sh
```

### 3. Manuelle Lösung
Falls die Scripts nicht funktionieren:

```bash
# Code aktualisieren
git pull origin IT-VW

# Container neu starten
docker compose restart scandy-app-scandy

# Oder vollständiger Rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Verwendung

### Für Code-Updates:
```bash
./quick_update.sh
```

### Für vollständige Updates:
```bash
./update_scandy_universal.sh
```

### Für manuelle Updates:
```bash
git pull origin IT-VW
docker compose restart scandy-app-scandy
```

## Debugging

### Prüfe Container-Status:
```bash
docker compose ps
```

### Prüfe Logs:
```bash
docker compose logs -f scandy-app-scandy
```

### Prüfe gemountete Volumes:
```bash
docker compose exec scandy-app-scandy ls -la /app/app
```

## Häufige Probleme

1. **Container startet nicht neu:**
   ```bash
   docker compose down
   docker compose up -d
   ```

2. **Code wird nicht aktualisiert:**
   ```bash
   docker compose restart scandy-app-scandy
   ```

3. **Docker-Cache Problem:**
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ``` 