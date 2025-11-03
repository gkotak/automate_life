-- ============================================
-- Multi-User Support Migration
-- ============================================
-- This script adds user_id to content_queue and content_sources tables
-- and updates RLS policies for user-scoped access
--
-- INSTRUCTIONS:
-- 1. Open Supabase Dashboard → SQL Editor
-- 2. Copy and paste this entire script
-- 3. Click "Run" to execute
--
-- WHAT THIS DOES:
-- - Adds user_id column to content_queue table
-- - Adds user_id column to content_sources table
-- - Updates RLS policies for user-scoped access
-- - Updates articles RLS to allow public read (for "All Articles" view)
-- - Creates indexes for performance
-- - Migrates existing data to your user account
--
-- ============================================

-- ============================================
-- STEP 1: GET YOUR USER ID
-- ============================================
-- First, find your user ID - we'll need this for data migration
-- Run this query separately to get your user_id, then replace 'YOUR-USER-ID-HERE' below

-- SELECT id, email FROM auth.users WHERE email = 'your-email@example.com';

-- ============================================
-- STEP 2: ADD user_id TO content_queue
-- ============================================

-- Add user_id column (nullable initially to allow existing data)
ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Create index for query performance
CREATE INDEX IF NOT EXISTS content_queue_user_id_idx ON content_queue(user_id);

-- Add helpful comment
COMMENT ON COLUMN content_queue.user_id IS 'Owner of the content queue item - references auth.users';

-- ============================================
-- STEP 3: ADD user_id TO content_sources
-- ============================================

-- Add user_id column (nullable initially)
ALTER TABLE content_sources
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Create index for query performance
CREATE INDEX IF NOT EXISTS content_sources_user_id_idx ON content_sources(user_id);

-- Add helpful comment
COMMENT ON COLUMN content_sources.user_id IS 'Owner of the content source (RSS feed/newsletter) - references auth.users';

-- ============================================
-- STEP 4: MIGRATE EXISTING DATA
-- ============================================
-- ⚠️ IMPORTANT: Replace 'YOUR-USER-ID-HERE' with your actual user UUID
-- Get it from: SELECT id FROM auth.users WHERE email = 'your-email@example.com';

-- Update content_queue records
UPDATE content_queue
SET user_id = 'd0ebb760-52e5-4478-8c1b-8ccfedf721d0'
WHERE user_id IS NULL;

-- Update content_sources records
UPDATE content_sources
SET user_id = 'd0ebb760-52e5-4478-8c1b-8ccfedf721d0'
WHERE user_id IS NULL;

-- ============================================
-- STEP 5: UPDATE RLS POLICIES - content_queue
-- ============================================

-- Drop old permissive policies
DROP POLICY IF EXISTS "Allow public read access to content_queue" ON content_queue;
DROP POLICY IF EXISTS "Allow authenticated insert to content_queue" ON content_queue;
DROP POLICY IF EXISTS "Allow authenticated update to content_queue" ON content_queue;
DROP POLICY IF EXISTS "Allow authenticated delete from content_queue" ON content_queue;

-- Create new user-scoped policies

-- SELECT: Users can only view their own queue items
CREATE POLICY "Users can view own content_queue" ON content_queue
  FOR SELECT
  USING (auth.uid() = user_id);

-- INSERT: Users can only insert items for themselves
CREATE POLICY "Users can insert own content_queue" ON content_queue
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- UPDATE: Users can only update their own items
CREATE POLICY "Users can update own content_queue" ON content_queue
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- DELETE: Users can only delete their own items
CREATE POLICY "Users can delete own content_queue" ON content_queue
  FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- STEP 6: UPDATE RLS POLICIES - content_sources
-- ============================================

-- Drop old permissive policies
DROP POLICY IF EXISTS "Allow public read access to content_sources" ON content_sources;
DROP POLICY IF EXISTS "Allow authenticated insert to content_sources" ON content_sources;
DROP POLICY IF EXISTS "Allow authenticated update to content_sources" ON content_sources;
DROP POLICY IF EXISTS "Allow authenticated delete from content_sources" ON content_sources;

-- Create new user-scoped policies

-- SELECT: Users can only view their own sources
CREATE POLICY "Users can view own content_sources" ON content_sources
  FOR SELECT
  USING (auth.uid() = user_id);

-- INSERT: Users can only insert sources for themselves
CREATE POLICY "Users can insert own content_sources" ON content_sources
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- UPDATE: Users can only update their own sources
CREATE POLICY "Users can update own content_sources" ON content_sources
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- DELETE: Users can only delete their own sources
CREATE POLICY "Users can delete own content_sources" ON content_sources
  FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- STEP 7: UPDATE RLS POLICIES - articles
-- ============================================
-- Add public read policy for "All Articles" view
-- Keep existing user-scoped write policies

-- Drop the old restrictive SELECT policy (from migration 010)
DROP POLICY IF EXISTS "Users can view own articles" ON articles;

-- Create new public read policy for authenticated users
CREATE POLICY "Authenticated users can view all articles" ON articles
  FOR SELECT
  TO authenticated
  USING (true);

-- Keep existing write policies (already user-scoped from migration 010):
-- - "Users can insert own articles"
-- - "Users can update own articles"
-- - "Users can delete own articles"

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check that user_id columns were added
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_name IN ('content_queue', 'content_sources')
  AND column_name = 'user_id';

-- Check RLS policies on content_queue
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename = 'content_queue'
ORDER BY policyname;

-- Check RLS policies on content_sources
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename = 'content_sources'
ORDER BY policyname;

-- Check articles policies
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename = 'articles'
ORDER BY policyname;

-- Count records by user
SELECT
  'content_queue' as table_name,
  COALESCE(user_id::text, 'NULL') as user_id,
  COUNT(*) as record_count
FROM content_queue
GROUP BY user_id
UNION ALL
SELECT
  'content_sources' as table_name,
  COALESCE(user_id::text, 'NULL') as user_id,
  COUNT(*) as record_count
FROM content_sources
GROUP BY user_id
ORDER BY table_name, record_count DESC;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
  RAISE NOTICE '✅ Multi-user support migration completed successfully!';
  RAISE NOTICE '';
  RAISE NOTICE 'Changes made:';
  RAISE NOTICE '1. Added user_id to content_queue and content_sources';
  RAISE NOTICE '2. Updated RLS policies for user-scoped access';
  RAISE NOTICE '3. Articles now have public read access (all authenticated users)';
  RAISE NOTICE '4. Created indexes for performance';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Update backend services to use JWT authentication';
  RAISE NOTICE '2. Update frontend to send auth tokens to backends';
  RAISE NOTICE '3. Create content sources management UI';
  RAISE NOTICE '4. Add article filtering (My Articles vs All Articles)';
END $$;
