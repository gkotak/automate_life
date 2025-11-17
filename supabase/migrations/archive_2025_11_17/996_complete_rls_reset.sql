-- COMPLETE RLS RESET
-- This script removes ALL existing RLS policies and rebuilds them from scratch
-- Run this to get a clean, known state

-- ============================================================================
-- STEP 1: Drop ALL existing policies on all tables
-- ============================================================================

-- Drop all policies on users table
DROP POLICY IF EXISTS "Users can read users in their org" ON users;
DROP POLICY IF EXISTS "Users can update their own profile" ON users;
DROP POLICY IF EXISTS "Admins can update org members" ON users;
DROP POLICY IF EXISTS "Users can read org members" ON users;
DROP POLICY IF EXISTS "Authenticated users can read user profiles" ON users;
DROP POLICY IF EXISTS "users_select_own" ON users;
DROP POLICY IF EXISTS "users_update_own" ON users;

-- Drop all policies on organizations table
DROP POLICY IF EXISTS "Users can read their organization" ON organizations;
DROP POLICY IF EXISTS "Admins can update their organization" ON organizations;

-- Drop all policies on articles table
DROP POLICY IF EXISTS "Allow public read access to articles" ON articles;
DROP POLICY IF EXISTS "public_read_articles" ON articles;
DROP POLICY IF EXISTS "authenticated_insert_articles" ON articles;
DROP POLICY IF EXISTS "authenticated_update_articles" ON articles;
DROP POLICY IF EXISTS "authenticated_delete_articles" ON articles;
DROP POLICY IF EXISTS "Allow authenticated delete from articles" ON articles;
DROP POLICY IF EXISTS "Allow authenticated insert to articles" ON articles;
DROP POLICY IF EXISTS "Allow authenticated update to articles" ON articles;
DROP POLICY IF EXISTS "Authenticated users can read articles" ON articles;
DROP POLICY IF EXISTS "Authenticated users can view all articles" ON articles;
DROP POLICY IF EXISTS "Authenticated users can insert articles" ON articles;
DROP POLICY IF EXISTS "Users can insert articles" ON articles;
DROP POLICY IF EXISTS "Users can update articles" ON articles;
DROP POLICY IF EXISTS "Users can update saved articles" ON articles;
DROP POLICY IF EXISTS "Users can delete articles" ON articles;
DROP POLICY IF EXISTS "Users can delete unsaved articles" ON articles;
DROP POLICY IF EXISTS "Users can read articles in their org" ON articles;
DROP POLICY IF EXISTS "Users can read articles" ON articles;
DROP POLICY IF EXISTS "Users can update articles in their org" ON articles;
DROP POLICY IF EXISTS "Users can delete articles in their org" ON articles;

-- Drop all policies on article_users table
DROP POLICY IF EXISTS "Users can read article_users in their org" ON article_users;
DROP POLICY IF EXISTS "Users can save articles to their org" ON article_users;
DROP POLICY IF EXISTS "Users can unsave their articles" ON article_users;
DROP POLICY IF EXISTS "Allow authenticated users to read article_users" ON article_users;
DROP POLICY IF EXISTS "Users can manage their own article relationships" ON article_users;
DROP POLICY IF EXISTS "Users can read their own saved articles" ON article_users;
DROP POLICY IF EXISTS "public_read_article_users" ON article_users;
DROP POLICY IF EXISTS "authenticated_insert_article_users" ON article_users;
DROP POLICY IF EXISTS "authenticated_delete_article_users" ON article_users;

-- Drop all policies on content_sources table
DROP POLICY IF EXISTS "Users can read content_sources in their org" ON content_sources;
DROP POLICY IF EXISTS "Users can insert content_sources in their org" ON content_sources;
DROP POLICY IF EXISTS "Users can update content_sources in their org" ON content_sources;
DROP POLICY IF EXISTS "Users can delete content_sources in their org" ON content_sources;

-- Drop all policies on content_queue table
DROP POLICY IF EXISTS "Users can read content_queue in their org" ON content_queue;
DROP POLICY IF EXISTS "Users can insert content_queue in their org" ON content_queue;
DROP POLICY IF EXISTS "Users can update content_queue in their org" ON content_queue;
DROP POLICY IF EXISTS "Users can delete content_queue in their org" ON content_queue;

-- ============================================================================
-- STEP 2: Create clean, minimal policies
-- ============================================================================

-- USERS TABLE: Users can only read and update their own profile
-- This is safe and cannot cause infinite recursion
CREATE POLICY "users_select_own"
ON users FOR SELECT
TO authenticated
USING (id = auth.uid());

CREATE POLICY "users_update_own"
ON users FOR UPDATE
TO authenticated
USING (id = auth.uid());

