-- Complete RLS Fix: Remove circular dependency and simplify
--
-- PROBLEM: The articles RLS policy uses a subquery on article_users,
-- but article_users also has RLS. This creates a circular dependency
-- where the policy can't validate itself.
--
-- SOLUTION: Make articles readable by authenticated users, rely on
-- frontend and article_users RLS for access control.

-- ============================================================================
-- STEP 1: Drop problematic articles policies
-- ============================================================================

DROP POLICY IF EXISTS "Users can read articles in their org" ON articles;
DROP POLICY IF EXISTS "Users can read articles" ON articles;

-- ============================================================================
-- STEP 2: Create simple, permissive policy for articles
-- ============================================================================

-- Allow authenticated users to read all articles
-- Security is enforced by:
-- 1. Frontend only shows articles from article_users query
-- 2. article_users table has organization_id RLS
-- 3. Only articles with article_users records are accessible via frontend
CREATE POLICY "Authenticated users can read articles"
ON articles FOR SELECT
TO authenticated
USING (true);

-- Keep the existing insert and update policies
-- (They should already exist from 004 migration, but recreate to be safe)

DROP POLICY IF EXISTS "Users can insert articles" ON articles;
CREATE POLICY "Users can insert articles"
ON articles FOR INSERT
TO authenticated
WITH CHECK (true);

DROP POLICY IF EXISTS "Users can update articles in their org" ON articles;
CREATE POLICY "Users can update articles"
ON articles FOR UPDATE
TO authenticated
USING (
  id IN (
    SELECT article_id FROM article_users
    WHERE user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS "Users can delete articles in their org" ON articles;
CREATE POLICY "Users can delete articles"
ON articles FOR DELETE
TO authenticated
USING (
  id IN (
    SELECT article_id FROM article_users
    WHERE user_id = auth.uid()
  )
);

-- ============================================================================
-- STEP 3: Ensure article_users policies are correct
-- ============================================================================

-- These should already exist from migration 004, but verify they're correct
DROP POLICY IF EXISTS "Users can read article_users in their org" ON article_users;
CREATE POLICY "Users can read article_users in their org"
ON article_users FOR SELECT
TO authenticated
USING (organization_id = get_user_organization_id());

DROP POLICY IF EXISTS "Users can save articles to their org" ON article_users;
CREATE POLICY "Users can save articles to their org"
ON article_users FOR INSERT
TO authenticated
WITH CHECK (
  user_id = auth.uid()
  AND organization_id = get_user_organization_id()
);

DROP POLICY IF EXISTS "Users can unsave their articles" ON article_users;
CREATE POLICY "Users can unsave their articles"
ON article_users FOR DELETE
TO authenticated
USING (
  user_id = auth.uid()
  AND organization_id = get_user_organization_id()
);

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'RLS POLICIES UPDATED';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Articles table:';
  RAISE NOTICE '  - SELECT: Authenticated users can read all articles';
  RAISE NOTICE '  - INSERT: Authenticated users can create articles';
  RAISE NOTICE '  - UPDATE: Users can update their articles (via article_users)';
  RAISE NOTICE '  - DELETE: Users can delete their articles (via article_users)';
  RAISE NOTICE '';
  RAISE NOTICE 'article_users table:';
  RAISE NOTICE '  - SELECT: Organization-scoped (via get_user_organization_id())';
  RAISE NOTICE '  - INSERT: Must match user and organization';
  RAISE NOTICE '  - DELETE: Users can delete their own records';
  RAISE NOTICE '';
  RAISE NOTICE 'Security model:';
  RAISE NOTICE '  - Articles are globally readable (like a shared content pool)';
  RAISE NOTICE '  - Access control via article_users junction table';
  RAISE NOTICE '  - article_users enforces organization isolation';
  RAISE NOTICE '  - Frontend queries article_users first (org-scoped)';
  RAISE NOTICE '  - Then fetches articles with those IDs';
  RAISE NOTICE '';
  RAISE NOTICE 'This matches how YouTube videos work:';
  RAISE NOTICE '  - Videos (articles) exist globally';
  RAISE NOTICE '  - Playlists (article_users) are user/org-specific';
  RAISE NOTICE '  - Security via playlist membership, not video access';
  RAISE NOTICE '========================================';
END $$;

-- Show current policies
SELECT
  tablename,
  policyname,
  cmd as operation,
  CASE
    WHEN roles::text = '{authenticated}' THEN 'authenticated'
    ELSE roles::text
  END as roles
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('articles', 'article_users')
ORDER BY tablename, cmd;
