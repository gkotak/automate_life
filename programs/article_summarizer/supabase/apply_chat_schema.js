#!/usr/bin/env node

/**
 * Script to apply chat schema to Supabase database
 * Reads the SQL file and executes it via Supabase client
 */

const fs = require('fs');
const path = require('path');

// Load environment variables
require('dotenv').config({ path: path.join(__dirname, '../../../.env.local') });

const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error('Error: SUPABASE_URL and SUPABASE_KEY must be set in .env.local');
  console.error('\nPlease run the SQL manually:');
  console.error('1. Go to https://supabase.com/dashboard');
  console.error('2. Navigate to SQL Editor');
  console.error('3. Copy and paste the contents of chat_schema.sql');
  console.error('4. Click "Run"');
  process.exit(1);
}

console.log('🔄 Applying chat schema to Supabase...');
console.log(`📍 URL: ${SUPABASE_URL}\n`);

// Read the SQL file
const sqlFile = path.join(__dirname, 'chat_schema.sql');
const sql = fs.readFileSync(sqlFile, 'utf8');

// Create Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// Execute the SQL
// Note: Supabase client doesn't support direct SQL execution via JS
// This script will output instructions instead

console.log('⚠️  The Supabase JavaScript client does not support direct SQL execution.');
console.log('\nPlease apply the schema manually using one of these methods:\n');
console.log('Method 1: Supabase Dashboard (Recommended)');
console.log('  1. Go to: https://supabase.com/dashboard/project/' + SUPABASE_URL.split('//')[1].split('.')[0]);
console.log('  2. Click "SQL Editor" in the left sidebar');
console.log('  3. Click "New query"');
console.log('  4. Copy and paste the contents of: programs/article_summarizer/supabase/chat_schema.sql');
console.log('  5. Click "Run" (or press Cmd/Ctrl + Enter)');
console.log('\nMethod 2: psql Command Line');
console.log('  psql $DATABASE_URL < programs/article_summarizer/supabase/chat_schema.sql');
console.log('\nThe schema will create:');
console.log('  ✅ conversations table');
console.log('  ✅ messages table');
console.log('  ✅ Indexes for performance');
console.log('  ✅ Auto-update trigger for conversation timestamps');
console.log('\nAfter applying, press Enter to continue...');

// Wait for user confirmation
process.stdin.once('data', () => {
  console.log('\n✅ Great! Assuming schema has been applied.');
  console.log('🚀 Ready to proceed with API implementation.\n');
  process.exit(0);
});
