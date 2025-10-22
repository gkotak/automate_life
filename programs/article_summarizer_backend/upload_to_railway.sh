#!/bin/bash
# Upload storage_state.json to Railway
# Run this script from your terminal

echo "📦 Uploading storage_state.json to Railway..."

# Check if Railway CLI is logged in
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway"
    echo "   Run: railway login"
    exit 1
fi

# Link to project if not already linked
if [ ! -f ".railway" ]; then
    echo "🔗 Linking to Railway project..."
    railway link
fi

# Upload the file
echo "⬆️  Uploading file..."
railway run "mkdir -p /app/storage && cat > /app/storage/storage_state.json" < programs/article_summarizer_backend/storage/storage_state.json

echo "✅ Done! File uploaded to Railway"
echo "🔄 Restart your Railway service to pick up the new file"
