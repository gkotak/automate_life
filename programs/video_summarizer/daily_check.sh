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
OUTPUT_FILE=$(python3 "$PYTHON_SCRIPT")

echo ""
if [ -n "$OUTPUT_FILE" ]; then
    echo "📄 New URLs found and saved to: $OUTPUT_FILE"
    echo "💡 Review the URLs and manually process the ones you want using:"
    echo "   ./scripts/summarize_article.sh [URL]"
else
    echo "✨ No new posts found today"
fi

echo ""
echo "✅ Daily check complete - $(date)"