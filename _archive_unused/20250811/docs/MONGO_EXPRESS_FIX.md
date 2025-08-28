# 🔧 Mongo Express Authentifizierungsproblem - Lösung

## 🚨 **Problem**
Mongo Express konnte sich nicht mit MongoDB verbinden und zeigte folgende Fehler:
```
MongoServerError: Authentication failed.
AuthenticationFailed: SCRAM authentication failed, storedKey mismatch
```

## 🔍 **Ursache**
Das Problem lag daran, dass MongoDB bereits mit einem anderen Passwort initialisiert wurde, als das in der `.env` Datei konfigurierte Passwort. Dies führte zu einem "storedKey mismatch" Fehler.

## ✅ **Lösung**

### 1. **Container und Volumes komplett entfernen**
```bash
docker compose down -v
```
- `-v` Flag entfernt auch alle Docker Volumes
- Dies löscht die alte MongoDB-Datenbank mit dem falschen Passwort

### 2. **Docker Compose Konfiguration korrigiert**
In `docker-compose.yml` wurden die Mongo Express Umgebungsvariablen direkt gesetzt:
```yaml
environment:
  ME_CONFIG_MONGODB_ADMINUSERNAME: admin
  ME_CONFIG_MONGODB_ADMINPASSWORD: as1LYetkPfzsnZTFRkAts51ep
  ME_CONFIG_MONGODB_URL: mongodb://admin:as1LYetkPfzsnZTFRkAts51ep@scandy-mongodb-scandy:27017/
  ME_CONFIG_BASICAUTH_USERNAME: admin
  ME_CONFIG_BASICAUTH_PASSWORD: as1LYetkPfzsnZTFRkAts51ep
```

### 3. **Container neu starten**
```bash
docker compose up -d
```

## 🎯 **Ergebnis**
- ✅ Mongo Express verbindet sich erfolgreich mit MongoDB
- ✅ Alle Container laufen im "healthy" Status
- ✅ Keine Authentifizierungsfehler mehr

## 📋 **Verfügbare Services**
- **Scandy App**: http://localhost:5000
- **Mongo Express**: http://localhost:8081
- **MongoDB**: localhost:27017

## 🔐 **Zugangsdaten**
- **Mongo Express Login**: admin / as1LYetkPfzsnZTFRkAts51ep
- **MongoDB Admin**: admin / as1LYetkPfzsnZTFRkAts51ep

## 💡 **Prävention**
Bei zukünftigen Problemen:
1. Immer `docker compose down -v` verwenden, um saubere Volumes zu haben
2. Passwörter in `.env` und `docker-compose.yml` synchron halten
3. Bei Authentifizierungsproblemen: Volumes löschen und neu initialisieren 