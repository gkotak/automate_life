-- ============================================================================
-- TEST SCRIPT FOR handle_new_user() TRIGGER
-- ============================================================================
-- Run this in Supabase SQL Editor to test if the trigger works
-- ============================================================================

-- Step 1: Check if trigger exists
SELECT
  trigger_name,
  event_manipulation,
  event_object_table,
  action_statement
FROM information_schema.triggers
WHERE trigger_name = 'on_auth_user_created';

-- Step 2: Check if function exists
SELECT
  routine_name,
  routine_type,
  security_type
FROM information_schema.routines
WHERE routine_name = 'handle_new_user';

-- Step 3: Check current RLS policies on organizations
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
WHERE tablename = 'organizations';

-- Step 4: Check current RLS policies on users
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
WHERE tablename = 'users';

-- Step 5: Test the function directly (without creating actual auth user)
-- This will show us the exact error if there is one
DO $$
DECLARE
  test_user_id UUID := gen_random_uuid();
  test_email TEXT := 'test@example.com';
  new_org_id UUID;
  org_name TEXT;
BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Testing handle_new_user() function logic';
  RAISE NOTICE 'Test User ID: %', test_user_id;
  RAISE NOTICE '========================================';

  -- Simulate what the trigger does
  org_name := COALESCE(
    split_part(test_email, '@', 1) || '''s Organization',
    'Personal Organization'
  );

  RAISE NOTICE 'Organization name: %', org_name;

  -- Try to insert organization
  BEGIN
    INSERT INTO public.organizations (name, created_at, updated_at)
    VALUES (org_name, NOW(), NOW())
    RETURNING id INTO new_org_id;

    RAISE NOTICE '✅ Organization created with ID: %', new_org_id;
  EXCEPTION
    WHEN OTHERS THEN
      RAISE NOTICE '❌ Failed to create organization: %', SQLERRM;
      RAISE EXCEPTION 'Organization insert failed: %', SQLERRM;
  END;

  -- Try to insert user profile
  BEGIN
    INSERT INTO public.users (
      id,
      organization_id,
      role,
      display_name,
      created_at,
      updated_at
    )
    VALUES (
      test_user_id,
      new_org_id,
      'admin',
      split_part(test_email, '@', 1),
      NOW(),
      NOW()
    );

    RAISE NOTICE '✅ User profile created';
  EXCEPTION
    WHEN OTHERS THEN
      RAISE NOTICE '❌ Failed to create user profile: %', SQLERRM;
      RAISE EXCEPTION 'User profile insert failed: %', SQLERRM;
  END;

  -- Clean up test data
  DELETE FROM public.users WHERE id = test_user_id;
  DELETE FROM public.organizations WHERE id = new_org_id;

  RAISE NOTICE '========================================';
  RAISE NOTICE '✅ TEST PASSED - Trigger logic works!';
  RAISE NOTICE '========================================';

EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '========================================';
    RAISE NOTICE '❌ TEST FAILED';
    RAISE NOTICE 'Error: %', SQLERRM;
    RAISE NOTICE '========================================';
    -- Rollback is automatic
END $$;
