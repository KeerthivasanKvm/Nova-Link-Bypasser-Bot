#!/bin/bash

# Ultimate Link Bypass Bot - Start Script
# =========================================

set -e

echo "🚀 Starting Ultimate Link Bypass Bot..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Run the bot
echo "🤖 Starting bot..."
python3 main.py "$@"
