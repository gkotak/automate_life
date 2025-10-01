#!/bin/bash

# View New Posts Extraction Logs
# Shows the latest log file for monitoring new post detection

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$SCRIPT_DIR/logs"

echo "📊 New Posts Extraction Log Viewer"
echo "=================================="

# Find the latest extraction log
LATEST_LOG=$(ls -t "$LOGS_DIR"/new_posts_extraction_*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ No extraction logs found in $LOGS_DIR"
    echo "💡 Run the daily post checker first: ./programs/daily_check.sh"
    exit 1
fi

echo "📁 Latest log file: $(basename "$LATEST_LOG")"
echo "📅 Last modified: $(stat -f "%Sm" "$LATEST_LOG")"
echo "📏 File size: $(du -h "$LATEST_LOG" | cut -f1)"
echo ""

# Show options
echo "Choose view option:"
echo "1. Show full log"
echo "2. Show last 50 lines"
echo "3. Show session summary only"
echo "4. Follow log (tail -f)"
echo "5. Search for specific text"
echo ""
read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo "📖 Full log contents:"
        echo "==================="
        cat "$LATEST_LOG"
        ;;
    2)
        echo "📖 Last 50 lines:"
        echo "================="
        tail -50 "$LATEST_LOG"
        ;;
    3)
        echo "📊 Session summary:"
        echo "=================="
        grep -E "(SESSION STARTED|FINAL SESSION SUMMARY|New posts|Successfully processed|Total tracked)" "$LATEST_LOG"
        ;;
    4)
        echo "📡 Following log (Ctrl+C to stop):"
        echo "================================="
        tail -f "$LATEST_LOG"
        ;;
    5)
        read -p "Enter search term: " search_term
        echo "🔍 Searching for '$search_term':"
        echo "==============================="
        grep -i "$search_term" "$LATEST_LOG" --color=always
        ;;
    *)
        echo "❌ Invalid choice. Showing last 20 lines instead:"
        tail -20 "$LATEST_LOG"
        ;;
esac

echo ""
echo "💡 Log file location: $LATEST_LOG"