#!/bin/bash

# Hybrid Article Summarizer Shell Wrapper
# This script provides a simple interface to the Python-based article summarizer

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/video_article_summarizer.py"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Check if URL provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <article_url>"
    echo ""
    echo "Example:"
    echo "  $0 https://example.com/article"
    echo ""
    echo "This hybrid approach combines:"
    echo "  • Python for deterministic file operations"
    echo "  • Claude Code API for AI-powered content analysis"
    exit 1
fi

URL="$1"

# Validate URL format
if [[ ! "$URL" =~ ^https?:// ]]; then
    echo "❌ Error: Please provide a valid HTTP/HTTPS URL"
    echo "Got: $URL"
    exit 1
fi

echo "🚀 Starting hybrid article summarizer..."
echo "📰 URL: $URL"
echo ""

# Check Python dependencies
echo "🔍 Checking Python dependencies..."
if ! python3 -c "import requests, bs4" &>/dev/null; then
    echo "📦 Installing required Python packages..."
    pip3 install -r "$REQUIREMENTS" || {
        echo "❌ Failed to install dependencies. Try:"
        echo "   pip3 install requests beautifulsoup4 lxml"
        exit 1
    }
fi

# Check Claude CLI
echo "🔍 Checking Claude Code CLI..."
if ! command -v claude &>/dev/null; then
    if [ ! -f "/usr/local/bin/claude" ] && [ ! -f "/opt/homebrew/bin/claude" ]; then
        echo "❌ Claude Code CLI not found. Please install Claude Code."
        exit 1
    fi
fi

echo "✅ All dependencies verified"
echo ""

# Run the Python script
echo "🐍 Running Python analysis..."
python3 "$PYTHON_SCRIPT" "$URL"

echo ""
echo "🎉 Article summarization complete!"
echo "📁 Check HTML/article_summaries/ for the generated summary"