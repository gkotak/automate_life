-- Debug: Check Current RLS State and Test Queries
-- Run this to understand what's blocking the frontend

-- ============================================================================
-- PART 1: Show all current RLS policies
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'CURRENT RLS POLICIES';
  RAISE NOTICE '========================================';
END $$;

SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('articles', 'article_users', 'users', 'organizations')
ORDER BY tablename, policyname;

-- ============================================================================
-- PART 2: Check user profiles exist
-- ============================================================================

DO $$
DECLARE
  auth_count INTEGER;
  profile_count INTEGER;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'USER PROFILE CHECK';
  RAISE NOTICE '========================================';

  SELECT COUNT(*) INTO auth_count FROM auth.users;
  SELECT COUNT(*) INTO profile_count FROM users;

  RAISE NOTICE 'auth.users count: %', auth_count;
  RAISE NOTICE 'users (profiles) count: %', profile_count;

  IF auth_count = profile_count THEN
    RAISE NOTICE '✓ All auth users have profiles';
  ELSE
    RAISE WARNING '✗ Missing profiles: % auth users vs % profiles', auth_count, profile_count;
  END IF;
END $$;

-- Show user details
SELECT
  'User profiles:' as info,
  u.id,
  u.organization_id,
  u.role,
  o.name as org_name,
  au.email
FROM users u
JOIN organizations o ON u.organization_id = o.id
JOIN auth.users au ON u.id = au.id;

-- ============================================================================
-- PART 3: Check article_users data
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'ARTICLE_USERS DATA';
  RAISE NOTICE '========================================';
END $$;

SELECT
  'article_users sample:' as info,
  au.user_id,
  au.article_id,
  au.organization_id,
  a.title,
  u.role as user_role
FROM article_users au
JOIN articles a ON au.article_id = a.id
JOIN users u ON au.user_id = u.id
LIMIT 10;

-- Count by user
SELECT
  'Articles per user:' as info,
  au.user_id,
  u.organization_id,
  COUNT(*) as article_count
FROM article_users au
JOIN users u ON au.user_id = u.id
GROUP BY au.user_id, u.organization_id;

-- ============================================================================
-- PART 4: Test RLS with actual user
-- ============================================================================

DO $$
DECLARE
  test_user_id UUID;
  test_org_id UUID;
  article_users_count INTEGER;
  articles_count INTEGER;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'RLS SIMULATION TEST';
  RAISE NOTICE '========================================';

  -- Get first user
  SELECT id INTO test_user_id FROM auth.users LIMIT 1;
  RAISE NOTICE 'Testing with user_id: %', test_user_id;

  -- Get their org
  SELECT organization_id INTO test_org_id FROM users WHERE id = test_user_id;
  RAISE NOTICE 'User organization_id: %', test_org_id;

  -- Count article_users they should see
  SELECT COUNT(*) INTO article_users_count
  FROM article_users
  WHERE user_id = test_user_id
    AND organization_id = test_org_id;

  RAISE NOTICE 'article_users count (with org filter): %', article_users_count;

  -- Count articles they should be able to access
  SELECT COUNT(*) INTO articles_count
  FROM articles
  WHERE id IN (
    SELECT article_id FROM article_users
    WHERE user_id = test_user_id
  );

  RAISE NOTICE 'articles count (via article_users): %', articles_count;

  IF article_users_count = 0 THEN
    RAISE WARNING '✗ User has no article_users records!';
  ELSIF articles_count = 0 THEN
    RAISE WARNING '✗ User has article_users but articles query returns 0!';
  ELSE
    RAISE NOTICE '✓ User should see % articles', articles_count;
  END IF;
END $$;

-- ============================================================================
-- PART 5: Test helper functions
-- ============================================================================

DO $$
DECLARE
  test_user_id UUID;
  org_from_function UUID;
  org_from_table UUID;
  is_admin_result BOOLEAN;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'HELPER FUNCTION TEST';
  RAISE NOTICE '========================================';

  -- Get first user
  SELECT id INTO test_user_id FROM auth.users LIMIT 1;

  -- This won't work in DO block since auth.uid() needs real session
  -- But we can show what the functions should return
  SELECT organization_id INTO org_from_table FROM users WHERE id = test_user_id;
  SELECT role = 'admin' INTO is_admin_result FROM users WHERE id = test_user_id;

  RAISE NOTICE 'For user %:', test_user_id;
  RAISE NOTICE '  - organization_id from table: %', org_from_table;
  RAISE NOTICE '  - is_admin from table: %', is_admin_result;
  RAISE NOTICE '';
  RAISE NOTICE 'NOTE: get_user_organization_id() and is_user_admin()';
  RAISE NOTICE 'use auth.uid() which only works in real user sessions,';
  RAISE NOTICE 'not in this DO block context.';
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'DEBUG COMPLETE';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Check the output above for:';
  RAISE NOTICE '1. Are RLS policies correct?';
  RAISE NOTICE '2. Do users have profiles with organization_id?';
  RAISE NOTICE '3. Do article_users have organization_id set?';
  RAISE NOTICE '4. Can the test query find articles?';
  RAISE NOTICE '========================================';
END $$;
