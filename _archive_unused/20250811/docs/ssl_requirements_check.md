# 🔒 SSL-Voraussetzungen für Scandy

## ✅ Erforderliche Voraussetzungen

### 1. **Domain-Name (OBLIGATORISCH)**

**Für Let's Encrypt SSL-Zertifikate benötigen Sie:**

#### ✅ Akzeptierte Optionen:
- **Eigene Domain**: `scandy.company.com`
- **Subdomain**: `scandy.ihre-domain.com`
- **Hauptdomain**: `ihre-domain.com`

#### ❌ Nicht möglich:
- **Nur IP-Adressen**: `192.168.1.100`
- **Lokale Adressen**: `localhost`
- **Private IPs**: `10.0.0.1`

### 2. **DNS-Konfiguration**

#### A-Record konfigurieren:
```
Typ: A-Record
Name: scandy (oder @ für Hauptdomain)
Wert: Ihre-Server-IP-Adresse
TTL: 300 (5 Minuten)
```

#### Beispiel DNS-Einträge:
```
scandy.company.com    A    203.0.113.1
*.scandy.company.com  A    203.0.113.1
```

### 3. **Server-Anforderungen**

#### ✅ Minimale Server-Anforderungen:
- **Betriebssystem**: Ubuntu 18.04+, CentOS 7+, Debian 9+
- **RAM**: 1 GB (2 GB empfohlen)
- **Speicher**: 10 GB freier Platz
- **Netzwerk**: Öffentliche IP-Adresse
- **Ports**: 80 (HTTP) und 443 (HTTPS) offen

#### ✅ Erforderliche Software:
- **Nginx**: Web-Server
- **Certbot**: SSL-Zertifikat-Management
- **Python 3.6+**: Für Certbot

## 🔧 Installation der Voraussetzungen

### Automatisches Setup-Skript verwenden:

```bash
# Skript ausführbar machen
chmod +x server_ssl_setup.sh

# Setup ausführen
./server_ssl_setup.sh
```

### Manuelle Installation:

#### 1. **Nginx installieren**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx -y

# CentOS/RHEL
sudo yum install nginx -y

# Nginx starten
sudo systemctl enable nginx
sudo systemctl start nginx
```

#### 2. **Certbot installieren**:
```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx -y

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx -y
```

#### 3. **Firewall konfigurieren**:
```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## 📋 Domain-Registrierung (falls erforderlich)

### Empfohlene Domain-Registrare:
- **Namecheap**: Günstig, gute Support
- **GoDaddy**: Große Auswahl
- **Hover**: Einfach zu bedienen
- **Google Domains**: Integration mit Google-Services

### Domain-Preise (jährlich):
- **.com**: ~10-15€
- **.de**: ~10-15€
- **.net**: ~12-18€
- **.org**: ~12-18€

## 🚨 Häufige Probleme und Lösungen

### Problem 1: "Domain nicht erreichbar"
**Lösung:**
```bash
# DNS-Auflösung testen
nslookup ihre-domain.com

# Port-Verfügbarkeit testen
nc -z ihre-domain.com 80
```

### Problem 2: "Certbot kann Domain nicht validieren"
**Lösung:**
1. DNS-Einträge prüfen
2. Warten Sie 24h für DNS-Propagation
3. Stellen Sie sicher, dass Port 80 erreichbar ist

### Problem 3: "Firewall blockiert Verbindung"
**Lösung:**
```bash
# Firewall-Status prüfen
sudo ufw status
sudo firewall-cmd --list-all

# Ports freigeben
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## 📊 Kostenübersicht

### Einmalige Kosten:
- **Domain-Registrierung**: 10-15€/Jahr
- **Server-Hosting**: 5-20€/Monat

### Laufende Kosten:
- **SSL-Zertifikat**: **KOSTENLOS** (Let's Encrypt)
- **Domain-Renewal**: 10-15€/Jahr
- **Server-Hosting**: 5-20€/Monat

## 🔄 Alternative Lösungen

### Option 1: Selbst-gehostete Domain
```bash
# Beispiel: scandy.local
# Erfordert lokale DNS-Konfiguration
# Nur für interne Nutzung
```

### Option 2: Cloudflare Tunnel
```bash
# Kostenlose HTTPS ohne Domain
# Erfordert Cloudflare-Account
# Komplexere Konfiguration
```

### Option 3: Reverse Proxy
```bash
# HTTPS über bestehenden Server
# Erfordert bereits konfigurierten HTTPS-Server
# Zusätzliche Komplexität
```

## ✅ Checkliste vor SSL-Installation

- [ ] Domain-Name registriert
- [ ] DNS-A-Record konfiguriert
- [ ] DNS-Propagation abgewartet (24h)
- [ ] Server erreichbar über Domain
- [ ] Nginx installiert und konfiguriert
- [ ] Certbot installiert
- [ ] Firewall konfiguriert
- [ ] Ports 80 und 443 offen
- [ ] Scandy-Anwendung läuft auf Port 5000

## 🚀 Nächste Schritte

1. **Domain registrieren** (falls noch nicht geschehen)
2. **DNS-Einträge konfigurieren**
3. **Server-Setup ausführen**:
   ```bash
   ./server_ssl_setup.sh
   ```
4. **SSL-Zertifikat installieren**:
   ```bash
   sudo certbot --nginx -d ihre-domain.com
   ```
5. **HTTPS-Verbindung testen**:
   ```bash
   curl -I https://ihre-domain.com
   ```

## 📞 Support

Bei Problemen:
1. DNS-Auflösung testen: `nslookup ihre-domain.com`
2. Port-Verfügbarkeit prüfen: `nc -z ihre-domain.com 80`
3. Nginx-Logs prüfen: `sudo tail -f /var/log/nginx/error.log`
4. Certbot-Logs prüfen: `sudo certbot certificates` 