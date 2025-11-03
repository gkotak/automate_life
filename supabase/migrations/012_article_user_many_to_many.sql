-- ============================================
-- Article-User Many-to-Many Relationship
-- ============================================
-- This migration converts the articles table from one-to-many (article belongs to one user)
-- to many-to-many (article can be saved by multiple users)
--
-- INSTRUCTIONS:
-- 1. Open Supabase Dashboard → SQL Editor
-- 2. Copy and paste this entire script
-- 3. Click "Run" to execute
--
-- WHAT THIS DOES:
-- - Creates article_users junction table for many-to-many relationship
-- - Migrates existing article-user associations to junction table
-- - Removes user_id column from articles table
-- - Keeps url as globally unique (one article per URL across all users)
-- - Updates RLS policies for shared article access
--
-- ============================================

-- ============================================
-- STEP 1: CREATE JUNCTION TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS article_users (
  id SERIAL PRIMARY KEY,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  saved_at TIMESTAMP DEFAULT NOW(),

  -- Composite unique constraint: each user can save each article only once
  UNIQUE(article_id, user_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS article_users_article_id_idx ON article_users(article_id);
CREATE INDEX IF NOT EXISTS article_users_user_id_idx ON article_users(user_id);
CREATE INDEX IF NOT EXISTS article_users_saved_at_idx ON article_users(saved_at DESC);

-- Add helpful comment
COMMENT ON TABLE article_users IS 'Junction table for many-to-many relationship between articles and users';

-- ============================================
-- STEP 2: MIGRATE EXISTING DATA
-- ============================================
-- Move existing user_id associations from articles table to article_users table

-- Insert existing article-user relationships into junction table
INSERT INTO article_users (article_id, user_id, saved_at)
SELECT id, user_id, created_at
FROM articles
WHERE user_id IS NOT NULL
ON CONFLICT (article_id, user_id) DO NOTHING;

-- ============================================
-- STEP 3: REMOVE user_id FROM articles TABLE
-- ============================================

-- Drop the old RLS policies that reference user_id on articles
DROP POLICY IF EXISTS "Users can view own articles" ON articles;
DROP POLICY IF EXISTS "Users can insert own articles" ON articles;
DROP POLICY IF EXISTS "Users can update own articles" ON articles;
DROP POLICY IF EXISTS "Users can delete own articles" ON articles;
DROP POLICY IF EXISTS "Authenticated users can view all articles" ON articles;

-- Remove user_id column from articles (no longer needed)
ALTER TABLE articles DROP COLUMN IF EXISTS user_id;

-- ============================================
-- STEP 4: UPDATE RLS POLICIES - articles
-- ============================================

-- SELECT: All authenticated users can read all articles
CREATE POLICY "Authenticated users can view all articles" ON articles
  FOR SELECT
  TO authenticated
  USING (true);

-- INSERT: Any authenticated user can insert articles (URL must be unique)
CREATE POLICY "Authenticated users can insert articles" ON articles
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

-- UPDATE: Users can update articles they've saved
CREATE POLICY "Users can update saved articles" ON articles
  FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM article_users
      WHERE article_users.article_id = articles.id
      AND article_users.user_id = auth.uid()
    )
  );

-- DELETE: Users can delete articles they've saved (and no other user has saved)
CREATE POLICY "Users can delete unsaved articles" ON articles
  FOR DELETE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM article_users
      WHERE article_users.article_id = articles.id
      AND article_users.user_id = auth.uid()
    )
    AND (
      -- Only allow delete if this is the only user who saved it
      SELECT COUNT(*) FROM article_users WHERE article_id = articles.id
    ) = 1
  );

-- ============================================
-- STEP 5: RLS POLICIES - article_users
-- ============================================

-- Enable RLS on junction table
ALTER TABLE article_users ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can see which articles they've saved
CREATE POLICY "Users can view own article saves" ON article_users
  FOR SELECT
  USING (auth.uid() = user_id);

-- INSERT: Users can save articles for themselves
CREATE POLICY "Users can save articles" ON article_users
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- DELETE: Users can unsave their own articles
CREATE POLICY "Users can unsave articles" ON article_users
  FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- STEP 6: CREATE HELPER FUNCTION
-- ============================================

-- Function to get user's saved articles
CREATE OR REPLACE FUNCTION get_user_articles(p_user_id UUID)
RETURNS TABLE (
  id INTEGER,
  title TEXT,
  url TEXT,
  summary_html TEXT,
  created_at TIMESTAMP,
  saved_at TIMESTAMP
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id,
    a.title,
    a.url,
    a.summary_html,
    a.created_at,
    au.saved_at
  FROM articles a
  INNER JOIN article_users au ON a.id = au.article_id
  WHERE au.user_id = p_user_id
  ORDER BY au.saved_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check that article_users table was created
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'article_users'
ORDER BY ordinal_position;

-- Check that user_id was removed from articles
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'articles' AND column_name = 'user_id';
-- Should return 0 rows

-- Check RLS policies on articles
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename = 'articles'
ORDER BY policyname;

-- Check RLS policies on article_users
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename = 'article_users'
ORDER BY policyname;

-- Count article-user associations
SELECT
  COUNT(DISTINCT article_id) as unique_articles,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(*) as total_associations
FROM article_users;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
  RAISE NOTICE '✅ Article-User many-to-many migration completed successfully!';
  RAISE NOTICE '';
  RAISE NOTICE 'Changes made:';
  RAISE NOTICE '1. Created article_users junction table';
  RAISE NOTICE '2. Migrated existing article-user associations';
  RAISE NOTICE '3. Removed user_id column from articles table';
  RAISE NOTICE '4. Updated RLS policies for shared article access';
  RAISE NOTICE '';
  RAISE NOTICE 'New behavior:';
  RAISE NOTICE '- Articles are globally unique by URL';
  RAISE NOTICE '- Multiple users can save the same article';
  RAISE NOTICE '- Each user tracks which articles they have saved';
  RAISE NOTICE '- Users can only update/delete articles they have saved';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Update backend to check for existing URL before processing';
  RAISE NOTICE '2. Update backend to add entry to article_users after processing';
  RAISE NOTICE '3. Update frontend to filter "My Articles" using article_users table';
END $$;
