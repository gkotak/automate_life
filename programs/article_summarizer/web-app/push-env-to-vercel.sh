#!/bin/bash
# Push environment variables from .env.local to Vercel

echo "📤 Pushing environment variables to Vercel..."

while IFS='=' read -r key value; do
  # Skip empty lines and comments
  [[ -z "$key" || "$key" =~ ^# ]] && continue
  
  echo "Adding $key..."
  echo "$value" | vercel env add "$key" production --force
done < .env.local

echo "✅ Done! All environment variables pushed to Vercel."
