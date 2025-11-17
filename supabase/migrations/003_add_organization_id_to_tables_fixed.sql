-- Migration: Add organization_id to Existing Tables (FIXED VERSION)
-- Description: Add organization_id foreign keys for multi-tenancy
-- Run this AFTER 002_backfill_existing_users.sql

-- ============================================================================
-- STEP 0: Debug - Check current state
-- ============================================================================

-- Check if users table has data
DO $$
DECLARE
  user_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO user_count FROM users;
  RAISE NOTICE 'Users table has % rows', user_count;

  IF user_count = 0 THEN
    RAISE EXCEPTION 'Users table is empty. Please run 002_backfill_existing_users.sql first';
  END IF;
END $$;

-- ============================================================================
-- STEP 1: Add organization_id to article_users (defense in depth)
-- ============================================================================

-- Add column (nullable for migration)
ALTER TABLE article_users
ADD COLUMN IF NOT EXISTS organization_id UUID;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_article_users_organization_id ON article_users(organization_id);

-- Backfill organization_id from user's profile
UPDATE article_users au
SET organization_id = u.organization_id
FROM users u
WHERE au.user_id = u.id
AND au.organization_id IS NULL;

-- Check for any remaining NULLs
DO $$
DECLARE
  null_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO null_count FROM article_users WHERE organization_id IS NULL;

  IF null_count > 0 THEN
    RAISE WARNING 'Found % article_users rows with NULL organization_id (orphaned data)', null_count;
    -- Delete orphaned rows (users that no longer exist)
    DELETE FROM article_users WHERE organization_id IS NULL;
    RAISE NOTICE 'Deleted % orphaned article_users rows', null_count;
  END IF;
END $$;

-- Now make it NOT NULL
ALTER TABLE article_users
ALTER COLUMN organization_id SET NOT NULL;

-- Add foreign key constraint
ALTER TABLE article_users
ADD CONSTRAINT article_users_organization_id_fkey
FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- Add constraint to ensure user's org matches
CREATE UNIQUE INDEX IF NOT EXISTS idx_article_users_org_user_article
ON article_users(user_id, article_id, organization_id);

-- ============================================================================
-- STEP 2: Add organization_id to content_sources (team-wide subscriptions)
-- ============================================================================

-- Add column (nullable for migration)
ALTER TABLE content_sources
ADD COLUMN IF NOT EXISTS organization_id UUID;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_content_sources_organization_id ON content_sources(organization_id);

-- Backfill organization_id from user's profile
UPDATE content_sources cs
SET organization_id = u.organization_id
FROM users u
WHERE cs.user_id = u.id
AND cs.organization_id IS NULL;

-- Check for any remaining NULLs
DO $$
DECLARE
  null_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO null_count FROM content_sources WHERE organization_id IS NULL;

  IF null_count > 0 THEN
    RAISE WARNING 'Found % content_sources rows with NULL organization_id (orphaned data)', null_count;
    -- Delete orphaned rows (users that no longer exist)
    DELETE FROM content_sources WHERE organization_id IS NULL;
    RAISE NOTICE 'Deleted % orphaned content_sources rows', null_count;
  END IF;
END $$;

-- Now make it NOT NULL
ALTER TABLE content_sources
ALTER COLUMN organization_id SET NOT NULL;

-- Add foreign key constraint
ALTER TABLE content_sources
ADD CONSTRAINT content_sources_organization_id_fkey
FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- Drop old unique constraint on (user_id, url)
ALTER TABLE content_sources
DROP CONSTRAINT IF EXISTS content_sources_user_id_url_key;

-- Add new unique constraint on (organization_id, url) for team-wide sources
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_sources_org_url
ON content_sources(organization_id, url);

-- ============================================================================
-- STEP 3: Add organization_id to content_queue (team-wide discovery)
-- ============================================================================

-- Add column (nullable for migration)
ALTER TABLE content_queue
ADD COLUMN IF NOT EXISTS organization_id UUID;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_content_queue_organization_id ON content_queue(organization_id);

-- Backfill organization_id from user's profile
UPDATE content_queue cq
SET organization_id = u.organization_id
FROM users u
WHERE cq.user_id = u.id
AND cq.organization_id IS NULL;

-- Check for any remaining NULLs
DO $$
DECLARE
  null_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO null_count FROM content_queue WHERE organization_id IS NULL;

  IF null_count > 0 THEN
    RAISE WARNING 'Found % content_queue rows with NULL organization_id (orphaned data)', null_count;
    -- Delete orphaned rows (users that no longer exist)
    DELETE FROM content_queue WHERE organization_id IS NULL;
    RAISE NOTICE 'Deleted % orphaned content_queue rows', null_count;
  END IF;
END $$;

-- Now make it NOT NULL
ALTER TABLE content_queue
ALTER COLUMN organization_id SET NOT NULL;

-- Add foreign key constraint
ALTER TABLE content_queue
ADD CONSTRAINT content_queue_organization_id_fkey
FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- ============================================================================
-- STEP 4: Verify the migration
-- ============================================================================

-- Check that all rows have organization_id set
DO $$
DECLARE
  article_users_null_count INTEGER;
  content_sources_null_count INTEGER;
  content_queue_null_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO article_users_null_count
  FROM article_users WHERE organization_id IS NULL;

  SELECT COUNT(*) INTO content_sources_null_count
  FROM content_sources WHERE organization_id IS NULL;

  SELECT COUNT(*) INTO content_queue_null_count
  FROM content_queue WHERE organization_id IS NULL;

  IF article_users_null_count > 0 OR content_sources_null_count > 0 OR content_queue_null_count > 0 THEN
    RAISE EXCEPTION 'Found NULL organization_id: article_users=%, content_sources=%, content_queue=%',
      article_users_null_count, content_sources_null_count, content_queue_null_count;
  ELSE
    RAISE NOTICE 'All tables successfully migrated with organization_id';
  END IF;
END $$;

-- Display summary
SELECT
  'article_users' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT organization_id) as distinct_orgs
FROM article_users
UNION ALL
SELECT
  'content_sources' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT organization_id) as distinct_orgs
FROM content_sources
UNION ALL
SELECT
  'content_queue' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT organization_id) as distinct_orgs
FROM content_queue;

-- ============================================================================
-- NOTES:
-- - articles table remains global (no organization_id) for efficiency
-- - conversations table remains user-scoped (no organization_id) for now
-- - This script handles orphaned data by deleting rows where user no longer exists
-- - Next, run 004_update_rls_policies.sql to update security policies
-- ============================================================================
