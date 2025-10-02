#!/bin/bash

# File Transcription Script - Shell wrapper
# Transcribes audio/video files using OpenAI Whisper API

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/transcribe_file.py"

echo "🎵 File Transcription Tool - $(date)"
echo "==============================================="

# Check if file argument provided
if [ $# -eq 0 ]; then
    echo "❌ Error: No file provided"
    echo ""
    echo "Usage: $0 <audio_or_video_file> [language]"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/audio.mp3"
    echo "  $0 /path/to/video.mp4 en"
    echo "  $0 recording.wav es"
    echo ""
    echo "Supported formats: mp3, mp4, wav, m4a, flac, webm, ogg, and more"
    echo "Language codes: en, es, fr, de, it, pt, ru, ja, ko, zh, etc."
    exit 1
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Check if file exists
if [ ! -f "$1" ]; then
    echo "❌ Error: File not found: $1"
    exit 1
fi

# Check dependencies
echo "🔍 Checking dependencies..."
if ! python3 -c "import openai" &>/dev/null; then
    echo "📦 Installing OpenAI package..."
    pip3 install openai
fi

# Check for OpenAI API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️ Warning: OPENAI_API_KEY not set in environment"
    echo "   Make sure you have it in your .env file or set it as an environment variable"
fi

# Run the transcription
echo "🚀 Starting transcription..."
python3 "$PYTHON_SCRIPT" "$@"

echo ""
echo "✅ Transcription complete - $(date)"