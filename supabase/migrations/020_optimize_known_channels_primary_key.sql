-- =====================================================
-- Migration: Make source_url primary key in known_channels
-- =====================================================
-- Purpose: Simplify lookups since source_url is the only lookup key
--          and no foreign keys reference this table
-- =====================================================

-- Step 1: Check for and handle NULL source_url values
-- Option A: Delete rows with NULL source_url (if they're incomplete/unused)
DELETE FROM known_channels
WHERE source_url IS NULL;

-- OR Option B: If you want to keep them, populate from channel_name or mark inactive
-- UPDATE known_channels
-- SET is_active = FALSE
-- WHERE source_url IS NULL;

-- Step 2: Make source_url NOT NULL
ALTER TABLE known_channels
ALTER COLUMN source_url SET NOT NULL;

-- Step 3: Drop the old unique constraint on channel_name (if it still exists)
ALTER TABLE known_channels
DROP CONSTRAINT IF EXISTS known_channels_channel_name_key;

-- Step 4: Drop the old primary key constraint on id (if it exists)
ALTER TABLE known_channels
DROP CONSTRAINT IF EXISTS known_channels_pkey;

-- Step 5: Drop the old id column (no longer needed as PK)
ALTER TABLE known_channels
DROP COLUMN IF EXISTS id;

-- Step 6: Add source_url as the new primary key
ALTER TABLE known_channels
ADD PRIMARY KEY (source_url);

-- Step 7: Drop the old serial sequence for id column (cleanup)
DROP SEQUENCE IF EXISTS known_channels_id_seq;

-- Step 8: Drop redundant indexes
DROP INDEX IF EXISTS idx_known_channels_source_url;
DROP INDEX IF EXISTS idx_known_channels_source_url_lookup;
DROP INDEX IF EXISTS idx_known_channels_name;

-- Step 9: Keep only the active lookup index (recreated for PK)
CREATE INDEX IF NOT EXISTS idx_known_channels_active
ON known_channels(source_url)
WHERE is_active = TRUE;

-- Step 10: Update table and column comments
COMMENT ON TABLE known_channels IS
  'Maps content source URLs to YouTube channels/playlists. Uses source_url as natural primary key since lookups are always by URL.';

COMMENT ON COLUMN known_channels.source_url IS
  'Content source URL (RSS feed, PocketCasts channel, etc.) - PRIMARY KEY and lookup key';

COMMENT ON COLUMN known_channels.channel_name IS
  'Optional human-readable channel name for display purposes';

-- =====================================================
-- Verification Queries
-- =====================================================

-- Check final schema
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'known_channels'
ORDER BY ordinal_position;

-- Check constraints
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'known_channels'::regclass
ORDER BY conname;

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'known_channels'
ORDER BY indexname;

-- Show sample data
SELECT source_url, channel_name, youtube_url, is_active
FROM known_channels
LIMIT 5;

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================

DO $$
BEGIN
  RAISE NOTICE '✅ known_channels optimization completed!';
  RAISE NOTICE '';
  RAISE NOTICE 'Changes made:';
  RAISE NOTICE '1. Removed rows with NULL source_url';
  RAISE NOTICE '2. source_url is now the PRIMARY KEY';
  RAISE NOTICE '3. Removed id column (no longer needed)';
  RAISE NOTICE '4. Simplified indexes';
  RAISE NOTICE '';
  RAISE NOTICE 'Final schema:';
  RAISE NOTICE '- source_url (PK), youtube_url, channel_name, notes, is_active, created_at, updated_at';
  RAISE NOTICE '';
  RAISE NOTICE 'Lookups are now simpler:';
  RAISE NOTICE '- SELECT youtube_url FROM known_channels WHERE source_url = $1 AND is_active = TRUE';
END $$;
