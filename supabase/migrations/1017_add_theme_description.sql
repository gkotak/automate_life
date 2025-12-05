-- =====================================================
-- Migration: 1017_add_theme_description
-- Purpose: Add description field to themes for better context in AI analysis
-- =====================================================

-- Add description column to themes table
ALTER TABLE themes ADD COLUMN IF NOT EXISTS description TEXT;

-- Add comment for documentation
COMMENT ON COLUMN themes.description IS 'Optional description providing context for the theme (e.g., competitor names, specific focus areas). Used to guide AI analysis.';
