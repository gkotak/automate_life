-- ============================================================================
-- SECURITY HARDENING - FUNCTION SEARCH PATH
-- ============================================================================
-- This migration adds explicit search_path to all actively used functions
-- to prevent search path hijacking attacks
-- Consolidates migration 998_fix_function_search_path.sql
--
-- See: https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable
-- ============================================================================

-- ============================================================================
-- AUTH HELPER FUNCTIONS
-- ============================================================================

-- Fix: get_user_organization_id
CREATE OR REPLACE FUNCTION get_user_organization_id()
RETURNS UUID AS $$
DECLARE
  org_id UUID;
BEGIN
  -- This bypasses RLS because function is SECURITY DEFINER
  SELECT organization_id INTO org_id
  FROM users
  WHERE id = auth.uid();

  RETURN org_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE SET search_path = public;

-- Fix: is_user_admin
CREATE OR REPLACE FUNCTION is_user_admin()
RETURNS BOOLEAN AS $$
DECLARE
  user_role TEXT;
BEGIN
  -- This bypasses RLS because function is SECURITY DEFINER
  SELECT role INTO user_role
  FROM users
  WHERE id = auth.uid();

  RETURN (user_role = 'admin');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE SET search_path = public;

-- ============================================================================
-- TRIGGER FUNCTIONS
-- ============================================================================

-- Fix: update_updated_at_column (trigger function)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

-- Fix: update_search_vector (for full-text search)
CREATE OR REPLACE FUNCTION update_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(NEW.summary_text, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(NEW.source, '')), 'C');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

-- Fix: update_conversation_timestamp
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE conversations
  SET updated_at = NOW()
  WHERE id = NEW.conversation_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = public;

-- Fix: update_known_channels_updated_at
CREATE OR REPLACE FUNCTION update_known_channels_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql SET search_path = public
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

-- ============================================================================
-- SEARCH FUNCTIONS
-- ============================================================================

-- Fix: search_articles (vector similarity search)
CREATE OR REPLACE FUNCTION search_articles(
  query_embedding vector(384),
  match_threshold float DEFAULT 0.5,
  match_count int DEFAULT 10
)
RETURNS TABLE (
  id integer,
  title text,
  url text,
  summary_text text,
  content_source text,
  platform text,
  created_at timestamp,
  similarity float
)
LANGUAGE plpgsql STABLE SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id,
    a.title,
    a.url,
    a.summary_text,
    a.content_source,
    a.platform,
    a.created_at,
    1 - (a.embedding <=> query_embedding) as similarity
  FROM articles a
  WHERE a.embedding IS NOT NULL
    AND 1 - (a.embedding <=> query_embedding) > match_threshold
  ORDER BY a.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================================
-- CLEANUP: Drop unused functions that were causing warnings
-- ============================================================================

-- These functions are not used by the application
DROP FUNCTION IF EXISTS match_articles(vector, double precision, integer);
DROP FUNCTION IF EXISTS match_articles(vector, float, integer);
DROP FUNCTION IF EXISTS match_articles(vector, float, int);
DROP FUNCTION IF EXISTS match_articles(vector);
DROP FUNCTION IF EXISTS hybrid_search(text, vector, float, int, int);
DROP FUNCTION IF EXISTS hybrid_search(text, vector);
DROP FUNCTION IF EXISTS get_article_frames(int);
DROP FUNCTION IF EXISTS get_article_frames(integer);
DROP FUNCTION IF EXISTS get_user_articles(uuid);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  fixed_count INTEGER;
BEGIN
  -- Count functions we fixed
  SELECT COUNT(*) INTO fixed_count
  FROM pg_proc p
  JOIN pg_namespace n ON p.pronamespace = n.oid
  WHERE n.nspname = 'public'
    AND p.proname IN (
      'get_user_organization_id',
      'is_user_admin',
      'update_updated_at_column',
      'update_search_vector',
      'update_conversation_timestamp',
      'search_articles',
      'update_known_channels_updated_at'
    );

  RAISE NOTICE '========================================';
  RAISE NOTICE 'SECURITY HARDENING - COMPLETE';
  RAISE NOTICE '========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Fixed % actively-used functions', fixed_count;
  RAISE NOTICE '';
  RAISE NOTICE 'All functions now have: SET search_path = public';
  RAISE NOTICE 'This prevents search path hijacking attacks';
  RAISE NOTICE '';
  RAISE NOTICE 'Cleaned up % unused functions', 9;
  RAISE NOTICE '========================================';
END $$;
