-- Diagnostic Script for RLS Issues
-- Run this to diagnose why articles aren't loading for logged-in users

-- Replace 'YOUR_USER_ID_HERE' with an actual user ID from auth.users
-- You can get this from: SELECT id FROM auth.users LIMIT 1;

-- ============================================================================
-- PART 1: Check user profile exists
-- ============================================================================

-- First, get a user ID to test with
SELECT
  'User IDs in system:' as info,
  id,
  email
FROM auth.users
LIMIT 3;

-- Check if users have profiles
SELECT
  'User profiles:' as info,
  u.id,
  u.organization_id,
  u.role,
  o.name as org_name
FROM users u
JOIN organizations o ON u.organization_id = o.id
LIMIT 3;

-- ============================================================================
-- PART 2: Check article_users relationships
-- ============================================================================

-- Check article_users data
SELECT
  'article_users sample:' as info,
  au.user_id,
  au.article_id,
  au.organization_id,
  a.title
FROM article_users au
JOIN articles a ON au.article_id = a.id
LIMIT 5;

-- ============================================================================
-- PART 3: Test RLS policies manually
-- ============================================================================

-- Test the helper function (run as service_role)
-- Pick a user_id from the first query above and replace below
DO $$
DECLARE
  test_user_id UUID;
  test_org_id UUID;
BEGIN
  -- Get first user
  SELECT id INTO test_user_id FROM auth.users LIMIT 1;

  RAISE NOTICE 'Testing with user_id: %', test_user_id;

  -- Try to get their org
  SELECT organization_id INTO test_org_id FROM users WHERE id = test_user_id;

  IF test_org_id IS NULL THEN
    RAISE WARNING 'User % has NO organization_id in users table!', test_user_id;
  ELSE
    RAISE NOTICE 'User % has organization_id: %', test_user_id, test_org_id;
  END IF;

  -- Check their articles
  RAISE NOTICE 'Articles for this user:';
  PERFORM a.id, a.title
  FROM articles a
  WHERE a.id IN (
    SELECT article_id FROM article_users WHERE user_id = test_user_id
  );

END $$;

-- ============================================================================
-- PART 4: Check RLS policies
-- ============================================================================

-- Show current RLS policies on articles
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
FROM pg_policies
WHERE tablename = 'articles';

-- ============================================================================
-- PART 5: Test query that frontend would run
-- ============================================================================

-- This simulates what the frontend query does
-- Replace 'USER_ID_HERE' with actual user ID from first query
SELECT
  'This is what frontend sees:' as info,
  a.id,
  a.title,
  a.url
FROM articles a
WHERE a.id IN (
  SELECT au.article_id
  FROM article_users au
  WHERE au.user_id = (SELECT id FROM auth.users LIMIT 1) -- Replace with actual user
);

-- ============================================================================
-- DIAGNOSIS SUMMARY
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'DIAGNOSIS COMPLETE';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Check the results above for:';
  RAISE NOTICE '1. Do users have profiles in users table?';
  RAISE NOTICE '2. Do article_users have organization_id set?';
  RAISE NOTICE '3. Does the test query return articles?';
  RAISE NOTICE '';
  RAISE NOTICE 'If users have no profiles, the RLS policies will block everything';
  RAISE NOTICE 'If article_users missing organization_id, queries will fail';
  RAISE NOTICE '========================================';
END $$;
