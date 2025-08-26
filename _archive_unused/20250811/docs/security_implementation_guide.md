# 🔒 Sicherheits-Implementierungsanleitung für Scandy

## ✅ Vollständige Sicherheitsimplementierung

### 1. **HTTPS/SSL-Konfiguration**

#### Alle PHP-Dateien korrigiert:
- ✅ `kantine_api_replacement.php` - HTTPS + SSL-Verifikation
- ✅ `kantine_corrected.php` - HTTPS + SSL-Verifikation  
- ✅ `kantine_api.php` - HTTPS + SSL-Verifikation
- ✅ `test_wordpress_canteen.php` - HTTPS + SSL-Verifikation
- ✅ `kantine_api_2weeks.php` - HTTPS + SSL-Verifikation
- ✅ `kantine_api_production.php` - HTTPS + SSL-Verifikation
- ✅ `test_kantine_isolated.php` - HTTPS + SSL-Verifikation

#### SSL-Zertifikat installieren:
```bash
# Let's Encrypt SSL-Zertifikat installieren
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Automatische Erneuerung
sudo crontab -e
# Füge hinzu: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. **CSRF-Schutz implementiert**

#### Flask-WTF CSRF-Schutz:
- ✅ CSRF-Schutz in `app/__init__.py` aktiviert
- ✅ CSRF-Token in allen Formularen hinzugefügt:
  - ✅ Login-Formular (`auth/login.html`)
  - ✅ Profil-Formular (`auth/profile.html`)
  - ✅ Setup-Formular (`setup.html`)
- ✅ Automatische CSRF-Token für AJAX-Requests in `base.html`

#### CSRF-Token in Formularen:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

### 3. **Security Headers implementiert**

#### Produktionskonfiguration (`app/config/config.py`):
```python
SECURITY_HEADERS = {
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'",
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
}
```

### 4. **Cookie-Sicherheit**

#### Sichere Cookie-Einstellungen:
```python
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
REMEMBER_COOKIE_SECURE = True
REMEMBER_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_SAMESITE = 'Strict'
```

### 5. **Rate Limiting**

#### Flask-Limiter implementiert:
```python
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

### 6. **HTTPS-Umleitung**

#### Automatische HTTP zu HTTPS Umleitung:
```python
@app.before_request
def force_https():
    if not request.is_secure and request.headers.get('X-Forwarded-Proto', 'http') == 'http':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
```

## 🔧 Nginx-Konfiguration

### Sichere Nginx-Konfiguration (`nginx_security_config.conf`):
```nginx
# HTTP zu HTTPS Umleitung
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server mit Security Headers
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL-Konfiguration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL-Sicherheitseinstellungen
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=scandy:10m rate=10r/s;
    limit_req zone=scandy burst=20 nodelay;
}
```

## 📋 Deployment-Checkliste

### Vor der Produktionsbereitstellung:

1. **SSL-Zertifikat installieren**:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

2. **Nginx-Konfiguration anwenden**:
   ```bash
   sudo cp nginx_security_config.conf /etc/nginx/sites-available/scandy
   sudo ln -s /etc/nginx/sites-available/scandy /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

3. **Umgebungsvariablen setzen**:
   ```bash
   # In .env-Datei:
   SESSION_COOKIE_SECURE=True
   REMEMBER_COOKIE_SECURE=True
   SESSION_COOKIE_HTTPONLY=True
   REMEMBER_COOKIE_HTTPONLY=True
   FLASK_ENV=production
   DEBUG=False
   FORCE_HTTPS=True
   ```

4. **Docker-Compose aktualisieren**:
   ```yaml
   environment:
     - SESSION_COOKIE_SECURE=True
     - REMEMBER_COOKIE_SECURE=True
     - FLASK_ENV=production
     - DEBUG=False
   ```

5. **PHP-Dateien konfigurieren**:
   ```php
   // Alle PHP-Dateien verwenden jetzt:
   $scandy_api_url = 'https://your-domain.com';
   curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
   curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
   ```

## 🚨 Sicherheitstests

### SSL-Test:
```bash
# SSL-Labs Test
curl -s "https://api.ssllabs.com/api/v3/analyze?host=your-domain.com"

# Lokaler SSL-Test
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### Security Headers Test:
```bash
# Security Headers prüfen
curl -I https://your-domain.com

# CSP-Test
curl -H "Content-Security-Policy-Report-Only: default-src 'self'" https://your-domain.com
```

### Rate Limiting Test:
```bash
# Rate Limiting testen
for i in {1..30}; do curl -I https://your-domain.com/auth/login; done
```

## 📊 Sicherheitsstatus

### ✅ Vollständig implementiert:
- **HTTPS/SSL**: Alle PHP-Dateien korrigiert
- **CSRF-Schutz**: Vollständig implementiert
- **Security Headers**: Vollständig implementiert
- **Cookie-Sicherheit**: Vollständig implementiert
- **Rate Limiting**: Implementiert
- **HTTPS-Umleitung**: Implementiert

### 🔧 Noch zu konfigurieren:
- **SSL-Zertifikat**: Noch zu installieren
- **Nginx-Konfiguration**: Noch anzuwenden
- **Domain-Konfiguration**: Noch anzupassen

## 📞 Support

Bei Fragen zur Sicherheitsimplementierung:
1. Prüfen Sie die `security_checklist.md`
2. Testen Sie alle Sicherheitsmaßnahmen
3. Überwachen Sie die Logs auf ungewöhnliche Aktivitäten

Die Anwendung ist jetzt vollständig für eine sichere Produktionsbereitstellung vorbereitet! 