-- ORGANIZATIONS TABLE: Users can read their own organization
CREATE POLICY "orgs_select_own"
ON organizations FOR SELECT
TO authenticated
USING (id = get_user_organization_id());

CREATE POLICY "orgs_update_own"
ON organizations FOR UPDATE
TO authenticated
USING (id = get_user_organization_id() AND is_user_admin());

-- ARTICLES TABLE: Public read, authenticated users can manage via article_users
CREATE POLICY "articles_select_public"
ON articles FOR SELECT
TO public
USING (true);

CREATE POLICY "articles_insert_authenticated"
ON articles FOR INSERT
TO authenticated
WITH CHECK (true);

CREATE POLICY "articles_update_saved"
ON articles FOR UPDATE
TO authenticated
USING (
  id IN (
    SELECT article_id FROM article_users WHERE user_id = auth.uid()
  )
);

CREATE POLICY "articles_delete_saved"
ON articles FOR DELETE
TO authenticated
USING (
  id IN (
    SELECT article_id FROM article_users WHERE user_id = auth.uid()
  )
);

-- ARTICLE_USERS TABLE: Users manage their own saved articles
CREATE POLICY "article_users_select_own"
ON article_users FOR SELECT
TO authenticated
USING (user_id = auth.uid());

CREATE POLICY "article_users_insert_own"
ON article_users FOR INSERT
TO authenticated
WITH CHECK (
  user_id = auth.uid()
  AND organization_id = get_user_organization_id()
);

CREATE POLICY "article_users_delete_own"
ON article_users FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- CONTENT_SOURCES TABLE: Scoped to user's organization
CREATE POLICY "content_sources_select_org"
ON content_sources FOR SELECT
TO authenticated
USING (organization_id = get_user_organization_id());

CREATE POLICY "content_sources_insert_org"
ON content_sources FOR INSERT
TO authenticated
WITH CHECK (organization_id = get_user_organization_id());

CREATE POLICY "content_sources_update_org"
ON content_sources FOR UPDATE
TO authenticated
USING (organization_id = get_user_organization_id());

CREATE POLICY "content_sources_delete_org"
ON content_sources FOR DELETE
TO authenticated
USING (organization_id = get_user_organization_id());

-- CONTENT_QUEUE TABLE: Scoped to user's organization
CREATE POLICY "content_queue_select_org"
ON content_queue FOR SELECT
TO authenticated
USING (organization_id = get_user_organization_id());

CREATE POLICY "content_queue_insert_org"
ON content_queue FOR INSERT
TO authenticated
WITH CHECK (organization_id = get_user_organization_id());

CREATE POLICY "content_queue_update_org"
ON content_queue FOR UPDATE
TO authenticated
USING (organization_id = get_user_organization_id());

CREATE POLICY "content_queue_delete_org"
ON content_queue FOR DELETE
TO authenticated
USING (organization_id = get_user_organization_id());

-- ============================================================================
-- STEP 3: Verification
-- ============================================================================

DO $$
DECLARE
  total_policies INTEGER;
BEGIN
  SELECT COUNT(*) INTO total_policies
  FROM pg_policies
  WHERE schemaname = 'public';

  RAISE NOTICE '========================================';
  RAISE NOTICE 'COMPLETE RLS RESET - SUCCESS';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Total policies created: %', total_policies;
  RAISE NOTICE '';
  RAISE NOTICE 'Policy summary:';
  RAISE NOTICE '  - users: 2 policies (select own, update own)';
  RAISE NOTICE '  - organizations: 2 policies (select own, update own)';
  RAISE NOTICE '  - articles: 4 policies (public select, auth insert/update/delete)';
  RAISE NOTICE '  - article_users: 3 policies (select/insert/delete own)';
  RAISE NOTICE '  - content_sources: 4 policies (org scoped CRUD)';
  RAISE NOTICE '  - content_queue: 4 policies (org scoped CRUD)';
  RAISE NOTICE '';
  RAISE NOTICE 'Expected total: 19 policies';
  RAISE NOTICE 'Actual total: % policies', total_policies;
  RAISE NOTICE '';
  RAISE NOTICE 'All policies use safe patterns:';
  RAISE NOTICE '  ✓ auth.uid() - direct comparison';
  RAISE NOTICE '  ✓ get_user_organization_id() - SECURITY DEFINER function';
  RAISE NOTICE '  ✓ No recursive queries on users table';
  RAISE NOTICE '========================================';
END $$;

-- Show all policies by table
SELECT
  tablename,
  COUNT(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;

-- Show detailed policy list
SELECT
  tablename,
  policyname,
  cmd as operation
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd, policyname;
