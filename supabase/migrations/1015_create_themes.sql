-- =====================================================
-- Migration: 1015_create_themes
-- Purpose: Create themes and themed insights tables for organizational analysis
-- Scope: Private articles only (themes are org-specific)
-- =====================================================

-- Themes table: Organization-level categories for strategic analysis
CREATE TABLE IF NOT EXISTS themes (
  id SERIAL PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Each theme name must be unique within an organization
  UNIQUE(organization_id, name)
);

-- Index for efficient org-based lookups
CREATE INDEX idx_themes_organization_id ON themes(organization_id);

-- Themed insights table: AI-generated insights linked to themes
CREATE TABLE IF NOT EXISTS private_article_themed_insights (
  id SERIAL PRIMARY KEY,
  private_article_id INTEGER NOT NULL REFERENCES private_articles(id) ON DELETE CASCADE,
  theme_id INTEGER NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
  insight_text TEXT NOT NULL,
  timestamp_seconds INTEGER,
  time_formatted TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient lookups
CREATE INDEX idx_themed_insights_private_article_id ON private_article_themed_insights(private_article_id);
CREATE INDEX idx_themed_insights_theme_id ON private_article_themed_insights(theme_id);

-- Enable Row Level Security
ALTER TABLE themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE private_article_themed_insights ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- RLS Policies for themes
-- Users can access themes for their organization
-- =====================================================

CREATE POLICY "themes_select" ON themes
  FOR SELECT TO authenticated
  USING (organization_id IN (
    SELECT organization_id FROM users WHERE id = (SELECT auth.uid())
  ));

CREATE POLICY "themes_insert" ON themes
  FOR INSERT TO authenticated
  WITH CHECK (organization_id IN (
    SELECT organization_id FROM users WHERE id = (SELECT auth.uid())
  ));

CREATE POLICY "themes_update" ON themes
  FOR UPDATE TO authenticated
  USING (organization_id IN (
    SELECT organization_id FROM users WHERE id = (SELECT auth.uid())
  ));

CREATE POLICY "themes_delete" ON themes
  FOR DELETE TO authenticated
  USING (organization_id IN (
    SELECT organization_id FROM users WHERE id = (SELECT auth.uid())
  ));

-- =====================================================
-- RLS Policies for private_article_themed_insights
-- Access is derived via theme's organization
-- =====================================================

CREATE POLICY "themed_insights_select" ON private_article_themed_insights
  FOR SELECT TO authenticated
  USING (theme_id IN (
    SELECT id FROM themes WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (SELECT auth.uid())
    )
  ));

CREATE POLICY "themed_insights_insert" ON private_article_themed_insights
  FOR INSERT TO authenticated
  WITH CHECK (theme_id IN (
    SELECT id FROM themes WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (SELECT auth.uid())
    )
  ));

CREATE POLICY "themed_insights_delete" ON private_article_themed_insights
  FOR DELETE TO authenticated
  USING (theme_id IN (
    SELECT id FROM themes WHERE organization_id IN (
      SELECT organization_id FROM users WHERE id = (SELECT auth.uid())
    )
  ));

-- =====================================================
-- Comments for documentation
-- =====================================================

COMMENT ON TABLE themes IS 'Organization-level categories for strategic content analysis (e.g., Competition, International Expansion)';
COMMENT ON COLUMN themes.name IS 'Theme name, unique within organization';
COMMENT ON TABLE private_article_themed_insights IS 'AI-generated insights linked to organizational themes';
COMMENT ON COLUMN private_article_themed_insights.insight_text IS 'The insight text relevant to the theme';
COMMENT ON COLUMN private_article_themed_insights.timestamp_seconds IS 'Optional timestamp in seconds if insight ties to specific transcript moment';
COMMENT ON COLUMN private_article_themed_insights.time_formatted IS 'Human-readable timestamp format (e.g., 5:00, 1:23:45)';
