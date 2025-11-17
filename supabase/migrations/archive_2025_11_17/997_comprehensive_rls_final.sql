-- ============================================================================
-- COMPREHENSIVE RLS POLICY RESET - FINAL VERSION
-- ============================================================================
-- This migration:
-- 1. Removes ALL existing RLS policies to eliminate conflicts
-- 2. Creates optimized policies using (select auth.uid()) pattern
-- 3. Implements proper organization scoping for multi-tenancy
-- 4. Avoids infinite recursion in users table
-- 5. Follows the principle: articles are global, access control via article_users
-- ============================================================================

-- ============================================================================
-- STEP 1: Drop ALL existing RLS policies
-- ============================================================================

DO $$
DECLARE
  pol record;
BEGIN
  -- Drop all policies on all public tables
  FOR pol IN
    SELECT schemaname, tablename, policyname
    FROM pg_policies
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I',
      pol.policyname, pol.schemaname, pol.tablename);
  END LOOP;

  RAISE NOTICE 'Dropped all existing RLS policies';
END $$;

-- ============================================================================
-- STEP 2: USERS TABLE - No infinite recursion
-- ============================================================================
-- Users can only read/update their own profile
-- Using (select auth.uid()) for performance optimization

CREATE POLICY "users_select_own"
ON users FOR SELECT
TO authenticated
USING (id = (select auth.uid()));

CREATE POLICY "users_update_own"
ON users FOR UPDATE
TO authenticated
USING (id = (select auth.uid()));

-- ============================================================================
-- STEP 3: ORGANIZATIONS TABLE - Users access their own org
-- ============================================================================

CREATE POLICY "orgs_select_own"
ON organizations FOR SELECT
TO authenticated
USING (id IN (
  SELECT organization_id FROM users WHERE id = (select auth.uid())
));

CREATE POLICY "orgs_update_admin"
ON organizations FOR UPDATE
TO authenticated
USING (
  id IN (
    SELECT organization_id FROM users
    WHERE id = (select auth.uid()) AND role = 'admin'
  )
);

-- ============================================================================
-- STEP 4: ARTICLES TABLE - Public read, controlled write
-- ============================================================================
-- Articles are global content - anyone can read
-- Only users who have saved them (via article_users) can update/delete

CREATE POLICY "articles_select_all"
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
    SELECT article_id FROM article_users
    WHERE user_id = (select auth.uid())
  )
);

CREATE POLICY "articles_delete_saved"
ON articles FOR DELETE
TO authenticated
USING (
  id IN (
    SELECT article_id FROM article_users
    WHERE user_id = (select auth.uid())
  )
);

-- ============================================================================
-- STEP 5: ARTICLE_USERS TABLE - Organization scoped
-- ============================================================================
-- This is the key table that controls article ownership
-- Users can only see/manage their own saved articles within their org

CREATE POLICY "article_users_select_own"
ON article_users FOR SELECT
TO authenticated
USING (user_id = (select auth.uid()));

