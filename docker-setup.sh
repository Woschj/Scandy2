#!/usr/bin/env bash
set -e

# Scandy Docker Setup Script
echo "🚀 Scandy Docker Setup"

# 1. Check dependencies
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Error: Docker is not installed."
    exit 1
fi

# 2. Create .env if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from env.example..."
    cp env.example .env

    # Generate random secrets
    SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || echo "scandy_$(date +%s)_secret")
    MONGO_PASS=$(openssl rand -hex 12 2>/dev/null || echo "scandy_$(date +%s)_pass")

    # Replace placeholders in .env
    # Using a different separator for sed to avoid issues with base64 chars
    sed -i "s|CHANGE_ME_SECRET_64CHARS|$SECRET_KEY|g" .env
    sed -i "s|CHANGE_ME_STRONG_PASSWORD|$MONGO_PASS|g" .env
    sed -i "s|CHANGE_ME_ADMIN_UI_PASS|admin|g" .env

    echo "✅ .env created with generated secrets."
else
    echo "ℹ️  .env already exists, skipping creation."
fi

# 3. Pull and start containers
echo "📦 Starting Scandy services..."
docker compose up -d --build

echo ""
echo "✅ Scandy is starting up!"
echo "🌐 Web Interface: http://localhost:5000"
echo "📊 Mongo Express: http://localhost:8081"
echo ""
echo "Run 'docker compose logs -f' to see the logs."
