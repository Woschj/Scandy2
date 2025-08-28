# 🔒 Scandy Sicherheits-Checkliste für Produktionsbereitstellung

## ✅ Vor der Bereitstellung

### 1. HTTPS/SSL-Konfiguration
- [ ] SSL-Zertifikat installiert (Let's Encrypt oder kommerziell)
- [ ] HTTP zu HTTPS Umleitung konfiguriert
- [ ] Alle HTTP-URLs in PHP-Dateien auf HTTPS geändert
- [ ] SSL-Verifikation in PHP-CURL aktiviert
- [ ] HSTS-Header konfiguriert

### 2. Passwort-Sicherheit
- [ ] Alle Standard-Passwörter geändert
- [ ] MongoDB-Root-Passwort sicher (mindestens 16 Zeichen)
- [ ] SECRET_KEY sicher generiert (mindestens 32 Zeichen)
- [ ] Admin-Passwort für Scandy geändert
- [ ] Mongo Express Basic Auth konfiguriert

### 3. Cookie-Sicherheit
- [ ] SESSION_COOKIE_SECURE=True
- [ ] REMEMBER_COOKIE_SECURE=True
- [ ] SESSION_COOKIE_HTTPONLY=True
- [ ] REMEMBER_COOKIE_HTTPONLY=True
- [ ] SameSite=Strict für alle Cookies

### 4. CSRF-Schutz
- [ ] Flask-WTF CSRF-Schutz aktiviert
- [ ] CSRF-Token in allen Formularen
- [ ] AJAX-Requests mit CSRF-Token

### 5. Security Headers
- [ ] X-Frame-Options: DENY
- [ ] X-Content-Type-Options: nosniff
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Content-Security-Policy konfiguriert
- [ ] Referrer-Policy: strict-origin-when-cross-origin
- [ ] Permissions-Policy konfiguriert

### 6. Rate Limiting
- [ ] Flask-Limiter installiert
- [ ] Rate Limiting für Login-Endpunkte
- [ ] Rate Limiting für API-Endpunkte
- [ ] Rate Limiting für Upload-Endpunkte

### 7. Datenbank-Sicherheit
- [ ] MongoDB-Authentifizierung aktiviert
- [ ] Netzwerk-Zugriff auf MongoDB beschränkt
- [ ] Backup-Strategie implementiert
- [ ] Datenbank-Passwörter verschlüsselt gespeichert

### 8. Datei-Upload-Sicherheit
- [ ] Dateityp-Validierung implementiert
- [ ] Dateigrößen-Limits gesetzt
- [ ] Ausführung von Upload-Dateien verhindert
- [ ] Upload-Verzeichnis außerhalb Web-Root

### 9. Netzwerk-Sicherheit
- [ ] Firewall konfiguriert
- [ ] Unnötige Ports geschlossen
- [ ] SSH-Zugriff auf Schlüssel beschränkt
- [ ] Fail2ban installiert und konfiguriert

### 10. Monitoring und Logging
- [ ] Log-Rotation konfiguriert
- [ ] Security-Events geloggt
- [ ] Monitoring für ungewöhnliche Aktivitäten
- [ ] Backup-Monitoring implementiert

## 🔧 Konfigurationsdateien

### Nginx-Konfiguration
```bash
# SSL-Zertifikat installieren
sudo certbot --nginx -d your-domain.com

# Nginx-Konfiguration anwenden
sudo cp nginx_security_config.conf /etc/nginx/sites-available/scandy
sudo ln -s /etc/nginx/sites-available/scandy /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Docker-Compose (Produktion)
```yaml
environment:
  - SESSION_COOKIE_SECURE=True
  - REMEMBER_COOKIE_SECURE=True
  - FLASK_ENV=production
  - DEBUG=False
```

### .env-Datei (Produktion)
```env
SESSION_COOKIE_SECURE=True
REMEMBER_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
REMEMBER_COOKIE_HTTPONLY=True
FLASK_ENV=production
DEBUG=False
FORCE_HTTPS=True
```

## 🚨 Kritische Sicherheitsprüfungen

### PHP-Dateien korrigieren
```php
// FALSCH:
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
$scandy_api_url = 'http://10.42.2.107';

// RICHTIG:
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);
curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);
$scandy_api_url = 'https://your-domain.com';
```

### Alle betroffenen PHP-Dateien:
- [ ] kantine_api_replacement.php
- [ ] kantine_corrected.php
- [ ] kantine_api.php
- [ ] test_wordpress_canteen.php
- [ ] kantine_api_2weeks.php
- [ ] kantine_api_production.php

## 📋 Regelmäßige Sicherheitsprüfungen

### Täglich
- [ ] Log-Dateien auf ungewöhnliche Aktivitäten prüfen
- [ ] Backup-Status überprüfen
- [ ] System-Updates prüfen

### Wöchentlich
- [ ] SSL-Zertifikat-Status prüfen
- [ ] Datenbank-Backups testen
- [ ] Security-Headers testen

### Monatlich
- [ ] Vollständige Sicherheitsüberprüfung
- [ ] Passwort-Rotation
- [ ] Zugriffsberechtigungen überprüfen

## 🛠️ Tools für Sicherheitstests

### SSL-Test
```bash
# SSL-Labs Test
curl -s "https://api.ssllabs.com/api/v3/analyze?host=your-domain.com"

# Lokaler SSL-Test
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### Security Headers Test
```bash
# Security Headers prüfen
curl -I https://your-domain.com

# CSP-Test
curl -H "Content-Security-Policy-Report-Only: default-src 'self'" https://your-domain.com
```

### Rate Limiting Test
```bash
# Rate Limiting testen
for i in {1..30}; do curl -I https://your-domain.com/auth/login; done
```

## 📞 Notfall-Kontakte

- **System-Administrator**: [Kontakt]
- **Security-Team**: [Kontakt]
- **Backup-Verantwortlicher**: [Kontakt]

## 🚨 Incident Response

1. **Sofortige Maßnahmen**
   - System isolieren
   - Logs sichern
   - Backup-Integrität prüfen

2. **Analyse**
   - Angriffsvektor identifizieren
   - Betroffene Systeme ermitteln
   - Datenverlust bewerten

3. **Wiederherstellung**
   - System aus Backup wiederherstellen
   - Sicherheitslücken schließen
   - Monitoring verstärken

4. **Dokumentation**
   - Incident dokumentieren
   - Lessons Learned sammeln
   - Sicherheitsmaßnahmen anpassen 