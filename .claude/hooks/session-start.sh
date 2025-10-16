#!/bin/bash
# Automatically create a new branch for this Claude Code session
# Run this at the start of each session: source .claude/hooks/session-start.sh
# Optional: Pass a description: source .claude/hooks/session-start.sh "fixing-env-vars"

# Get optional task description from first argument
TASK_DESC=${1:-"work"}

# Generate unique branch name with timestamp
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
SESSION_ID=$(echo $RANDOM | md5sum | head -c 6 2>/dev/null || echo $RANDOM)
BRANCH_NAME="agent/${TASK_DESC}-${TIMESTAMP}-${SESSION_ID}"

echo "🌿 Creating new session branch: $BRANCH_NAME"
git checkout -b "$BRANCH_NAME"

echo "✅ Branch created! This session will commit to: $BRANCH_NAME"
echo ""
echo "💡 When done, merge with:"
echo "   git checkout main && git merge $BRANCH_NAME && git branch -d $BRANCH_NAME"
echo "   Or simply run: source .claude/hooks/session-end.sh"
echo ""

# Store branch name for session cleanup
echo "$BRANCH_NAME" > .git/CURRENT_SESSION_BRANCH
