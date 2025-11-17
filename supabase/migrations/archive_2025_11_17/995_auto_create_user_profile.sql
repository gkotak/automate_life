-- Auto-create user profile and organization when a new user signs up
-- This ensures every auth.users record has a corresponding users profile

-- ============================================================================
-- STEP 1: Create function to handle new user creation
-- ============================================================================

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  new_org_id UUID;
  user_email TEXT;
  org_name TEXT;
BEGIN
  -- Get user's email from auth.users
  SELECT email INTO user_email FROM auth.users WHERE id = NEW.id;

  -- Create organization name from email (before @)
  org_name := COALESCE(
    split_part(user_email, '@', 1) || '''s Organization',
    'Personal Organization'
  );

  -- Create a new organization for this user
  INSERT INTO organizations (name, created_at, updated_at)
  VALUES (org_name, NOW(), NOW())
  RETURNING id INTO new_org_id;

  -- Create user profile with reference to the new organization
  INSERT INTO users (
    id,
    organization_id,
    role,
    display_name,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id,
    new_org_id,
    'admin', -- First user in an org is admin
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(user_email, '@', 1)),
    NOW(),
    NOW()
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- STEP 2: Create trigger on auth.users
-- ============================================================================

-- Drop trigger if it exists
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

-- Create trigger that fires when a new user is inserted into auth.users
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION handle_new_user();

-- ============================================================================
-- STEP 3: Backfill any existing auth.users that don't have profiles
-- ============================================================================

-- This handles users who signed up after we deployed the users table
-- but before this trigger was created
DO $$
DECLARE
  auth_user RECORD;
  new_org_id UUID;
  org_name TEXT;
  user_display_name TEXT;
BEGIN
  -- Find auth.users without profiles
  FOR auth_user IN
    SELECT au.id, au.email, au.raw_user_meta_data
    FROM auth.users au
    LEFT JOIN users u ON au.id = u.id
    WHERE u.id IS NULL
  LOOP
    RAISE NOTICE 'Creating profile for user: % (%)', auth_user.email, auth_user.id;

    -- Create organization name from email
    org_name := COALESCE(
      split_part(auth_user.email, '@', 1) || '''s Organization',
      'Personal Organization'
    );

    -- Create organization
    INSERT INTO organizations (name, created_at, updated_at)
    VALUES (org_name, NOW(), NOW())
    RETURNING id INTO new_org_id;

    -- Get display name from metadata or email
    user_display_name := COALESCE(
      auth_user.raw_user_meta_data->>'display_name',
      split_part(auth_user.email, '@', 1)
    );

    -- Create user profile
    INSERT INTO users (
      id,
      organization_id,
      role,
      display_name,
      created_at,
      updated_at
    )
    VALUES (
      auth_user.id,
      new_org_id,
      'admin',
      user_display_name,
      NOW(),
      NOW()
    );

    RAISE NOTICE '✓ Created organization % and profile for user %', org_name, auth_user.email;
  END LOOP;
END $$;

-- ============================================================================
-- Verification
-- ============================================================================

DO $$
DECLARE
  auth_count INTEGER;
  user_count INTEGER;
BEGIN
  SELECT COUNT(*) INTO auth_count FROM auth.users;
  SELECT COUNT(*) INTO user_count FROM users;

  RAISE NOTICE '========================================';
  RAISE NOTICE 'AUTO USER PROFILE CREATION';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Trigger created: on_auth_user_created';
  RAISE NOTICE 'Function: handle_new_user()';
  RAISE NOTICE '';
  RAISE NOTICE 'Current state:';
  RAISE NOTICE '  - auth.users: %', auth_count;
  RAISE NOTICE '  - users profiles: %', user_count;

  IF auth_count = user_count THEN
    RAISE NOTICE '  ✓ All auth users have profiles';
  ELSE
    RAISE WARNING '  ✗ Mismatch: % auth.users vs % profiles', auth_count, user_count;
  END IF;

  RAISE NOTICE '';
  RAISE NOTICE 'New users will automatically get:';
  RAISE NOTICE '  - Personal organization';
  RAISE NOTICE '  - User profile with admin role';
  RAISE NOTICE '========================================';
END $$;

-- Show sample user data
SELECT
  u.id,
  u.display_name,
  u.role,
  o.name as organization_name,
  au.email
FROM users u
JOIN organizations o ON u.organization_id = o.id
JOIN auth.users au ON u.id = au.id
ORDER BY u.created_at DESC
LIMIT 5;
