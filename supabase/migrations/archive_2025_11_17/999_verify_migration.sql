-- Migration Verification Script
-- Description: Comprehensive checks to verify organizations and user roles migration succeeded
-- Run this to verify all 4 migration scripts completed successfully

-- ============================================================================
-- PART 1: Check Tables Exist
-- ============================================================================

DO $$
DECLARE
  tables_exist BOOLEAN;
BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PART 1: Checking Tables Exist';
  RAISE NOTICE '========================================';

  -- Check organizations table exists
  SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'organizations'
  ) INTO tables_exist;

  IF tables_exist THEN
    RAISE NOTICE '✓ organizations table exists';
  ELSE
    RAISE EXCEPTION '✗ organizations table does NOT exist - run 001_create_organizations_and_users.sql';
  END IF;

  -- Check users table exists
  SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'users'
  ) INTO tables_exist;

  IF tables_exist THEN
    RAISE NOTICE '✓ users table exists';
  ELSE
    RAISE EXCEPTION '✗ users table does NOT exist - run 001_create_organizations_and_users.sql';
  END IF;
END $$;

-- ============================================================================
-- PART 2: Check Data Was Backfilled
-- ============================================================================

DO $$
DECLARE
  auth_user_count INTEGER;
  user_profile_count INTEGER;
  org_count INTEGER;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PART 2: Checking Data Backfill';
  RAISE NOTICE '========================================';

  -- Count auth.users
  SELECT COUNT(*) INTO auth_user_count FROM auth.users;
  RAISE NOTICE 'auth.users count: %', auth_user_count;

  -- Count user profiles
  SELECT COUNT(*) INTO user_profile_count FROM users;
  RAISE NOTICE 'users (profiles) count: %', user_profile_count;

  -- Count organizations
  SELECT COUNT(*) INTO org_count FROM organizations;
  RAISE NOTICE 'organizations count: %', org_count;

  -- Verify counts match
  IF auth_user_count = user_profile_count THEN
    RAISE NOTICE '✓ All auth.users have profiles';
  ELSE
    RAISE WARNING '✗ Mismatch: % auth.users vs % profiles', auth_user_count, user_profile_count;
  END IF;

  IF user_profile_count = org_count THEN
    RAISE NOTICE '✓ Each user has their own organization (1:1 mapping)';
  ELSE
    RAISE WARNING '✗ Mismatch: % users vs % organizations', user_profile_count, org_count;
  END IF;

  -- Check all users are admins (initial migration)
  DECLARE
    admin_count INTEGER;
  BEGIN
    SELECT COUNT(*) INTO admin_count FROM users WHERE role = 'admin';
    IF admin_count = user_profile_count THEN
      RAISE NOTICE '✓ All users are admins (as expected for migration)';
    ELSE
      RAISE NOTICE 'ℹ % admins, % total users', admin_count, user_profile_count;
    END IF;
  END;
END $$;

-- ============================================================================
-- PART 3: Check organization_id Columns Added
-- ============================================================================

DO $$
DECLARE
  column_exists BOOLEAN;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PART 3: Checking organization_id Columns';
  RAISE NOTICE '========================================';

  -- Check article_users.organization_id
  SELECT EXISTS (
    SELECT FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'article_users'
    AND column_name = 'organization_id'
  ) INTO column_exists;

  IF column_exists THEN
    RAISE NOTICE '✓ article_users.organization_id exists';
  ELSE
    RAISE EXCEPTION '✗ article_users.organization_id does NOT exist - run 003_add_organization_id_to_tables.sql';
  END IF;

  -- Check content_sources.organization_id
  SELECT EXISTS (
    SELECT FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'content_sources'
    AND column_name = 'organization_id'
  ) INTO column_exists;

  IF column_exists THEN
    RAISE NOTICE '✓ content_sources.organization_id exists';
  ELSE
    RAISE EXCEPTION '✗ content_sources.organization_id does NOT exist - run 003_add_organization_id_to_tables.sql';
  END IF;

  -- Check content_queue.organization_id
  SELECT EXISTS (
    SELECT FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'content_queue'
    AND column_name = 'organization_id'
  ) INTO column_exists;

  IF column_exists THEN
    RAISE NOTICE '✓ content_queue.organization_id exists';
  ELSE
    RAISE EXCEPTION '✗ content_queue.organization_id does NOT exist - run 003_add_organization_id_to_tables.sql';
  END IF;
END $$;

-- ============================================================================
-- PART 4: Check for NULL organization_id Values
-- ============================================================================

