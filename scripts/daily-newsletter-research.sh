#!/bin/bash

# Daily Newsletter Research Automation Script
# This script runs the newsletter research workflow automatically

# Set working directory
cd "/Users/gauravkotak/cursor-projects-1/automate_life"

# Log file for tracking runs
LOG_FILE="/Users/gauravkotak/cursor-projects-1/automate_life/logs/newsletter-research.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting daily newsletter research workflow"

# Run the newsletter research command
# Note: This assumes Claude Code CLI is available in PATH
if command -v claude &> /dev/null; then
    log "Running newsletter research via Claude Code CLI"
    claude /newsletter-research >> "$LOG_FILE" 2>&1
    log "Newsletter research completed"
else
    log "ERROR: Claude Code CLI not found in PATH"
    exit 1
fi

log "Daily newsletter research workflow finished"