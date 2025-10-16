#!/bin/bash
# Automatically create a new branch for this Claude Code session
# Run this at the start of each session: source .claude/hooks/session-start.sh

# Generate unique branch name with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SESSION_ID=$(echo $RANDOM | md5sum | head -c 6)
BRANCH_NAME="agent/session-${TIMESTAMP}-${SESSION_ID}"

echo "🌿 Creating new session branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"

echo "✅ Branch created! This session will commit to: $BRANCH_NAME"
echo ""
echo "💡 When done, merge with:"
echo "   git checkout main && git merge $BRANCH_NAME && git branch -d $BRANCH_NAME"
echo ""

# Store branch name for session cleanup
echo "$BRANCH_NAME" > .git/CURRENT_SESSION_BRANCH
