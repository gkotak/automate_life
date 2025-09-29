#!/bin/bash

# Daily Newsletter Research Automation Script
# This script runs the newsletter research workflow automatically

# Set working directory
cd "/Users/gauravkotak/cursor-projects-1/automate_life"

# Ensure PATH includes common locations for Claude CLI
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

# Log file for tracking runs
LOG_FILE="/Users/gauravkotak/cursor-projects-1/automate_life/logs/newsletter-research.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting daily newsletter research workflow"

# Run the newsletter research command
# Check for Claude CLI in multiple locations
CLAUDE_CMD=""
if command -v claude &> /dev/null; then
    CLAUDE_CMD="claude"
elif [ -f "/usr/local/bin/claude" ]; then
    CLAUDE_CMD="/usr/local/bin/claude"
elif [ -f "/opt/homebrew/bin/claude" ]; then
    CLAUDE_CMD="/opt/homebrew/bin/claude"
else
    log "ERROR: Claude Code CLI not found in PATH or standard locations"
    log "Searched locations: PATH, /usr/local/bin/claude, /opt/homebrew/bin/claude"
    exit 1
fi

log "Found Claude CLI at: $CLAUDE_CMD"
log "Running newsletter research via Claude Code CLI"
"$CLAUDE_CMD" /newsletter-research >> "$LOG_FILE" 2>&1
if [ $? -eq 0 ]; then
    log "Newsletter research completed successfully"
else
    log "ERROR: Newsletter research failed with exit code $?"
fi

log "Daily newsletter research workflow finished"