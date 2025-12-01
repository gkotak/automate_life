-- Remove redundant organization_id columns from content tables
-- Security is now enforced at the article level (private_articles table)
-- and through user_id checks in RLS policies

-- ============================================
-- STEP 1: Remove organization_id from article_users
-- ============================================

-- First, drop any policies that reference organization_id
DROP POLICY IF EXISTS "article_users_insert_own_org" ON article_users;
DROP POLICY IF EXISTS "article_users_select_own_org" ON article_users;
DROP POLICY IF EXISTS "article_users_delete_own_org" ON article_users;
DROP POLICY IF EXISTS "article_users_update_own_org" ON article_users;

-- Now drop the column
ALTER TABLE article_users DROP COLUMN IF EXISTS organization_id;

-- Drop old index if it exists
DROP INDEX IF EXISTS idx_article_users_organization_id;

COMMENT ON TABLE article_users IS 'Junction table for many-to-many relationship between public articles and users. Security enforced via user_id only.';

-- ============================================
-- STEP 2: Remove organization_id from content_sources
-- ============================================

-- First, drop any policies that reference organization_id
DROP POLICY IF EXISTS "content_sources_insert_org" ON content_sources;
DROP POLICY IF EXISTS "content_sources_select_org" ON content_sources;
DROP POLICY IF EXISTS "content_sources_update_org" ON content_sources;
DROP POLICY IF EXISTS "content_sources_delete_org" ON content_sources;

-- Now drop the column
ALTER TABLE content_sources DROP COLUMN IF EXISTS organization_id;

-- Drop old index if it exists
DROP INDEX IF EXISTS idx_content_sources_organization_id;

COMMENT ON TABLE content_sources IS 'User content sources (RSS feeds, newsletters, podcasts). Scoped to individual users via user_id.';

-- ============================================
-- STEP 3: Remove organization_id from content_queue
-- ============================================

-- First, drop any policies that reference organization_id
DROP POLICY IF EXISTS "content_queue_insert_org" ON content_queue;
DROP POLICY IF EXISTS "content_queue_select_org" ON content_queue;
DROP POLICY IF EXISTS "content_queue_update_org" ON content_queue;
DROP POLICY IF EXISTS "content_queue_delete_org" ON content_queue;

-- Now drop the column
ALTER TABLE content_queue DROP COLUMN IF EXISTS organization_id;

-- Drop old index if it exists
DROP INDEX IF EXISTS idx_content_queue_organization_id;

COMMENT ON TABLE content_queue IS 'Queue of discovered content awaiting processing. Scoped to individual users via user_id.';
