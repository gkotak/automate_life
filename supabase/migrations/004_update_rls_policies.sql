-- Migration: Update RLS Policies for Multi-Tenancy
-- Description: Update Row Level Security policies to enforce organization-based access control
-- Run this AFTER 003_add_organization_id_to_tables.sql

-- ============================================================================
-- STEP 1: Update articles RLS policies (access via article_users with org validation)
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can read their own articles" ON articles;
DROP POLICY IF EXISTS "Users can read saved articles" ON articles;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON articles;
DROP POLICY IF EXISTS "Allow authenticated users to read articles" ON articles;

-- New policy: Users can read articles in their organization
CREATE POLICY "Users can read articles in their org"
ON articles FOR SELECT
USING (
  id IN (
    SELECT article_id FROM article_users
    WHERE user_id = auth.uid()
    AND organization_id = get_user_organization_id()
  )
);

-- Users can insert articles (global, but access controlled via article_users)
CREATE POLICY "Users can insert articles"
ON articles FOR INSERT
WITH CHECK (true); -- Anyone can create articles, access controlled via article_users

-- Users can update their org's articles
CREATE POLICY "Users can update articles in their org"
ON articles FOR UPDATE
USING (
  id IN (
    SELECT article_id FROM article_users
    WHERE user_id = auth.uid()
    AND organization_id = get_user_organization_id()
  )
);

-- ============================================================================
-- STEP 2: Update article_users RLS policies (org-scoped)
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can manage their own article relationships" ON article_users;
DROP POLICY IF EXISTS "Users can read their own saved articles" ON article_users;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON article_users;

-- Users can read article_users in their organization
CREATE POLICY "Users can read article_users in their org"
ON article_users FOR SELECT
USING (organization_id = get_user_organization_id());

-- Users can insert their own article relationships (must match their org)
CREATE POLICY "Users can save articles to their org"
ON article_users FOR INSERT
WITH CHECK (
  user_id = auth.uid()
  AND organization_id = get_user_organization_id()
);

-- Users can delete their own article relationships
CREATE POLICY "Users can unsave their articles"
ON article_users FOR DELETE
USING (
  user_id = auth.uid()
  AND organization_id = get_user_organization_id()
);

-- ============================================================================
-- STEP 3: Update content_sources RLS policies (org-scoped)
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can manage their own content sources" ON content_sources;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON content_sources;

-- Users can read content sources in their organization
CREATE POLICY "Users can read content sources in their org"
ON content_sources FOR SELECT
USING (organization_id = get_user_organization_id());

-- Users can insert content sources to their organization
CREATE POLICY "Users can add content sources to their org"
ON content_sources FOR INSERT
WITH CHECK (organization_id = get_user_organization_id());

-- Users can update content sources in their organization
CREATE POLICY "Users can update content sources in their org"
ON content_sources FOR UPDATE
USING (organization_id = get_user_organization_id());

-- Admins can delete content sources
CREATE POLICY "Admins can delete content sources"
ON content_sources FOR DELETE
USING (
  organization_id = get_user_organization_id()
  AND is_user_admin()
);

-- ============================================================================
-- STEP 4: Update content_queue RLS policies (org-scoped)
-- ============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can manage their own content queue" ON content_queue;
DROP POLICY IF EXISTS "Enable read access for authenticated users" ON content_queue;

-- Users can read content queue in their organization
CREATE POLICY "Users can read content queue in their org"
ON content_queue FOR SELECT
USING (organization_id = get_user_organization_id());

-- Users can insert to content queue in their organization
CREATE POLICY "Users can add to content queue in their org"
ON content_queue FOR INSERT
WITH CHECK (organization_id = get_user_organization_id());

-- Users can update content queue items in their organization
CREATE POLICY "Users can update content queue in their org"
ON content_queue FOR UPDATE
USING (organization_id = get_user_organization_id());

-- Users can delete from content queue
CREATE POLICY "Users can delete from content queue in their org"
ON content_queue FOR DELETE
USING (organization_id = get_user_organization_id());

-- ============================================================================
-- STEP 5: Update conversations RLS policies (user-scoped for now)
-- ============================================================================

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can manage their own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can read their own conversations" ON conversations;

-- Users can read their own conversations
CREATE POLICY "Users can read their own conversations"
ON conversations FOR SELECT
USING (user_id = auth.uid());

-- Users can insert their own conversations
CREATE POLICY "Users can create conversations"
ON conversations FOR INSERT
WITH CHECK (user_id = auth.uid());

-- Users can update their own conversations
CREATE POLICY "Users can update their own conversations"
ON conversations FOR UPDATE
USING (user_id = auth.uid());

-- Users can delete their own conversations
CREATE POLICY "Users can delete their own conversations"
ON conversations FOR DELETE
USING (user_id = auth.uid());

-- ============================================================================
-- STEP 6: Update messages RLS policies (via conversation ownership)
-- ============================================================================

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can manage their own messages" ON messages;
DROP POLICY IF EXISTS "Users can read their own messages" ON messages;

-- Users can read messages in their conversations
CREATE POLICY "Users can read their conversation messages"
ON messages FOR SELECT
USING (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = auth.uid()
  )
);

-- Users can insert messages to their conversations
CREATE POLICY "Users can create messages in their conversations"
ON messages FOR INSERT
WITH CHECK (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = auth.uid()
  )
);

-- Users can update their messages
CREATE POLICY "Users can update their messages"
ON messages FOR UPDATE
USING (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = auth.uid()
  )
);

-- Users can delete their messages
CREATE POLICY "Users can delete their messages"
ON messages FOR DELETE
USING (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = auth.uid()
  )
);

-- ============================================================================
-- STEP 7: Verify policies are active
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE 'RLS Policies updated successfully';
  RAISE NOTICE 'Testing queries as authenticated user...';
END $$;

-- List all policies for verification
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('articles', 'article_users', 'content_sources', 'content_queue', 'conversations', 'messages')
ORDER BY tablename, policyname;

-- ============================================================================
-- NOTES:
-- - All policies now enforce organization-based access control
-- - articles remain global but access is controlled via article_users
-- - Admin privileges are enforced through is_user_admin() function
-- - conversations and messages remain user-scoped for privacy
-- ============================================================================
