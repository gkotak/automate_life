-- ============================================
-- User Authentication Migration
-- ============================================
-- This script adds user authentication support to the Automate Life database
--
-- INSTRUCTIONS:
-- 1. Open Supabase Dashboard → SQL Editor
-- 2. Copy and paste this entire script
-- 3. Click "Run" to execute
--
-- WHAT THIS DOES:
-- - Adds user_id column to articles table
-- - Adds user_id column to conversations table
-- - Updates RLS policies to enforce user ownership
-- - Creates indexes for performance
--
-- ROLLBACK:
-- If you need to undo this migration, see the rollback script at the bottom
-- ============================================

-- ============================================
-- STEP 1: ADD user_id COLUMN TO ARTICLES
-- ============================================

-- Add user_id column (nullable initially to allow existing data)
ALTER TABLE articles
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Create index for query performance
CREATE INDEX IF NOT EXISTS articles_user_id_idx ON articles(user_id);

-- Add helpful comment
COMMENT ON COLUMN articles.user_id IS 'Owner of the article - references auth.users. NULL for articles created before authentication was enabled.';

-- ============================================
-- STEP 2: ADD user_id COLUMN TO CONVERSATIONS
-- ============================================

-- Add user_id column to conversations (for per-user chat history)
ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;

-- Create index for query performance
CREATE INDEX IF NOT EXISTS conversations_user_id_idx ON conversations(user_id);

-- Add helpful comment
COMMENT ON COLUMN conversations.user_id IS 'Owner of the conversation - references auth.users. NULL for conversations created before authentication was enabled.';

-- ============================================
-- STEP 3: UPDATE RLS POLICIES FOR ARTICLES
-- ============================================

-- Drop old permissive policies (that allowed all operations)
DROP POLICY IF EXISTS "Users can view all articles" ON articles;
DROP POLICY IF EXISTS "Users can insert articles" ON articles;
DROP POLICY IF EXISTS "Users can update articles" ON articles;
DROP POLICY IF EXISTS "Users can delete articles" ON articles;

-- Create new user-scoped policies

-- SELECT: Users can only view their own articles
CREATE POLICY "Users can view own articles" ON articles
  FOR SELECT
  USING (auth.uid() = user_id);

-- INSERT: Users can only insert articles with their own user_id
CREATE POLICY "Users can insert own articles" ON articles
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- UPDATE: Users can only update their own articles
CREATE POLICY "Users can update own articles" ON articles
  FOR UPDATE
  USING (auth.uid() = user_id);

-- DELETE: Users can only delete their own articles
CREATE POLICY "Users can delete own articles" ON articles
  FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- STEP 4: UPDATE RLS POLICIES FOR CONVERSATIONS
-- ============================================

-- Drop old permissive policies
DROP POLICY IF EXISTS "Users can view all conversations" ON conversations;
DROP POLICY IF EXISTS "Users can insert conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update conversations" ON conversations;
DROP POLICY IF EXISTS "Users can delete conversations" ON conversations;

-- Create new user-scoped policies

-- SELECT: Users can only view their own conversations
CREATE POLICY "Users can view own conversations" ON conversations
  FOR SELECT
  USING (auth.uid() = user_id);

-- INSERT: Users can only insert conversations with their own user_id
CREATE POLICY "Users can insert own conversations" ON conversations
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- UPDATE: Users can only update their own conversations
CREATE POLICY "Users can update own conversations" ON conversations
  FOR UPDATE
  USING (auth.uid() = user_id);

-- DELETE: Users can only delete their own conversations
CREATE POLICY "Users can delete own conversations" ON conversations
  FOR DELETE
  USING (auth.uid() = user_id);

-- ============================================
-- STEP 5: UPDATE RLS POLICIES FOR MESSAGES
-- ============================================
-- Messages should be accessible if the user owns the parent conversation

-- Drop old policies if they exist
DROP POLICY IF EXISTS "Users can view all messages" ON messages;
DROP POLICY IF EXISTS "Users can insert messages" ON messages;
DROP POLICY IF EXISTS "Users can update messages" ON messages;
DROP POLICY IF EXISTS "Users can delete messages" ON messages;

-- SELECT: Users can view messages from their own conversations
CREATE POLICY "Users can view own messages" ON messages
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND conversations.user_id = auth.uid()
    )
  );

-- INSERT: Users can insert messages into their own conversations
CREATE POLICY "Users can insert own messages" ON messages
  FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND conversations.user_id = auth.uid()
    )
  );

-- UPDATE: Users can update messages in their own conversations
CREATE POLICY "Users can update own messages" ON messages
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND conversations.user_id = auth.uid()
    )
  );

-- DELETE: Users can delete messages from their own conversations
CREATE POLICY "Users can delete own messages" ON messages
  FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM conversations
      WHERE conversations.id = messages.conversation_id
      AND conversations.user_id = auth.uid()
    )
  );

