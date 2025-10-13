#!/bin/bash

# Quick Process Script - Simplified wrapper for common post management tasks
# Makes it easy to check and process posts without remembering complex commands

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POST_MANAGER="$SCRIPT_DIR/post_manager.py"

echo "📋 Quick Post Processor"
echo "======================"

# Check if post manager exists
if [ ! -f "$POST_MANAGER" ]; then
    echo "❌ Error: Post manager not found at $POST_MANAGER"
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  check, c        - Show recent discovered posts"
    echo "  stats, s        - Show post statistics"
    echo "  process [n]     - Process first n discovered posts (default: 3)"
    echo "  stratechery     - Show only Stratechery posts"
    echo "  lenny          - Show only Lenny's Newsletter posts"
    echo "  claude         - Show only Creator Economy (Claude-related) posts"
    echo "  urls [source]   - Show URLs only for external processing"
    echo "  bulk [n]        - Bulk process n posts (default: 5)"
    echo ""
    echo "Examples:"
    echo "  $0 check           # Show recent posts"
    echo "  $0 process 2       # Process first 2 discovered posts"
    echo "  $0 stratechery     # Show Stratechery posts only"
    echo "  $0 urls lenny      # Get Lenny's Newsletter URLs for processing"
    echo "  $0 bulk 10         # Bulk process 10 posts"
}

# Parse command
COMMAND=${1:-check}
shift || true

case "$COMMAND" in
    "check"|"c")
        echo "🔍 Recent discovered posts:"
        python3 "$POST_MANAGER" list --status=discovered --limit=10
        ;;

    "stats"|"s")
        python3 "$POST_MANAGER" stats
        ;;

    "process")
        NUM=${1:-3}
        echo "🚀 Processing first $NUM discovered posts..."
        POST_IDS=$(python3 "$POST_MANAGER" list --status=discovered --format=json --limit="$NUM" | jq -r '.[].post_id' | tr '\n' ' ')
        if [ -n "$POST_IDS" ]; then
            python3 "$POST_MANAGER" process $POST_IDS
        else
            echo "✨ No discovered posts to process"
        fi
        ;;

    "stratechery")
        echo "📰 Stratechery posts:"
        python3 "$POST_MANAGER" list --source=stratechery --limit=10
        ;;

    "lenny")
        echo "📰 Lenny's Newsletter posts:"
        python3 "$POST_MANAGER" list --source=lennysnewsletter --limit=10
        ;;

    "claude")
        echo "📰 Creator Economy (Claude-related) posts:"
        python3 "$POST_MANAGER" list --source=creatoreconomy --limit=10
        ;;

    "urls")
        SOURCE=${1:-""}
        if [ -n "$SOURCE" ]; then
            echo "🔗 URLs from $SOURCE:"
            python3 "$POST_MANAGER" list --source="$SOURCE" --format=urls --limit=20
        else
            echo "🔗 All discovered URLs:"
            python3 "$POST_MANAGER" list --status=discovered --format=urls --limit=20
        fi
        ;;

    "bulk")
        NUM=${1:-5}
        echo "🔄 Bulk processing $NUM discovered posts..."
        python3 "$POST_MANAGER" bulk --status=discovered --action=process --limit="$NUM"
        ;;

    "help"|"-h"|"--help")
        show_usage
        ;;

    *)
        echo "❌ Unknown command: $COMMAND"
        echo ""
        show_usage
        exit 1
        ;;
esac