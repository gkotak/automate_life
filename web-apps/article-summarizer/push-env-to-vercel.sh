#!/bin/bash
# Push environment variables from .env.local to Vercel

set -e  # Exit on error
set -o pipefail  # Catch errors in pipelines

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
  echo "❌ Error: .env.local file not found!"
  echo "   Make sure you're running this from the web-apps/article-summarizer directory"
  exit 1
fi

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
  echo "❌ Error: Vercel CLI not installed!"
  echo "   Install with: npm install -g vercel"
  echo "   Then login with: vercel login"
  exit 1
fi

echo "📤 Pushing environment variables to Vercel..."
echo ""

count=0
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip empty lines and comments
  [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

  # Skip lines that don't contain '='
  [[ ! "$line" =~ = ]] && continue

  # Extract key and value
  key=$(echo "$line" | cut -d'=' -f1 | xargs)
  value=$(echo "$line" | cut -d'=' -f2-)

  # Skip if key is empty
  [[ -z "$key" ]] && continue

  echo "  🔑 Adding $key..."
  if echo "$value" | vercel env add "$key" production --force > /dev/null 2>&1; then
    ((count++))
  else
    echo "     ❌ Failed to add $key"
    exit 1
  fi
done < .env.local

echo ""
echo "✅ Done! Pushed $count environment variable(s) to Vercel production."
echo ""
echo "💡 To verify, visit: https://vercel.com/dashboard → Your Project → Settings → Environment Variables"
