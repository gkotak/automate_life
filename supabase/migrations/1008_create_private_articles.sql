-- Create private_articles table for organization-scoped content
-- This table mirrors the public articles table structure but with organization_id

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

  -- Vector search fields
  embedding vector(1536),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Unique constraint: Same URL can exist across different orgs
  UNIQUE(organization_id, url)
);

-- Create indexes for performance
CREATE INDEX idx_private_articles_organization_id ON private_articles(organization_id);
CREATE INDEX idx_private_articles_created_at ON private_articles(created_at DESC);
CREATE INDEX idx_private_articles_url ON private_articles(url);

-- Vector search index (if using embeddings)
CREATE INDEX idx_private_articles_embedding ON private_articles USING ivfflat(embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

-- Add helpful comment
COMMENT ON TABLE private_articles IS 'Organization-private articles that are not shared globally';
COMMENT ON COLUMN private_articles.organization_id IS 'Organization that owns this private article';

-- ============================================
-- RLS POLICIES
-- ============================================

-- Enable RLS
ALTER TABLE private_articles ENABLE ROW LEVEL SECURITY;

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

CREATE TRIGGER private_articles_updated_at_trigger
  BEFORE UPDATE ON private_articles
  FOR EACH ROW
  EXECUTE FUNCTION update_private_articles_updated_at();
