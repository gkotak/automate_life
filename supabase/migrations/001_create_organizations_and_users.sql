-- Migration: Create Organizations and Users Profile Tables
-- Description: Add multi-tenancy support with organizations and user roles
-- Run this in Supabase SQL Editor

-- ============================================================================
-- STEP 1: Create Organizations Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  billing_id TEXT, -- For future Stripe/payment integration
  metadata JSONB DEFAULT '{}', -- Custom org-specific settings and configuration
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add index for faster queries
CREATE INDEX idx_organizations_billing_id ON organizations(billing_id) WHERE billing_id IS NOT NULL;

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_organizations_updated_at
  BEFORE UPDATE ON organizations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 2: Create Users Profile Table (extends auth.users)
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('admin', 'member')),
  display_name TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for faster queries
CREATE INDEX idx_users_organization_id ON users(organization_id);
CREATE INDEX idx_users_role ON users(role);

-- Add trigger to update updated_at timestamp
CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 3: Enable Row Level Security (RLS)
-- ============================================================================

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 4: Create RLS Policies for Organizations
-- ============================================================================

-- Users can read their own organization
CREATE POLICY "Users can read their own organization"
ON organizations FOR SELECT
USING (
  id IN (SELECT organization_id FROM users WHERE id = auth.uid())
);

-- Users can update their own organization if they are admin
CREATE POLICY "Admins can update their organization"
ON organizations FOR UPDATE
USING (
  id IN (
    SELECT organization_id FROM users
    WHERE id = auth.uid() AND role = 'admin'
  )
);

-- ============================================================================
-- STEP 5: Create RLS Policies for Users
-- ============================================================================

-- Users can read their own profile
CREATE POLICY "Users can read their own profile"
ON users FOR SELECT
USING (id = auth.uid());

-- Users can read other users in their organization
CREATE POLICY "Users can read org members"
ON users FOR SELECT
USING (
  organization_id IN (
    SELECT organization_id FROM users WHERE id = auth.uid()
  )
);

-- Users can update their own profile (limited fields)
CREATE POLICY "Users can update their own profile"
ON users FOR UPDATE
USING (id = auth.uid());

-- Admins can update other users in their organization
CREATE POLICY "Admins can update org members"
ON users FOR UPDATE
USING (
  organization_id IN (
    SELECT organization_id FROM users
    WHERE id = auth.uid() AND role = 'admin'
  )
);

-- ============================================================================
-- STEP 6: Create helper function to get user's organization
-- ============================================================================

CREATE OR REPLACE FUNCTION get_user_organization_id()
RETURNS UUID AS $$
BEGIN
  RETURN (SELECT organization_id FROM users WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================================
-- STEP 7: Create helper function to check if user is admin
-- ============================================================================

CREATE OR REPLACE FUNCTION is_user_admin()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN (SELECT role = 'admin' FROM users WHERE id = auth.uid());
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================================
-- NOTES:
-- - After running this, you need to run the backfill script (002_backfill_existing_users.sql)
-- - Then run the script to add organization_id to existing tables (003_add_organization_id_to_tables.sql)
-- ============================================================================
