-- ============================================
-- Content Sources Schema Cleanup
-- ============================================
-- This migration cleans up the content_sources table schema:
-- 1. Removes deprecated source_type column (system auto-detects at runtime)
-- 2. Removes deprecated description column (replaced by notes)
-- 3. Updates unique constraint from global url to user-scoped (user_id, url)
--
-- WHAT THIS DOES:
-- - Drops source_type column (no longer needed - RSS vs blog detected at runtime)
-- - Drops description column (renamed to notes in earlier refactoring)
-- - Changes unique constraint to allow multiple users to subscribe to same feed
-- - Prevents individual users from adding duplicate URLs
--
-- ============================================

-- ============================================
-- STEP 1: Drop deprecated columns
-- ============================================

-- Drop source_type column (no longer used - system auto-detects at runtime)
ALTER TABLE content_sources DROP COLUMN IF EXISTS source_type;

-- Drop description column (replaced by notes)
ALTER TABLE content_sources DROP COLUMN IF EXISTS description;

-- ============================================
-- STEP 2: Update unique constraint
-- ============================================

-- Drop the global unique constraint on url
-- (This was preventing multiple users from subscribing to the same feed)
ALTER TABLE content_sources DROP CONSTRAINT IF EXISTS content_sources_url_key;

-- Add a unique constraint on (user_id, url) combination
-- This allows different users to subscribe to the same feed
-- But prevents the same user from adding the same URL twice
ALTER TABLE content_sources
ADD CONSTRAINT content_sources_user_url_unique
UNIQUE (user_id, url);

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Verify final schema
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'content_sources'
ORDER BY ordinal_position;

-- Verify constraints
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'content_sources'::regclass
ORDER BY conname;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
  RAISE NOTICE '✅ Content sources schema cleanup completed successfully!';
  RAISE NOTICE '';
  RAISE NOTICE 'Changes made:';
  RAISE NOTICE '1. Removed source_type column (auto-detected at runtime)';
  RAISE NOTICE '2. Removed description column (replaced by notes)';
  RAISE NOTICE '3. Updated unique constraint to (user_id, url)';
  RAISE NOTICE '';
  RAISE NOTICE 'Final schema:';
  RAISE NOTICE '- id, title, url, notes, is_active, user_id, created_at, updated_at';
  RAISE NOTICE '';
  RAISE NOTICE 'Users can now:';
  RAISE NOTICE '- Subscribe to the same RSS feed (multiple users)';
  RAISE NOTICE '- Cannot add duplicate URLs to their own sources';
END $$;
