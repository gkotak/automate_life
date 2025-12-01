-- Combined migration script to run in Supabase SQL Editor
-- This combines migrations 1008, 1009, and 1012

-- ============================================
-- From 1012: Fix embedding dimension first
-- ============================================

-- Check if private_articles exists and fix embedding dimension
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'private_articles') THEN
    ALTER TABLE private_articles ALTER COLUMN embedding TYPE vector(384);
    RAISE NOTICE 'Updated private_articles embedding dimension to 384';
  END IF;
END $$;

-- Then ensure the table is created with correct dimension if it doesn't exist
-- (This is from migration 1008 but with corrected embedding dimension)

CREATE TABLE IF NOT EXISTS private_articles (
  id SERIAL PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

  -- Core fields (same as articles table)
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  source TEXT,
  summary_text TEXT,
  transcript_text TEXT,
  original_article_text TEXT,
  content_source TEXT,
  video_id TEXT,
  audio_url TEXT,
  platform TEXT,
  tags TEXT[],

  -- Structured data (JSON fields)
  key_insights JSONB,
  quotes JSONB,
  images JSONB,
  video_frames JSONB,

  -- Metadata
  duration_minutes INTEGER,
  word_count INTEGER,
  topics JSONB,

  -- Vector search fields (384 dimensions for text-embedding-3-small)
  embedding vector(384),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Unique constraint: Same URL can exist across different orgs
  UNIQUE(organization_id, url)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_private_articles_organization_id ON private_articles(organization_id);
CREATE INDEX IF NOT EXISTS idx_private_articles_created_at ON private_articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_private_articles_url ON private_articles(url);

-- Vector search index (if using embeddings)
CREATE INDEX IF NOT EXISTS idx_private_articles_embedding ON private_articles USING ivfflat(embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

-- Add helpful comment
COMMENT ON TABLE private_articles IS 'Organization-private articles that are not shared globally';
COMMENT ON COLUMN private_articles.organization_id IS 'Organization that owns this private article';
COMMENT ON COLUMN private_articles.embedding IS 'OpenAI text-embedding-3-small vector (384 dimensions)';

-- ============================================
-- RLS POLICIES
-- ============================================

-- Enable RLS
ALTER TABLE private_articles ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "private_articles_select_own_org" ON private_articles;
DROP POLICY IF EXISTS "private_articles_insert_own_org" ON private_articles;
DROP POLICY IF EXISTS "private_articles_update_own_org" ON private_articles;
DROP POLICY IF EXISTS "private_articles_delete_own_org" ON private_articles;

-- SELECT: Users can only read private articles from their organization
CREATE POLICY "private_articles_select_own_org"
ON private_articles FOR SELECT
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = auth.uid()
  )
);

-- INSERT: Users can create private articles for their organization
CREATE POLICY "private_articles_insert_own_org"
ON private_articles FOR INSERT
TO authenticated
WITH CHECK (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = auth.uid()
  )
);

-- UPDATE: Users can update private articles from their organization
CREATE POLICY "private_articles_update_own_org"
ON private_articles FOR UPDATE
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = auth.uid()
  )
);

-- DELETE: Users can delete private articles from their organization
CREATE POLICY "private_articles_delete_own_org"
ON private_articles FOR DELETE
TO authenticated
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = auth.uid()
  )
);

-- ============================================
-- TRIGGERS
-- ============================================

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_private_articles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS private_articles_updated_at_trigger ON private_articles;

CREATE TRIGGER private_articles_updated_at_trigger
  BEFORE UPDATE ON private_articles
  FOR EACH ROW
  EXECUTE FUNCTION update_private_articles_updated_at();

-- ============================================
-- From 1009: Create private_article_users junction table
-- ============================================

CREATE TABLE IF NOT EXISTS private_article_users (
  id SERIAL PRIMARY KEY,
  private_article_id INTEGER NOT NULL REFERENCES private_articles(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  saved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Unique constraint: User can only save a private article once
  UNIQUE(private_article_id, user_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_private_article_users_private_article_id ON private_article_users(private_article_id);
CREATE INDEX IF NOT EXISTS idx_private_article_users_user_id ON private_article_users(user_id);
CREATE INDEX IF NOT EXISTS idx_private_article_users_saved_at ON private_article_users(saved_at DESC);

COMMENT ON TABLE private_article_users IS 'Junction table tracking which users have saved which private articles';

-- ============================================
-- RLS POLICIES for private_article_users
-- ============================================

ALTER TABLE private_article_users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "private_article_users_select_own" ON private_article_users;
DROP POLICY IF EXISTS "private_article_users_insert_own" ON private_article_users;
DROP POLICY IF EXISTS "private_article_users_delete_own" ON private_article_users;

-- SELECT: Users can view their own saved private articles
CREATE POLICY "private_article_users_select_own"
ON private_article_users FOR SELECT
TO authenticated
USING (user_id = auth.uid());

-- INSERT: Users can save private articles for themselves
CREATE POLICY "private_article_users_insert_own"
ON private_article_users FOR INSERT
TO authenticated
WITH CHECK (user_id = auth.uid());

-- DELETE: Users can remove private articles from their saved list
CREATE POLICY "private_article_users_delete_own"
ON private_article_users FOR DELETE
TO authenticated
USING (user_id = auth.uid());
