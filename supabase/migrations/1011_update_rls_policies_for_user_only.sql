-- Update RLS policies to use user_id only (remove organization_id checks)
-- This simplifies the security model while maintaining proper isolation

-- ============================================
-- ARTICLE_USERS TABLE POLICIES
-- ============================================

-- Drop old policies
DROP POLICY IF EXISTS "article_users_select_own_org" ON article_users;
DROP POLICY IF EXISTS "article_users_insert_own_org" ON article_users;
DROP POLICY IF EXISTS "article_users_delete_own_org" ON article_users;
DROP POLICY IF EXISTS "article_users_select_own" ON article_users;
DROP POLICY IF EXISTS "article_users_insert_own" ON article_users;
DROP POLICY IF EXISTS "article_users_delete_own" ON article_users;
DROP POLICY IF EXISTS "Users can view own article saves" ON article_users;
DROP POLICY IF EXISTS "Users can save articles" ON article_users;
DROP POLICY IF EXISTS "Users can unsave articles" ON article_users;

-- Create simple user-based policies
CREATE POLICY "article_users_select_own"
ON article_users FOR SELECT
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "article_users_insert_own"
ON article_users FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

CREATE POLICY "article_users_delete_own"
ON article_users FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- ============================================
-- CONTENT_SOURCES TABLE POLICIES
-- ============================================

-- Drop old policies
DROP POLICY IF EXISTS "content_sources_select_org" ON content_sources;
DROP POLICY IF EXISTS "content_sources_insert_org" ON content_sources;
DROP POLICY IF EXISTS "content_sources_update_org" ON content_sources;
DROP POLICY IF EXISTS "content_sources_delete_org" ON content_sources;
DROP POLICY IF EXISTS "content_sources_select_own" ON content_sources;
DROP POLICY IF EXISTS "content_sources_insert_own" ON content_sources;
DROP POLICY IF EXISTS "content_sources_update_own" ON content_sources;
DROP POLICY IF EXISTS "content_sources_delete_own" ON content_sources;

-- Create simple user-based policies
CREATE POLICY "content_sources_select_own"
ON content_sources FOR SELECT
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "content_sources_insert_own"
ON content_sources FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

CREATE POLICY "content_sources_update_own"
ON content_sources FOR UPDATE
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "content_sources_delete_own"
ON content_sources FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- ============================================
-- CONTENT_QUEUE TABLE POLICIES
-- ============================================

-- Drop old policies
DROP POLICY IF EXISTS "content_queue_select_org" ON content_queue;
DROP POLICY IF EXISTS "content_queue_insert_org" ON content_queue;
DROP POLICY IF EXISTS "content_queue_update_org" ON content_queue;
DROP POLICY IF EXISTS "content_queue_delete_org" ON content_queue;
DROP POLICY IF EXISTS "content_queue_select_own" ON content_queue;
DROP POLICY IF EXISTS "content_queue_insert_own" ON content_queue;
DROP POLICY IF EXISTS "content_queue_update_own" ON content_queue;
DROP POLICY IF EXISTS "content_queue_delete_own" ON content_queue;

-- Create simple user-based policies
CREATE POLICY "content_queue_select_own"
ON content_queue FOR SELECT
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "content_queue_insert_own"
ON content_queue FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

CREATE POLICY "content_queue_update_own"
ON content_queue FOR UPDATE
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "content_queue_delete_own"
ON content_queue FOR DELETE
TO authenticated
USING (user_id = auth.uid());
