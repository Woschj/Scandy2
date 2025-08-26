# 🔒 Lokales SSL Setup für Scandy (ohne Domain)

## ✅ Lösung für lokale Server

**Für lokale Server ohne Domain gibt es mehrere Lösungen:**

### 🎯 **Empfohlene Lösung: Selbst-signiertes Zertifikat**

#### ✅ Vorteile:
- **Kostenlos** und einfach zu implementieren
- **Vollständige HTTPS-Verschlüsselung**
- **Alle Security Features** verfügbar
- **Keine Domain erforderlich**

#### ⚠️ Nachteile:
- **Browser-Warnung** (kann umgangen werden)
- **Zertifikat muss importiert** werden
- **Nur für lokale Nutzung**

## 🚀 Schnelle Einrichtung

### 1. **Automatisches Setup-Skript verwenden:**

```bash
# Skript ausführbar machen
chmod +x local_ssl_setup.sh

# Setup ausführen
./local_ssl_setup.sh
```

### 2. **Manuelle Einrichtung:**

```bash
# 1. Nginx installieren
sudo apt update
sudo apt install nginx -y

# 2. SSL-Verzeichnis erstellen
sudo mkdir -p /etc/ssl/scandy

# 3. Selbst-signiertes Zertifikat erstellen
SERVER_IP=$(hostname -I | awk '{print $1}')
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/scandy/scandy.key \
    -out /etc/ssl/scandy/scandy.crt \
    -subj "/C=DE/ST=Germany/L=Local/O=Scandy/OU=IT/CN=$SERVER_IP" \
    -addext "subjectAltName=DNS:localhost,DNS:$SERVER_IP,IP:$SERVER_IP,IP:127.0.0.1"

# 4. Nginx-Konfiguration erstellen
sudo tee /etc/nginx/sites-available/scandy-local > /dev/null <<EOF
server {
    listen 80;
    server_name $SERVER_IP localhost;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $SERVER_IP localhost;
    
    ssl_certificate /etc/ssl/scandy/scandy.crt;
    ssl_certificate_key /etc/ssl/scandy/scandy.key;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 5. Nginx-Konfiguration aktivieren
sudo ln -sf /etc/nginx/sites-available/scandy-local /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔧 Browser-Zertifikat importieren

### **Chrome/Edge:**
1. Öffnen Sie `https://IHRE-SERVER-IP`
2. Klicken Sie auf "Erweitert" → "Zur Website"
3. Klicken Sie auf das Schloss-Symbol → "Zertifikat anzeigen"
4. Tab "Details" → "Zertifikat exportieren"
5. Speichern als `.crt` Datei
6. Chrome: Einstellungen → "Sicherheit" → "Zertifikate verwalten"
7. Tab "Vertrauenswürdige Stammzertifizierungsstellen" → "Importieren"

### **Firefox:**
1. Öffnen Sie `https://IHRE-SERVER-IP`
2. Klicken Sie auf "Erweitert" → "Akzeptieren des Risikos und fortfahren"
3. Klicken Sie auf das Schloss-Symbol → "Zertifikat anzeigen"
4. Tab "Details" → "Exportieren"
5. Firefox: Einstellungen → "Datenschutz & Sicherheit" → "Zertifikate anzeigen"
6. Tab "Zertifizierungsstellen" → "Importieren"

## 📋 PHP-Dateien anpassen

### **Alle PHP-Dateien auf lokale IP ändern:**

```php
// Vorher:
$scandy_api_url = 'https://your-domain.com';

// Nachher:
$scandy_api_url = 'https://192.168.1.100';  // Ihre lokale IP
```

### **Betroffene Dateien:**
- `kantine_api_replacement.php`
- `kantine_corrected.php`
- `kantine_api.php`
- `test_wordpress_canteen.php`
- `kantine_api_2weeks.php`
- `kantine_api_production.php`
- `test_kantine_isolated.php`

## 🔄 Alternative Lösungen

### **Option 1: HTTP für lokale Entwicklung**
```bash
# Deaktivieren Sie HTTPS für lokale Entwicklung
# In .env-Datei:
SESSION_COOKIE_SECURE=False
REMEMBER_COOKIE_SECURE=False
```

### **Option 2: Cloudflare Tunnel**
```bash
# Kostenlose HTTPS ohne Domain
# Erfordert Cloudflare-Account
# Komplexere Konfiguration
```

### **Option 3: Reverse Proxy**
```bash
# HTTPS über bestehenden Server
# Erfordert bereits konfigurierten HTTPS-Server
```

## 🚨 Wichtige Hinweise

### **Sicherheitswarnungen:**
1. **Selbst-signierte Zertifikate** sind nur für lokale Entwicklung
2. **Browser zeigen Warnung** - das ist normal
3. **Zertifikat importieren** um Warnung zu entfernen
4. **Nicht für Produktion** verwenden

### **Produktionsumgebung:**
- Verwenden Sie **echte Domain** mit Let's Encrypt
- Oder **kommerzielle SSL-Zertifikate**
- **Nie selbst-signierte Zertifikate** in Produktion

## 📊 Vergleich der Lösungen

| Lösung | Kosten | Einfachheit | Sicherheit | Browser-Warnung |
|--------|--------|-------------|------------|-----------------|
| **Selbst-signiert** | Kostenlos | Einfach | ✅ Vollständig | ⚠️ Ja (entfernbar) |
| **HTTP lokal** | Kostenlos | Sehr einfach | ❌ Keine | ❌ Nein |
| **Domain + Let's Encrypt** | ~10€/Jahr | Mittel | ✅ Vollständig | ❌ Nein |
| **Cloudflare Tunnel** | Kostenlos | Komplex | ✅ Vollständig | ❌ Nein |

## ✅ Checkliste für lokales Setup

- [ ] Nginx installiert
- [ ] Selbst-signiertes Zertifikat erstellt
- [ ] Nginx-Konfiguration aktiviert
- [ ] Firewall konfiguriert
- [ ] Zertifikat in Browser importiert
- [ ] PHP-Dateien angepasst
- [ ] HTTPS-Verbindung getestet

## 🚀 Nächste Schritte

1. **Setup-Skript ausführen**:
   ```bash
   ./local_ssl_setup.sh
   ```

2. **Zertifikat importieren** (siehe Anleitung oben)

3. **PHP-Dateien anpassen**:
   ```bash
   # Alle PHP-Dateien auf lokale IP ändern
   sed -i 's/https:\/\/your-domain.com/https:\/\/192.168.1.100/g' *.php
   ```

4. **Testen**:
   ```bash
   curl -k https://IHRE-SERVER-IP
   ```

## 📞 Support

Bei Problemen:
1. Nginx-Logs prüfen: `sudo tail -f /var/log/nginx/error.log`
2. SSL-Zertifikat prüfen: `openssl x509 -in /etc/ssl/scandy/scandy.crt -text`
3. Port-Verfügbarkeit: `sudo netstat -tlnp | grep :443` 