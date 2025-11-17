-- Migration: Backfill Existing Users with Organizations
-- Description: Create personal organizations for all existing users and populate users table
-- Run this AFTER 001_create_organizations_and_users.sql

-- ============================================================================
-- STEP 1: Create personal organization for each existing user
-- ============================================================================

-- Insert organizations for all existing auth.users
INSERT INTO organizations (id, name, metadata)
SELECT
  gen_random_uuid() as id,
  COALESCE(
    raw_user_meta_data->>'display_name',
    email
  ) || '''s Organization' as name,
  jsonb_build_object(
    'is_personal', true,
    'created_from_migration', true
  ) as metadata
FROM auth.users
WHERE id NOT IN (SELECT id FROM users);

-- ============================================================================
-- STEP 2: Create user profiles for all existing users
-- ============================================================================

-- Insert user profiles with organization mapping
-- Each user gets their own org and is set as admin
WITH user_orgs AS (
  SELECT
    u.id as user_id,
    o.id as org_id,
    COALESCE(
      u.raw_user_meta_data->>'display_name',
      split_part(u.email, '@', 1)
    ) as display_name
  FROM auth.users u
  CROSS JOIN LATERAL (
    SELECT id FROM organizations
    WHERE name LIKE '%' || COALESCE(u.raw_user_meta_data->>'display_name', u.email) || '%'
    LIMIT 1
  ) o
  WHERE u.id NOT IN (SELECT id FROM users)
)
INSERT INTO users (id, organization_id, role, display_name)
SELECT
  user_id,
  org_id,
  'admin' as role, -- All existing users become admins of their personal org
  display_name
FROM user_orgs;

-- ============================================================================
-- STEP 3: Verify the migration
-- ============================================================================

-- Check that all auth.users now have profiles
DO $$
DECLARE
  auth_user_count INTEGER;
  profile_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO auth_user_count FROM auth.users;
  SELECT COUNT(*) INTO profile_count FROM users;

  IF auth_user_count != profile_count THEN
    RAISE EXCEPTION 'User count mismatch: % auth.users vs % user profiles', auth_user_count, profile_count;
  ELSE
    RAISE NOTICE 'Successfully created profiles for % users', profile_count;
  END IF;
END $$;

-- Display summary
SELECT
  COUNT(*) as total_users,
  COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
  COUNT(CASE WHEN role = 'member' THEN 1 END) as member_users
FROM users;

SELECT
  COUNT(*) as total_organizations,
  COUNT(CASE WHEN metadata->>'is_personal' = 'true' THEN 1 END) as personal_orgs
FROM organizations;

-- ============================================================================
-- NOTES:
-- - All existing users are set as 'admin' of their personal organization
-- - Each user gets their own organization named after their display name or email
-- - Next, run 003_add_organization_id_to_tables.sql to add org_id to content tables
-- ============================================================================
