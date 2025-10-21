#!/bin/bash
# Local Development Server for Article Summarizer Backend
# Usage: ./run_local.sh

set -e

echo "🚀 Starting Article Summarizer Backend (Local Development)"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Error: .env.local not found!"
    echo "   Copy .env.local.example and fill in your credentials"
    exit 1
fi

echo "✅ Environment configured"
echo ""
echo "📡 Starting FastAPI server on http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health"
echo ""
echo "💡 Tip: Update frontend to use http://localhost:8000 instead of Railway URL"
echo ""

# Run uvicorn with reload for development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
