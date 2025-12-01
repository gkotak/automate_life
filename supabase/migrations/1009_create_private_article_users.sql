-- Create private_article_users junction table
-- Links users to their saved private articles (many-to-many relationship)

CREATE TABLE IF NOT EXISTS private_article_users (
  id SERIAL PRIMARY KEY,
  private_article_id INTEGER NOT NULL REFERENCES private_articles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  saved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Composite unique constraint: each user can save each private article only once
  UNIQUE(private_article_id, user_id)
);

-- Create indexes for performance
CREATE INDEX idx_private_article_users_private_article_id ON private_article_users(private_article_id);
CREATE INDEX idx_private_article_users_user_id ON private_article_users(user_id);
CREATE INDEX idx_private_article_users_saved_at ON private_article_users(saved_at DESC);

-- Add helpful comment
COMMENT ON TABLE private_article_users IS 'Junction table for many-to-many relationship between private articles and users';

-- ============================================
-- RLS POLICIES
-- ============================================

-- Enable RLS
ALTER TABLE private_article_users ENABLE ROW LEVEL SECURITY;

-- SELECT: Users can see which private articles they've saved
-- Note: private_articles table RLS ensures they can only access articles from their org
CREATE POLICY "private_article_users_select_own"
ON private_article_users FOR SELECT
TO authenticated
USING (user_id = auth.uid());

-- INSERT: Users can save private articles for themselves
-- Note: private_articles table RLS ensures they can only save articles from their org
CREATE POLICY "private_article_users_insert_own"
ON private_article_users FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

-- DELETE: Users can unsave their own private articles
CREATE POLICY "private_article_users_delete_own"
ON private_article_users FOR DELETE
TO authenticated
USING (user_id = auth.uid());

-- ============================================
-- HELPER FUNCTION
-- ============================================

-- Function to get user's saved private articles
CREATE OR REPLACE FUNCTION get_user_private_articles(p_user_id UUID)
RETURNS TABLE (
  id INTEGER,
  title TEXT,
  url TEXT,
  summary_text TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  saved_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    pa.id,
    pa.title,
    pa.url,
    pa.summary_text,
    pa.created_at,
    pau.saved_at
  FROM private_articles pa
  INNER JOIN private_article_users pau ON pa.id = pau.private_article_id
  WHERE pau.user_id = p_user_id
  ORDER BY pau.saved_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
