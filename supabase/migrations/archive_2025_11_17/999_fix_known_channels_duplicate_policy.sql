-- ============================================================================
-- FIX DUPLICATE POLICY ON KNOWN_CHANNELS TABLE
-- ============================================================================
-- This migration fixes the performance warning:
-- "Table public.known_channels has multiple permissive policies for
--  role authenticated for action SELECT"
--
-- The issue: We had both a SELECT policy and an ALL policy
-- The fix: Remove the SELECT policy since ALL already includes SELECT
-- ============================================================================

-- Drop the duplicate SELECT policy
DROP POLICY IF EXISTS "known_channels_select_authenticated" ON known_channels;

-- The "known_channels_modify_authenticated" policy with FOR ALL remains
-- and covers all operations (SELECT, INSERT, UPDATE, DELETE)

-- Verification
DO $$
DECLARE
  policy_count INTEGER;
BEGIN
  -- Count policies on known_channels for authenticated role
  SELECT COUNT(*) INTO policy_count
  FROM pg_policies
  WHERE schemaname = 'public'
    AND tablename = 'known_channels'
    AND roles::text LIKE '%authenticated%';

  RAISE NOTICE '========================================';
  RAISE NOTICE 'KNOWN_CHANNELS POLICY FIX - COMPLETE';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Policies on known_channels: %', policy_count;
  RAISE NOTICE '';

  IF policy_count = 1 THEN
    RAISE NOTICE '✓ Only one policy remains (FOR ALL)';
    RAISE NOTICE '✓ No duplicate SELECT policies';
    RAISE NOTICE '✓ Performance warning resolved';
  ELSE
    RAISE WARNING 'Expected 1 policy but found %', policy_count;
  END IF;

  RAISE NOTICE '========================================';
END $$;

-- Show final policy
SELECT
  tablename,
  policyname,
  cmd as operation,
  CASE
    WHEN roles::text = '{public}' THEN 'public'
    WHEN roles::text = '{authenticated}' THEN 'authenticated'
    ELSE roles::text
  END as role
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'known_channels'
ORDER BY policyname;