CREATE POLICY "article_users_insert_own_org"
ON article_users FOR INSERT
TO authenticated
WITH CHECK (
  user_id = (select auth.uid())
  AND organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

CREATE POLICY "article_users_delete_own"
ON article_users FOR DELETE
TO authenticated
USING (user_id = (select auth.uid()));

-- ============================================================================
-- STEP 6: CONTENT_SOURCES TABLE - Organization scoped
-- ============================================================================

CREATE POLICY "content_sources_select_org"
ON content_sources FOR SELECT
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

CREATE POLICY "content_sources_insert_org"
ON content_sources FOR INSERT
TO authenticated
WITH CHECK (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

CREATE POLICY "content_sources_update_org"
ON content_sources FOR UPDATE
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

CREATE POLICY "content_sources_delete_org"
ON content_sources FOR DELETE
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

-- ============================================================================
-- STEP 7: CONTENT_QUEUE TABLE - Organization scoped
-- ============================================================================

CREATE POLICY "content_queue_select_org"
ON content_queue FOR SELECT
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

CREATE POLICY "content_queue_insert_org"
ON content_queue FOR INSERT
TO authenticated
WITH CHECK (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

CREATE POLICY "content_queue_update_org"
ON content_queue FOR UPDATE
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

CREATE POLICY "content_queue_delete_org"
ON content_queue FOR DELETE
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = (select auth.uid())
  )
);

-- ============================================================================
-- STEP 8: CONVERSATIONS TABLE - User scoped
-- ============================================================================

CREATE POLICY "conversations_select_own"
ON conversations FOR SELECT
TO authenticated
USING (user_id = (select auth.uid()));

CREATE POLICY "conversations_insert_own"
ON conversations FOR INSERT
TO authenticated
WITH CHECK (user_id = (select auth.uid()));

CREATE POLICY "conversations_update_own"
ON conversations FOR UPDATE
TO authenticated
USING (user_id = (select auth.uid()));

CREATE POLICY "conversations_delete_own"
ON conversations FOR DELETE
TO authenticated
USING (user_id = (select auth.uid()));

-- ============================================================================
-- STEP 9: MESSAGES TABLE - Via conversation ownership
-- ============================================================================

CREATE POLICY "messages_select_own_conversations"
ON messages FOR SELECT
TO authenticated
USING (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = (select auth.uid())
  )
);

CREATE POLICY "messages_insert_own_conversations"
ON messages FOR INSERT
TO authenticated
WITH CHECK (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = (select auth.uid())
  )
);

CREATE POLICY "messages_update_own_conversations"
ON messages FOR UPDATE
TO authenticated
USING (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = (select auth.uid())
  )
);

CREATE POLICY "messages_delete_own_conversations"
ON messages FOR DELETE
TO authenticated
USING (
  conversation_id IN (
    SELECT id FROM conversations WHERE user_id = (select auth.uid())
  )
);

-- ============================================================================
-- STEP 10: KNOWN_CHANNELS TABLE - Authenticated read, write
-- ============================================================================

CREATE POLICY "known_channels_select_authenticated"
ON known_channels FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "known_channels_modify_authenticated"
ON known_channels FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  total_policies INTEGER;
  table_policy_counts TEXT;
BEGIN
  -- Count total policies
  SELECT COUNT(*) INTO total_policies
  FROM pg_policies
  WHERE schemaname = 'public';

  -- Build summary of policies per table
  SELECT string_agg(
    format('  - %s: %s policies', tablename, policy_count),
    E'\n'
    ORDER BY tablename
  ) INTO table_policy_counts
  FROM (
    SELECT tablename, COUNT(*) as policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    GROUP BY tablename
  ) t;

  RAISE NOTICE '========================================';
  RAISE NOTICE 'COMPREHENSIVE RLS RESET - COMPLETE';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Total policies created: %', total_policies;
  RAISE NOTICE '';
  RAISE NOTICE 'Policies by table:';
  RAISE NOTICE '%', table_policy_counts;
  RAISE NOTICE '';
  RAISE NOTICE 'Key design principles:';
  RAISE NOTICE '  ✓ All policies use (select auth.uid()) for performance';
  RAISE NOTICE '  ✓ Users table has no recursive queries';
  RAISE NOTICE '  ✓ Articles are globally readable';
  RAISE NOTICE '  ✓ Article ownership via article_users table';
  RAISE NOTICE '  ✓ Organization scoping for content_sources and content_queue';
  RAISE NOTICE '  ✓ User-scoped conversations and messages';
  RAISE NOTICE '';
  RAISE NOTICE 'No infinite recursion - safe to use!';
  RAISE NOTICE '========================================';
END $$;

-- Show detailed policy list for verification
SELECT
  tablename,
  policyname,
  cmd as operation,
  CASE
    WHEN roles::text = '{public}' THEN 'public'
    WHEN roles::text = '{authenticated}' THEN 'authenticated'
    ELSE roles::text
  END as role
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, cmd, policyname;
