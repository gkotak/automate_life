-- Migration: Add organization_id to Existing Tables
-- Description: Add organization_id foreign keys for multi-tenancy
-- Run this AFTER 002_backfill_existing_users.sql

-- ============================================================================
-- STEP 1: Add organization_id to article_users (defense in depth)
-- ============================================================================

-- Add column (nullable for migration)
ALTER TABLE article_users
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_article_users_organization_id ON article_users(organization_id);

-- Backfill organization_id from user's profile
UPDATE article_users
SET organization_id = (
  SELECT organization_id FROM users WHERE id = article_users.user_id
)
WHERE organization_id IS NULL;

-- Make it NOT NULL after backfill
ALTER TABLE article_users
ALTER COLUMN organization_id SET NOT NULL;

-- Add constraint to ensure user's org matches
CREATE UNIQUE INDEX IF NOT EXISTS idx_article_users_org_user_article
ON article_users(user_id, article_id, organization_id);

-- ============================================================================
-- STEP 2: Add organization_id to content_sources (team-wide subscriptions)
-- ============================================================================

-- Add column (nullable for migration)
ALTER TABLE content_sources
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_content_sources_organization_id ON content_sources(organization_id);

-- Backfill organization_id from user's profile
UPDATE content_sources
SET organization_id = (
  SELECT organization_id FROM users WHERE id = content_sources.user_id
)
WHERE organization_id IS NULL;

-- Make it NOT NULL after backfill
ALTER TABLE content_sources
ALTER COLUMN organization_id SET NOT NULL;

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
ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_content_queue_organization_id ON content_queue(organization_id);

-- Backfill organization_id from user's profile
UPDATE content_queue
SET organization_id = (
  SELECT organization_id FROM users WHERE id = content_queue.user_id
)
WHERE organization_id IS NULL;

-- Make it NOT NULL after backfill
ALTER TABLE content_queue
ALTER COLUMN organization_id SET NOT NULL;

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
-- - Next, run 004_update_rls_policies.sql to update security policies
-- ============================================================================
