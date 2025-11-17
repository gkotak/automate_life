-- Clean Slate: Remove ALL existing RLS policies and start fresh
-- This fixes the issue where multiple conflicting policies exist

-- ============================================================================
-- STEP 1: Drop ALL existing policies on articles table
-- ============================================================================

-- Drop all the duplicate/old policies
DROP POLICY IF EXISTS "Allow public read access to articles" ON articles;
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

-- ============================================================================
-- STEP 2: Create clean, simple policies
-- ============================================================================

-- PUBLIC READ: Anyone (authenticated or not) can read articles
CREATE POLICY "public_read_articles"
ON articles FOR SELECT
TO public
USING (true);

-- AUTHENTICATED INSERT: Any authenticated user can create articles
CREATE POLICY "authenticated_insert_articles"
ON articles FOR INSERT
TO authenticated
WITH CHECK (true);

-- AUTHENTICATED UPDATE: Users can update articles they have in article_users
CREATE POLICY "authenticated_update_articles"
ON articles FOR UPDATE
TO authenticated
USING (
  id IN (
    SELECT article_id FROM article_users WHERE user_id = auth.uid()
  )
);

-- AUTHENTICATED DELETE: Users can delete articles they have in article_users
CREATE POLICY "authenticated_delete_articles"
ON articles FOR DELETE
TO authenticated
USING (
  id IN (
    SELECT article_id FROM article_users WHERE user_id = auth.uid()
  )
);

-- ============================================================================
-- STEP 3: Fix article_users policies
-- ============================================================================

-- Drop old policies
DROP POLICY IF EXISTS "Users can read article_users in their org" ON article_users;
DROP POLICY IF EXISTS "Users can save articles to their org" ON article_users;
DROP POLICY IF EXISTS "Users can unsave their articles" ON article_users;
DROP POLICY IF EXISTS "Allow authenticated users to read article_users" ON article_users;
DROP POLICY IF EXISTS "Users can manage their own article relationships" ON article_users;
DROP POLICY IF EXISTS "Users can read their own saved articles" ON article_users;

-- PUBLIC READ: Anyone can see article_users (frontend filters by user)
CREATE POLICY "public_read_article_users"
ON article_users FOR SELECT
TO public
USING (true);

-- AUTHENTICATED INSERT: Users can save articles (must match their user_id and org)
CREATE POLICY "authenticated_insert_article_users"
ON article_users FOR INSERT
TO authenticated
WITH CHECK (
  user_id = auth.uid()
  AND organization_id = get_user_organization_id()
);

-- AUTHENTICATED DELETE: Users can delete their own article_users records
CREATE POLICY "authenticated_delete_article_users"
ON article_users FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'CLEAN SLATE RLS POLICIES';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'articles table:';
  RAISE NOTICE '  - SELECT: Public (anyone can read)';
  RAISE NOTICE '  - INSERT: Authenticated users';
  RAISE NOTICE '  - UPDATE: Users with article_users record';
  RAISE NOTICE '  - DELETE: Users with article_users record';
  RAISE NOTICE '';
  RAISE NOTICE 'article_users table:';
  RAISE NOTICE '  - SELECT: Public (frontend filters)';
  RAISE NOTICE '  - INSERT: Authenticated (must match user_id + org)';
  RAISE NOTICE '  - DELETE: User can delete their own';
  RAISE NOTICE '';
  RAISE NOTICE 'Removed all conflicting duplicate policies!';
  RAISE NOTICE '========================================';
END $$;

-- Show final policies
SELECT
  tablename,
  policyname,
  cmd as operation,
  roles::text
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('articles', 'article_users')
ORDER BY tablename, cmd, policyname;