DO $$
DECLARE
  null_count INTEGER;
  total_count INTEGER;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PART 4: Checking for NULL organization_id';
  RAISE NOTICE '========================================';

  -- Check article_users
  SELECT COUNT(*) INTO total_count FROM article_users;
  SELECT COUNT(*) INTO null_count FROM article_users WHERE organization_id IS NULL;
  IF null_count = 0 THEN
    RAISE NOTICE '✓ article_users: 0 NULL values (% total rows)', total_count;
  ELSE
    RAISE WARNING '✗ article_users: % NULL values out of % rows', null_count, total_count;
  END IF;

  -- Check content_sources
  SELECT COUNT(*) INTO total_count FROM content_sources;
  SELECT COUNT(*) INTO null_count FROM content_sources WHERE organization_id IS NULL;
  IF null_count = 0 THEN
    RAISE NOTICE '✓ content_sources: 0 NULL values (% total rows)', total_count;
  ELSE
    RAISE WARNING '✗ content_sources: % NULL values out of % rows', null_count, total_count;
  END IF;

  -- Check content_queue
  SELECT COUNT(*) INTO total_count FROM content_queue;
  SELECT COUNT(*) INTO null_count FROM content_queue WHERE organization_id IS NULL;
  IF null_count = 0 THEN
    RAISE NOTICE '✓ content_queue: 0 NULL values (% total rows)', total_count;
  ELSE
    RAISE WARNING '✗ content_queue: % NULL values out of % rows', null_count, total_count;
  END IF;
END $$;

-- ============================================================================
-- PART 5: Check RLS Policies Exist
-- ============================================================================

DO $$
DECLARE
  policy_count INTEGER;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PART 5: Checking RLS Policies';
  RAISE NOTICE '========================================';

  -- Count policies for each table
  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'organizations';
  RAISE NOTICE 'organizations: % policies', policy_count;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'users';
  RAISE NOTICE 'users: % policies', policy_count;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'articles';
  RAISE NOTICE 'articles: % policies', policy_count;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'article_users';
  RAISE NOTICE 'article_users: % policies', policy_count;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'content_sources';
  RAISE NOTICE 'content_sources: % policies', policy_count;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'content_queue';
  RAISE NOTICE 'content_queue: % policies', policy_count;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'conversations';
  RAISE NOTICE 'conversations: % policies', policy_count;

  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public' AND tablename = 'messages';
  RAISE NOTICE 'messages: % policies', policy_count;
END $$;

-- ============================================================================
-- PART 6: Check Helper Functions Exist
-- ============================================================================

DO $$
DECLARE
  function_exists BOOLEAN;
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PART 6: Checking Helper Functions';
  RAISE NOTICE '========================================';

  -- Check get_user_organization_id()
  SELECT EXISTS (
    SELECT FROM pg_proc
    WHERE proname = 'get_user_organization_id'
  ) INTO function_exists;

  IF function_exists THEN
    RAISE NOTICE '✓ get_user_organization_id() function exists';
  ELSE
    RAISE EXCEPTION '✗ get_user_organization_id() function does NOT exist - run 001_create_organizations_and_users.sql';
  END IF;

  -- Check is_user_admin()
  SELECT EXISTS (
    SELECT FROM pg_proc
    WHERE proname = 'is_user_admin'
  ) INTO function_exists;

  IF function_exists THEN
    RAISE NOTICE '✓ is_user_admin() function exists';
  ELSE
    RAISE EXCEPTION '✗ is_user_admin() function does NOT exist - run 001_create_organizations_and_users.sql';
  END IF;
END $$;

-- ============================================================================
-- PART 7: Sample Data Display
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'PART 7: Sample Data';
  RAISE NOTICE '========================================';
END $$;

-- Show sample organizations
SELECT
  id,
  name,
  billing_id,
  created_at
FROM organizations
LIMIT 3;

-- Show sample users with org info
SELECT
  u.id,
  u.display_name,
  u.role,
  o.name as organization_name,
  u.created_at
FROM users u
JOIN organizations o ON u.organization_id = o.id
LIMIT 3;

-- Show table row counts with org distribution
SELECT
  'article_users' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT organization_id) as distinct_orgs,
  COUNT(DISTINCT user_id) as distinct_users
FROM article_users
UNION ALL
SELECT
  'content_sources' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT organization_id) as distinct_orgs,
  COUNT(DISTINCT user_id) as distinct_users
FROM content_sources
UNION ALL
SELECT
  'content_queue' as table_name,
  COUNT(*) as total_rows,
  COUNT(DISTINCT organization_id) as distinct_orgs,
  COUNT(DISTINCT user_id) as distinct_users
FROM content_queue;

-- ============================================================================
-- FINAL SUMMARY
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'VERIFICATION COMPLETE';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'If you see this message with all ✓ checks passing,';
  RAISE NOTICE 'your migration was successful!';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Test logging in to your web app';
  RAISE NOTICE '2. Check that userProfile and organization load in AuthContext';
  RAISE NOTICE '3. Verify data isolation (create second user, check can''t see first user''s data)';
  RAISE NOTICE '========================================';
END $$;
