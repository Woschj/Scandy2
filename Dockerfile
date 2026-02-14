# --- Build Stage (Node.js) ---
FROM node:18-slim AS builder

WORKDIR /app

# Install Node.js dependencies
COPY package*.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# We only need the templates and static input to build the CSS
COPY app/templates ./app/templates
COPY app/static ./app/static

RUN npm install && npm run build:css

# --- Final Stage (Python) ---
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app

# Copy built CSS from builder stage
COPY --from=builder /app/app/static/css/main.css ./app/static/css/main.css

# Ensure necessary directories exist
RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/flask_session /app/tmp

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app/wsgi.py
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Health Check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "100", "--preload", "app.wsgi:application"]
