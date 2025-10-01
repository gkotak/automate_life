#!/bin/bash

# Daily Post Checker - Simple wrapper script
# Checks for new posts and runs video summarizer automatically

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/daily_post_checker.py"

echo "🌅 Daily Post Checker - $(date)"
echo "==============================================="

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Check dependencies
echo "🔍 Checking dependencies..."
if ! python3 -c "import requests, bs4" &>/dev/null; then
    echo "📦 Installing required Python packages..."
    pip3 install requests beautifulsoup4 lxml
fi

# Run the daily checker
echo "🚀 Running daily post checker..."
python3 "$PYTHON_SCRIPT"

echo ""
echo "✅ Daily check complete - $(date)"