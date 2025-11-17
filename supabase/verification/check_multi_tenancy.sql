-- ============================================================================
-- MULTI-TENANCY VERIFICATION SCRIPT
-- ============================================================================
-- Run this in Supabase SQL Editor to verify organizations are working
-- ============================================================================

-- 1. Check if organizations table exists and has data
SELECT
  'Organizations' as table_name,
  COUNT(*) as total_records,
  COUNT(DISTINCT id) as unique_orgs
FROM organizations;

-- 2. Check if users are assigned to organizations
SELECT
  'Users with Organizations' as check_name,
  COUNT(*) as total_users,
  COUNT(DISTINCT organization_id) as unique_orgs,
  COUNT(CASE WHEN organization_id IS NULL THEN 1 END) as users_without_org
FROM users;

-- 3. Show sample organization data
SELECT
  o.id,
  o.name as org_name,
  o.created_at,
  COUNT(u.id) as user_count
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id
GROUP BY o.id, o.name, o.created_at
ORDER BY o.created_at DESC
LIMIT 10;

-- 4. Check article_users has organization_id
SELECT
  'Article Users' as table_name,
  COUNT(*) as total_records,
  COUNT(DISTINCT organization_id) as unique_orgs,
  COUNT(CASE WHEN organization_id IS NULL THEN 1 END) as missing_org_id
FROM article_users;

-- 5. Check content_sources has organization_id
SELECT
  'Content Sources' as table_name,
  COUNT(*) as total_records,
  COUNT(DISTINCT organization_id) as unique_orgs,
  COUNT(CASE WHEN organization_id IS NULL THEN 1 END) as missing_org_id
FROM content_sources;

-- 6. Verify RLS policies exist
SELECT
  tablename,
  policyname,
  cmd as operation
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('organizations', 'users', 'articles', 'article_users', 'content_sources', 'content_queue')
ORDER BY tablename, policyname;

-- 7. Check current user's organization (if logged in as a specific user)
-- Replace 'YOUR-USER-ID' with actual auth.users.id to test
-- SELECT
--   u.id as user_id,
--   u.role,
--   o.id as org_id,
--   o.name as org_name
-- FROM users u
-- JOIN organizations o ON o.id = u.organization_id
-- WHERE u.id = 'YOUR-USER-ID';

-- 8. Verify helper functions exist
SELECT
  proname as function_name,
  pg_get_functiondef(oid) as definition
FROM pg_proc
WHERE proname IN ('get_user_organization_id', 'is_user_admin', 'handle_new_user')
ORDER BY proname;
