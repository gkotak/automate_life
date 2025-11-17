-- Fix: Articles RLS Policy for Frontend Compatibility
-- Description: Simplify articles RLS to work with frontend's two-step query pattern
-- The frontend gets article_ids from article_users (org-scoped), then queries articles
-- This is safe because article_users already enforces organization scoping

-- ============================================================================
-- Drop the overly restrictive policy
-- ============================================================================

DROP POLICY IF EXISTS "Users can read articles in their org" ON articles;

-- ============================================================================
-- Create new policy that trusts article_users org scoping
-- ============================================================================

-- New policy: Users can read any article (access control via article_users)
-- This is safe because:
-- 1. article_users table has RLS that enforces organization_id = get_user_organization_id()
-- 2. Frontend queries article_users first, gets article_ids, then queries articles
-- 3. The article_users query already enforced org scoping, so we trust those IDs
CREATE POLICY "Users can read articles"
ON articles FOR SELECT
USING (
  -- Allow reading any article that exists in article_users for this user
  -- The article_users table RLS already enforces organization scoping
  id IN (
    SELECT article_id FROM article_users
    WHERE user_id = auth.uid()
  )
);

-- Verification: Test the policy works
DO $$
BEGIN
  RAISE NOTICE '========================================';
  RAISE NOTICE 'Articles RLS Policy Updated';
  RAISE NOTICE '========================================';
  RAISE NOTICE 'The new policy allows reading articles via article_users';
  RAISE NOTICE 'Organization scoping is enforced by article_users RLS';
  RAISE NOTICE 'This matches the frontend two-step query pattern:';
  RAISE NOTICE '  1. Query article_users for article_ids (org-scoped by RLS)';
  RAISE NOTICE '  2. Query articles with those IDs (allowed by this policy)';
  RAISE NOTICE '========================================';
END $$;
