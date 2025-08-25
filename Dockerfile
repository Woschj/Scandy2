# Einfaches Dockerfile für Scandy (App-Stufe)
FROM python:3.11-slim

# Installiere System-Abhängigkeiten
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    wget \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# HINWEIS: mongorestore nicht im Image installieren – die App hat einen Python-Fallback,
# falls mongorestore nicht verfügbar ist. Das vermeidet Build-Fehler auf restriktiven Netzwerken.

WORKDIR /app

# Build-Argument für Requirements-Rebuild
ARG REBUILD_REQUIREMENTS=false

# Kopiere nur die notwendigen Dateien
COPY requirements.txt .

# Requirements installieren (immer neu installieren bei Updates)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Node.js-Abhängigkeiten installieren
COPY package*.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./
RUN npm install --silent && \
    npm update --silent && \
    npm audit fix --silent || true

# App-Code kopieren und CSS bauen
COPY app ./app
RUN npm run build:css

# Erstelle notwendige Verzeichnisse
RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/static /app/tmp

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app/wsgi.py

# Exponiere Port
EXPOSE 5000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Starte die Anwendung mit Gunicorn (Produktions-WSGI-Server)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "100", "app.wsgi:application"] 