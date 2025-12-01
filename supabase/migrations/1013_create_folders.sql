-- =====================================================
-- Migration: 1013_create_folders
-- Purpose: Create folders table for organizing articles
-- Access: Organization-level (all org users have full access)
-- =====================================================

CREATE TABLE IF NOT EXISTS folders (
  id SERIAL PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

  -- Folder name must be unique within organization
  UNIQUE(organization_id, name)
);

-- Indexes for efficient lookups
CREATE INDEX idx_folders_organization_id ON folders(organization_id);
CREATE INDEX idx_folders_name ON folders(name);
CREATE INDEX idx_folders_created_at ON folders(created_at DESC);

-- Auto-update timestamp trigger (reuse existing function if available)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'update_updated_at_column') THEN
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $func$
    BEGIN
      NEW.updated_at = NOW();
      RETURN NEW;
    END;
    $func$ LANGUAGE plpgsql;
  END IF;
END
$$;

CREATE TRIGGER folders_updated_at
  BEFORE UPDATE ON folders
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security
ALTER TABLE folders ENABLE ROW LEVEL SECURITY;

-- RLS Policies (organization-level access)
-- All users in the same organization can read all folders
CREATE POLICY "folders_select_own_org" ON folders
  FOR SELECT TO authenticated
  USING (organization_id IN (SELECT organization_id FROM users WHERE id = (select auth.uid())));

-- All users in the same organization can create folders
CREATE POLICY "folders_insert_own_org" ON folders
  FOR INSERT TO authenticated
  WITH CHECK (organization_id IN (SELECT organization_id FROM users WHERE id = (select auth.uid())));

-- All users in the same organization can update folders
CREATE POLICY "folders_update_own_org" ON folders
  FOR UPDATE TO authenticated
  USING (organization_id IN (SELECT organization_id FROM users WHERE id = (select auth.uid())));

-- All users in the same organization can delete folders
CREATE POLICY "folders_delete_own_org" ON folders
  FOR DELETE TO authenticated
  USING (organization_id IN (SELECT organization_id FROM users WHERE id = (select auth.uid())));

-- Comments for documentation
COMMENT ON TABLE folders IS 'Folders for organizing articles (both public and private). Organization-scoped access.';
COMMENT ON COLUMN folders.organization_id IS 'Organization that owns this folder';
COMMENT ON COLUMN folders.name IS 'Folder name (unique within organization)';
COMMENT ON COLUMN folders.description IS 'Optional description of the folder';
