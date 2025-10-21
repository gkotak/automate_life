#!/bin/bash

# Script to apply chat schema to Supabase database
# Run this script to create the conversations and messages tables

set -e

# Load environment variables
if [ -f "../../../.env.local" ]; then
  export $(grep -v '^#' ../../../.env.local | xargs)
elif [ -f "../../.env.local" ]; then
  export $(grep -v '^#' ../../.env.local | xargs)
fi

# Check for required environment variables
if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SECRET_KEY" ]; then
  echo "Error: SUPABASE_URL and SUPABASE_SECRET_KEY must be set"
  echo "Using SUPABASE_URL: $SUPABASE_URL"
  echo ""
  echo "Please set SUPABASE_SECRET_KEY in .env.local or run the SQL manually in Supabase SQL Editor"
  echo ""
  echo "To run manually:"
  echo "1. Go to https://supabase.com/dashboard/project/YOUR_PROJECT/sql"
  echo "2. Copy and paste the contents of chat_schema.sql"
  echo "3. Click 'Run'"
  exit 1
fi

echo "Applying chat schema to Supabase..."
echo "URL: $SUPABASE_URL"

# Apply the schema using Supabase REST API
curl -X POST "${SUPABASE_URL}/rest/v1/rpc/exec_sql" \
  -H "apikey: ${SUPABASE_SECRET_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SECRET_KEY}" \
  -H "Content-Type: application/json" \
  -d @chat_schema.sql

echo ""
echo "Schema applied successfully!"
echo ""
echo "Created tables:"
echo "  - conversations"
echo "  - messages"
echo ""
echo "Created indexes:"
echo "  - idx_conversations_updated_at"
echo "  - idx_messages_conversation_id"
echo "  - idx_messages_created_at"
echo "  - idx_messages_conversation_created"
echo ""
echo "Created trigger:"
echo "  - trigger_update_conversation_timestamp"
