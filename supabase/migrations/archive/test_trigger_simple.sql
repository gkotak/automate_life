-- ============================================================================
-- SIMPLE DIRECT TEST - Run each part separately
-- ============================================================================

-- Test 1: Check organizations INSERT policy exists
SELECT
  policyname,
  roles,
  cmd,
  with_check
FROM pg_policies
WHERE tablename = 'organizations' AND cmd = 'INSERT';

-- Test 2: Check users INSERT policy exists
SELECT
  policyname,
  roles,
  cmd,
  with_check
FROM pg_policies
WHERE tablename = 'users' AND cmd = 'INSERT';

-- Test 3: Try to insert into organizations directly
-- This should work if the INSERT policy is correct
INSERT INTO public.organizations (name, created_at, updated_at)
VALUES ('Test Org', NOW(), NOW())
RETURNING id, name;

-- If the above succeeded, you'll see a row returned
-- Now let's clean it up:
DELETE FROM public.organizations WHERE name = 'Test Org';

-- Test 4: Check if trigger and function exist
SELECT EXISTS (
  SELECT 1 FROM information_schema.triggers
  WHERE trigger_name = 'on_auth_user_created'
) as trigger_exists,
EXISTS (
  SELECT 1 FROM information_schema.routines
  WHERE routine_name = 'handle_new_user'
) as function_exists;
