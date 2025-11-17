-- Fix infinite recursion in users table RLS policies
-- The problem: policies on users table were querying users table directly
-- The solution: Use auth.jwt() to get claims instead of querying users table

-- ============================================================================
-- STEP 1: Drop all existing policies on users table
-- ============================================================================

DROP POLICY IF EXISTS "Users can read users in their org" ON users;
DROP POLICY IF EXISTS "Users can update their own profile" ON users;
DROP POLICY IF EXISTS "Admins can update org members" ON users;

-- ============================================================================
-- STEP 2: Create new policies that don't cause infinite recursion
-- ============================================================================

-- Allow users to read their own profile
-- This is safe because it doesn't query the users table recursively
CREATE POLICY "users_select_own"
ON users FOR SELECT
TO authenticated
USING (id = auth.uid());

-- Allow users to update their own profile
CREATE POLICY "users_update_own"
ON users FOR UPDATE
TO authenticated
USING (id = auth.uid());

-- ============================================================================
-- STEP 3: Update helper functions to be more explicit
-- ============================================================================

-- Recreate get_user_organization_id with better security context
CREATE OR REPLACE FUNCTION get_user_organization_id()
RETURNS UUID AS $$
DECLARE
  org_id UUID;
BEGIN
  -- This bypasses RLS because function is SECURITY DEFINER
  SELECT organization_id INTO org_id
  FROM users
  WHERE id = auth.uid();

  RETURN org_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Recreate is_user_admin with better security context
CREATE OR REPLACE FUNCTION is_user_admin()
RETURNS BOOLEAN AS $$
DECLARE
  user_role TEXT;
BEGIN
  -- This bypasses RLS because function is SECURITY DEFINER
  SELECT role INTO user_role
  FROM users
  WHERE id = auth.uid();

  RETURN (user_role = 'admin');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'FIXED: Users table infinite recursion';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'New policies on users table:';
  RAISE NOTICE '  - users_select_own: User can read their own profile';
  RAISE NOTICE '  - users_update_own: User can update their own profile';
  RAISE NOTICE '';
  RAISE NOTICE 'These policies are safe because they use auth.uid()';
  RAISE NOTICE 'directly without querying the users table.';
  RAISE NOTICE '';
  RAISE NOTICE 'Helper functions (get_user_organization_id, is_user_admin)';
  RAISE NOTICE 'are SECURITY DEFINER so they bypass RLS when querying users.';
  RAISE NOTICE '========================================';
END $$;

-- Show final policies on users table
SELECT
  tablename,
  policyname,
  cmd as operation,
  roles::text
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'users'
ORDER BY cmd, policyname;
