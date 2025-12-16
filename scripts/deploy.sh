#!/bin/bash

# Avionyx Deployment Script

echo "🐔 Starting Avionyx Deployment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    if [ -f .env.example ]; then
        echo "📝 Creating .env from .env.example..."
        cp .env.example .env
        echo "✅ Created .env"
    else
        echo "❌ Error: .env.example also missing. Cannot proceed."
        exit 1
    fi
fi

# Check if TELEGRAM_TOKEN is set or is default
if grep -q "your_telegram_bot_token_here" .env || ! grep -q "TELEGRAM_TOKEN=" .env; then
    echo "⚠️  TELEGRAM_TOKEN is not configured."
    echo "📖 Help: See docs/setup_credentials.md for how to get a token."
    read -p "🔑 Enter your Telegram Bot Token: " token
    if [ -n "$token" ]; then
        # If the line exists, replace it; otherwise append it
        if grep -q "TELEGRAM_TOKEN=" .env; then
            sed -i "s/TELEGRAM_TOKEN=.*/TELEGRAM_TOKEN=$token/" .env
        else
            echo "TELEGRAM_TOKEN=$token" >> .env
        fi
        echo "✅ Token updated."
    else
        echo "❌ Token not provided. Please edit .env manually."
        exit 1
    fi
fi

# Check for Admin IDs
if grep -q "123456789,987654321" .env || ! grep -q "ADMIN_IDS=" .env; then
    echo "⚠️  Admin IDs are not configured correctly."
    echo "📖 Help: See docs/setup_credentials.md to find your ID from @userinfobot."
    read -p "👤 Enter Admin ID(s) (comma separated): " admin_id
    if [ -n "$admin_id" ]; then
        if grep -q "ADMIN_IDS=" .env; then
            sed -i "s/ADMIN_IDS=.*/ADMIN_IDS=$admin_id/" .env
        else
            echo "ADMIN_IDS=$admin_id" >> .env
        fi
        echo "✅ Admin ID updated."
    else 
        echo "⚠️  Proceeding without updating Admin IDs. You might not have access."
    fi
fi

# Ensure data directory exists
mkdir -p data

echo "🚀 Building and Starting Docker Containers..."
docker-compose up -d --build

if [ $? -eq 0 ]; then
    echo "✅ Deployment Successful!"
    echo "📜 Showing logs (Ctrl+C to exit logs)..."
    sleep 2
    docker-compose logs -f
else
    echo "❌ Deployment Failed. Check docker output above."
fi
