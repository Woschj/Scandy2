# Stage 1: Build CSS using Tailwind
FROM node:20-slim AS css-builder
WORKDIR /app
COPY package*.json ./
COPY tailwind.config.js ./
COPY postcss.config.js ./
# We need the app directory for Tailwind to scan for classes
COPY app ./app
RUN npm install && npm run build:css

# Stage 2: Final Python Runtime
FROM python:3.11-slim
WORKDIR /app

# Create a non-root user
RUN groupadd -r scandy && useradd -r -g scandy scandy

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built CSS from the builder stage
COPY --from=css-builder /app/app/static/css/main.css /app/app/static/css/main.css

# Ensure necessary directories exist for persistence and set permissions
RUN mkdir -p /app/app/uploads /app/app/backups /app/app/logs /app/app/flask_session /app/tmp && \
    chown -R scandy:scandy /app

# Switch to non-root user
USER scandy

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app/wsgi.py

# Expose the application port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "100", "app.wsgi:application"]
