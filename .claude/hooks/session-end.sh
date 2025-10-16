#!/bin/bash
# Merge session branch back to main and clean up
# Run this at the end of each session: source .claude/hooks/session-end.sh

# Read the current session branch
if [ ! -f ".git/CURRENT_SESSION_BRANCH" ]; then
  echo "❌ No active session branch found"
  echo "   (Are you sure you ran session-start.sh?)"
  exit 1
fi

BRANCH_NAME=$(cat .git/CURRENT_SESSION_BRANCH)

echo "📝 Current session branch: $BRANCH_NAME"
echo ""

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
  echo "⚠️  WARNING: You have uncommitted changes!"
  echo "   Please commit or stash them first."
  git status --short
  exit 1
fi

# Ask user if they want to merge
read -p "🔀 Merge $BRANCH_NAME into main? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "❌ Merge cancelled. Branch kept: $BRANCH_NAME"
  echo "   To merge later: git checkout main && git merge $BRANCH_NAME"
  exit 0
fi

# Merge into main
echo "🔀 Merging $BRANCH_NAME into main..."
git checkout main
git merge --no-ff "$BRANCH_NAME" -m "Merge session: $BRANCH_NAME"

# Ask if they want to push
read -p "📤 Push to remote? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  git push
  echo "✅ Pushed to remote"
fi

# Delete the session branch
echo "🗑️  Deleting session branch: $BRANCH_NAME"
git branch -d "$BRANCH_NAME"

# Clean up tracking file
rm .git/CURRENT_SESSION_BRANCH

echo ""
echo "✅ Session complete! Back on main branch."
