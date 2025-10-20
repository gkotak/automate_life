-- ============================================================================
-- Row Level Security (RLS) Setup for Article Summarizer
-- ============================================================================
-- This script sets up RLS policies for all tables in the article_summarizer project
--
-- Security Model:
-- - Public users: Can READ articles (view summaries, transcripts, etc.)
-- - Authenticated users: Can INSERT/UPDATE/DELETE articles and manage content
-- - Service role: Full access (used by backend scripts)
--
-- Run this in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/gmwqeqlbfhxffxpsjokf/editor
-- ============================================================================

-- ============================================================================
-- 1. ARTICLES TABLE
-- ============================================================================
-- Articles are public for reading, but only authenticated users can write
ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;

-- Allow anyone to read articles (public access for web app)
CREATE POLICY "Allow public read access to articles"
ON public.articles
FOR SELECT
USING (true);

-- Allow authenticated users to insert articles (for backend processing)
CREATE POLICY "Allow authenticated insert to articles"
ON public.articles
FOR INSERT
WITH CHECK (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- Allow authenticated users to update articles
CREATE POLICY "Allow authenticated update to articles"
ON public.articles
FOR UPDATE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- Allow authenticated users to delete articles
CREATE POLICY "Allow authenticated delete from articles"
ON public.articles
FOR DELETE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- ============================================================================
-- 2. CONTENT_QUEUE TABLE
-- ============================================================================
-- Queue for pending articles to process
ALTER TABLE public.content_queue ENABLE ROW LEVEL SECURITY;

-- Allow public to read queue (for displaying pending items)
CREATE POLICY "Allow public read access to content_queue"
ON public.content_queue
FOR SELECT
USING (true);

-- Allow authenticated users to manage queue
CREATE POLICY "Allow authenticated insert to content_queue"
ON public.content_queue
FOR INSERT
WITH CHECK (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

CREATE POLICY "Allow authenticated update to content_queue"
ON public.content_queue
FOR UPDATE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

CREATE POLICY "Allow authenticated delete from content_queue"
ON public.content_queue
FOR DELETE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- ============================================================================
-- 3. CONTENT_SOURCES TABLE
-- ============================================================================
-- RSS feeds and content sources
ALTER TABLE public.content_sources ENABLE ROW LEVEL SECURITY;

-- Allow public to read sources (for displaying where articles come from)
CREATE POLICY "Allow public read access to content_sources"
ON public.content_sources
FOR SELECT
USING (true);

-- Allow authenticated users to manage sources
CREATE POLICY "Allow authenticated insert to content_sources"
ON public.content_sources
FOR INSERT
WITH CHECK (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

CREATE POLICY "Allow authenticated update to content_sources"
ON public.content_sources
FOR UPDATE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

CREATE POLICY "Allow authenticated delete from content_sources"
ON public.content_sources
FOR DELETE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- ============================================================================
-- 4. CONVERSATIONS TABLE
-- ============================================================================
-- Chat conversations (if you want these private, adjust accordingly)
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

-- Allow public read for conversations (change if you want private chats)
CREATE POLICY "Allow public read access to conversations"
ON public.conversations
FOR SELECT
USING (true);

-- Allow authenticated users to create conversations
CREATE POLICY "Allow authenticated insert to conversations"
ON public.conversations
FOR INSERT
WITH CHECK (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- Allow authenticated users to update conversations
CREATE POLICY "Allow authenticated update to conversations"
ON public.conversations
FOR UPDATE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- Allow authenticated users to delete conversations
CREATE POLICY "Allow authenticated delete from conversations"
ON public.conversations
FOR DELETE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- ============================================================================
-- 5. MESSAGES TABLE
-- ============================================================================
-- Chat messages
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Allow public read for messages (change if you want private chats)
CREATE POLICY "Allow public read access to messages"
ON public.messages
FOR SELECT
USING (true);

-- Allow authenticated users to create messages
CREATE POLICY "Allow authenticated insert to messages"
ON public.messages
FOR INSERT
WITH CHECK (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- Allow authenticated users to update messages
CREATE POLICY "Allow authenticated update to messages"
ON public.messages
FOR UPDATE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- Allow authenticated users to delete messages
CREATE POLICY "Allow authenticated delete from messages"
ON public.messages
FOR DELETE
USING (
  auth.role() = 'authenticated' OR
  auth.role() = 'service_role'
);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to verify RLS is enabled:

-- Check which tables have RLS enabled
SELECT
  schemaname,
  tablename,
  rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('articles', 'content_queue', 'content_sources', 'conversations', 'messages');

-- List all policies
SELECT
  schemaname,
  tablename,
  policyname,
  cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- ============================================================================
-- IMPORTANT NOTES
-- ============================================================================
-- 1. Your Python scripts use SUPABASE_ANON_KEY which has the 'anon' role
--    This means they won't be able to INSERT/UPDATE/DELETE with current policies
--
-- 2. You have two options:
--
--    OPTION A (Recommended): Use SUPABASE_SERVICE_ROLE_KEY in backend scripts
--    - Update .env.local to use service role key for article_summarizer
--    - Service role bypasses RLS and has full access
--    - Keep anon key for frontend (Next.js web app)
--
--    OPTION B: Allow anon role to write (less secure)
--    - Modify policies to allow auth.role() = 'anon' for INSERT/UPDATE/DELETE
--    - This means anyone with your anon key can modify data
--    - Only do this if you keep the app private/localhost
--
-- 3. Current setup:
--    - Frontend (Next.js): Uses anon key → Can READ all tables ✓
--    - Backend (Python): Uses anon key → Cannot WRITE ✗
--
-- 4. To fix backend, change your Python scripts to use service_role_key:
--    supabase = create_client(
--        os.getenv('SUPABASE_URL'),
--        os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Changed from SUPABASE_ANON_KEY
--    )
--
-- ============================================================================
