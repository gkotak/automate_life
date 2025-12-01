-- =====================================================
-- Migration: 1014_create_folder_articles
-- Purpose: Create junction tables for folder-article relationships
-- Note: Two tables needed since public/private articles are separate
-- =====================================================

-- Junction table for public articles
CREATE TABLE IF NOT EXISTS folder_articles (
  id SERIAL PRIMARY KEY,
  folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
  article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- Prevent duplicate entries
  UNIQUE(folder_id, article_id)
);

-- Indexes for efficient lookups
CREATE INDEX idx_folder_articles_folder_id ON folder_articles(folder_id);
CREATE INDEX idx_folder_articles_article_id ON folder_articles(article_id);
CREATE INDEX idx_folder_articles_added_at ON folder_articles(added_at DESC);

-- Junction table for private articles
CREATE TABLE IF NOT EXISTS folder_private_articles (
  id SERIAL PRIMARY KEY,
  folder_id INTEGER NOT NULL REFERENCES folders(id) ON DELETE CASCADE,
  private_article_id INTEGER NOT NULL REFERENCES private_articles(id) ON DELETE CASCADE,
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- Prevent duplicate entries
  UNIQUE(folder_id, private_article_id)
);

-- Indexes for efficient lookups
CREATE INDEX idx_folder_private_articles_folder_id ON folder_private_articles(folder_id);
CREATE INDEX idx_folder_private_articles_private_article_id ON folder_private_articles(private_article_id);
CREATE INDEX idx_folder_private_articles_added_at ON folder_private_articles(added_at DESC);

-- Enable Row Level Security
ALTER TABLE folder_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE folder_private_articles ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS Policies for folder_articles
-- Access is derived from the folder's organization
-- =====================================================

CREATE POLICY "folder_articles_select" ON folder_articles
  FOR SELECT TO authenticated
  USING (folder_id IN (
    SELECT id FROM folders WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (select auth.uid())
    )
  ));

CREATE POLICY "folder_articles_insert" ON folder_articles
  FOR INSERT TO authenticated
  WITH CHECK (folder_id IN (
    SELECT id FROM folders WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (select auth.uid())
    )
  ));

CREATE POLICY "folder_articles_delete" ON folder_articles
  FOR DELETE TO authenticated
  USING (folder_id IN (
    SELECT id FROM folders WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (select auth.uid())
    )
  ));

-- =====================================================
-- RLS Policies for folder_private_articles
-- Same pattern as folder_articles
-- =====================================================

CREATE POLICY "folder_private_articles_select" ON folder_private_articles
  FOR SELECT TO authenticated
  USING (folder_id IN (
    SELECT id FROM folders WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (select auth.uid())
    )
  ));

CREATE POLICY "folder_private_articles_insert" ON folder_private_articles
  FOR INSERT TO authenticated
  WITH CHECK (folder_id IN (
    SELECT id FROM folders WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (select auth.uid())
    )
  ));

CREATE POLICY "folder_private_articles_delete" ON folder_private_articles
  FOR DELETE TO authenticated
  USING (folder_id IN (
    SELECT id FROM folders WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (select auth.uid())
    )
  ));

-- Comments for documentation
COMMENT ON TABLE folder_articles IS 'Junction table linking folders to public articles';
COMMENT ON TABLE folder_private_articles IS 'Junction table linking folders to private articles';
COMMENT ON COLUMN folder_articles.added_at IS 'When the article was added to the folder';
COMMENT ON COLUMN folder_private_articles.added_at IS 'When the private article was added to the folder';