-- ============================================
-- STEP 6: HANDLE EXISTING DATA (OPTIONAL)
-- ============================================

-- Option A: Assign existing articles to a system user
-- Uncomment the lines below if you want to preserve existing articles
-- Replace 'YOUR-USER-UUID' with your actual user UUID from auth.users

/*
-- First, get your user UUID:
-- SELECT id FROM auth.users WHERE email = 'your-email@example.com';

-- Then update existing articles:
UPDATE articles
SET user_id = 'YOUR-USER-UUID'  -- Replace with actual UUID
WHERE user_id IS NULL;

-- And existing conversations:
UPDATE conversations
SET user_id = 'YOUR-USER-UUID'  -- Replace with actual UUID
WHERE user_id IS NULL;
*/

-- Option B: Delete existing test data
-- Uncomment the lines below if you want to delete unowned articles/conversations

/*
DELETE FROM articles WHERE user_id IS NULL;
DELETE FROM conversations WHERE user_id IS NULL;
*/

-- ============================================
-- STEP 7: MAKE user_id REQUIRED (OPTIONAL - DO LATER)
-- ============================================

-- ⚠️ WARNING: Only run this after all existing data has been migrated!
-- ⚠️ This will prevent inserting articles/conversations without user_id

-- Uncomment when ready to enforce user_id:

/*
ALTER TABLE articles ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE conversations ALTER COLUMN user_id SET NOT NULL;
*/

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check that user_id column was added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'articles' AND column_name = 'user_id';

-- Check RLS policies on articles
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE tablename = 'articles';

-- Count articles by user (after migration)
SELECT
  COALESCE(user_id::text, 'NULL') as user_id,
  COUNT(*) as article_count
FROM articles
GROUP BY user_id
ORDER BY article_count DESC;

-- ============================================
-- SUCCESS MESSAGE
-- ============================================

DO $$
BEGIN
  RAISE NOTICE '✅ User authentication migration completed successfully!';
  RAISE NOTICE '';
  RAISE NOTICE 'Next steps:';
  RAISE NOTICE '1. Enable Email auth in Supabase Dashboard → Authentication → Providers';
  RAISE NOTICE '2. Implement frontend auth UI (login/signup pages)';
  RAISE NOTICE '3. Test with a new user account';
  RAISE NOTICE '4. When ready, make user_id required (see STEP 7)';
  RAISE NOTICE '';
  RAISE NOTICE 'Current state:';
  RAISE NOTICE '- user_id column added (nullable)';
  RAISE NOTICE '- RLS policies updated to user-scoped';
  RAISE NOTICE '- Indexes created for performance';
END $$;

-- ============================================
-- ROLLBACK SCRIPT (IF NEEDED)
-- ============================================

/*
-- ⚠️ WARNING: This will remove all authentication!
-- ⚠️ Only use if you need to completely undo this migration

-- Restore permissive policies on articles
DROP POLICY IF EXISTS "Users can view own articles" ON articles;
DROP POLICY IF EXISTS "Users can insert own articles" ON articles;
DROP POLICY IF EXISTS "Users can update own articles" ON articles;
DROP POLICY IF EXISTS "Users can delete own articles" ON articles;

CREATE POLICY "Users can view all articles" ON articles FOR SELECT USING (true);
CREATE POLICY "Users can insert articles" ON articles FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update articles" ON articles FOR UPDATE USING (true);
CREATE POLICY "Users can delete articles" ON articles FOR DELETE USING (true);

-- Restore permissive policies on conversations
DROP POLICY IF EXISTS "Users can view own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can delete own conversations" ON conversations;

CREATE POLICY "Users can view all conversations" ON conversations FOR SELECT USING (true);
CREATE POLICY "Users can insert conversations" ON conversations FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update conversations" ON conversations FOR UPDATE USING (true);
CREATE POLICY "Users can delete conversations" ON conversations FOR DELETE USING (true);

-- Restore permissive policies on messages
DROP POLICY IF EXISTS "Users can view own messages" ON messages;
DROP POLICY IF EXISTS "Users can insert own messages" ON messages;
DROP POLICY IF EXISTS "Users can update own messages" ON messages;
DROP POLICY IF EXISTS "Users can delete own messages" ON messages;

CREATE POLICY "Users can view all messages" ON messages FOR SELECT USING (true);
CREATE POLICY "Users can insert messages" ON messages FOR INSERT WITH CHECK (true);
CREATE POLICY "Users can update messages" ON messages FOR UPDATE USING (true);
CREATE POLICY "Users can delete messages" ON messages FOR DELETE USING (true);

-- Remove user_id columns
DROP INDEX IF EXISTS articles_user_id_idx;
DROP INDEX IF EXISTS conversations_user_id_idx;

ALTER TABLE articles DROP COLUMN IF EXISTS user_id;
ALTER TABLE conversations DROP COLUMN IF EXISTS user_id;

RAISE NOTICE '⚠️ Rollback completed - authentication removed';
*/
