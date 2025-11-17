-- Show EXACTLY what RLS policies are currently active

SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles::text,
  cmd,
  qual,
  with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'articles'
ORDER BY policyname;
