-- Check if tables exist
SELECT
  table_schema,
  table_name,
  table_type
FROM information_schema.tables
WHERE table_name IN ('organizations', 'users')
  AND table_schema = 'public'
ORDER BY table_name;

-- Check what schema the trigger function is using
SELECT
  routine_schema,
  routine_name,
  routine_type,
  security_type,
  specific_name
FROM information_schema.routines
WHERE routine_name = 'handle_new_user';

-- Try selecting from organizations to confirm it exists
SELECT COUNT(*) as org_count FROM public.organizations;

-- Try selecting from users to confirm it exists
SELECT COUNT(*) as user_count FROM public.users;
