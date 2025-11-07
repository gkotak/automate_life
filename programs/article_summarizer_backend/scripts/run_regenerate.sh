#!/bin/bash
# Wrapper script to run regenerate_summary.py with environment variables

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Try to source .env.local file
if [ -f "$BACKEND_DIR/.env.local" ]; then
    echo "Loading environment from .env.local..."
    set -a
    source "$BACKEND_DIR/.env.local"
    set +a
elif [ -f "$BACKEND_DIR/.env" ]; then
    echo "Loading environment from .env..."
    set -a
    source "$BACKEND_DIR/.env"
    set +a
else
    echo "Error: No .env file found!"
    exit 1
fi

# Check if article ID was provided
if [ -z "$1" ]; then
    echo "Usage: ./scripts/run_regenerate.sh <article_id>"
    echo "Example: ./scripts/run_regenerate.sh 269"
    exit 1
fi

# Run the Python script
cd "$BACKEND_DIR"
python3 scripts/regenerate_summary.py "$1"
