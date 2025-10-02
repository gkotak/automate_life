#!/bin/bash

# Manual Post Checker - Using refactored processor
# Manually checks for new posts (no automation)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/processors/post_checker.py"

echo "🔍 Manual Post Checker V2 - $(date)"
echo "==============================================="

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: Python script not found at $PYTHON_SCRIPT"
    echo "Falling back to original script..."
    exec "$SCRIPT_DIR/daily_check.sh" "$@"
fi

# Check dependencies
echo "🔍 Checking dependencies..."
if ! python3 -c "import requests, bs4" &>/dev/null; then
    echo "📦 Installing required Python packages..."
    pip3 install requests beautifulsoup4 lxml
fi

# Run the daily checker
echo "🚀 Running daily post checker (refactored version)..."
SUMMARY=$(python3 "$PYTHON_SCRIPT")

echo ""
if [ -n "$SUMMARY" ]; then
    echo "📊 $SUMMARY"
    echo ""
    echo "💡 To manage and process posts, use the post manager:"
    echo "   python3 scripts/post_manager.py list --status=discovered"
    echo "   python3 scripts/post_manager.py process <post_ids>"
    echo "   python3 scripts/post_manager.py bulk --status=discovered --action=process --limit=5"
else
    echo "✨ No new posts found today"
fi

echo ""
echo "✅ Manual check complete - $(date)"