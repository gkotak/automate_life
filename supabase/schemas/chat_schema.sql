-- Chat Interface Database Schema
-- Creates tables for conversations and messages to support the chat interface

-- ============================================
-- CONVERSATIONS TABLE
-- ============================================
-- Stores chat sessions/conversations
CREATE TABLE IF NOT EXISTS conversations (
  id BIGSERIAL PRIMARY KEY,
  title TEXT, -- Auto-generated from first message or user-provided
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for listing conversations by most recent
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);

-- ============================================
-- MESSAGES TABLE
-- ============================================
-- Stores individual messages within conversations
CREATE TABLE IF NOT EXISTS messages (
  id BIGSERIAL PRIMARY KEY,
  conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  sources JSONB, -- Array of article sources: [{id: 60, title: "...", similarity: 0.85, url: "..."}]
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fetching messages by conversation (most common query)
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- Index for ordering messages within a conversation
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Composite index for efficient conversation message fetching
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created ON messages(conversation_id, created_at);

-- ============================================
-- TRIGGER: UPDATE CONVERSATION TIMESTAMP
-- ============================================
-- Automatically update conversations.updated_at when a new message is added
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE conversations
  SET updated_at = NOW()
  WHERE id = NEW.conversation_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if it exists (for idempotency)
DROP TRIGGER IF EXISTS trigger_update_conversation_timestamp ON messages;

-- Create trigger
CREATE TRIGGER trigger_update_conversation_timestamp
  AFTER INSERT ON messages
  FOR EACH ROW
  EXECUTE FUNCTION update_conversation_timestamp();

-- ============================================
-- COMMENTS (Documentation)
-- ============================================
COMMENT ON TABLE conversations IS 'Stores chat sessions/conversations';
COMMENT ON TABLE messages IS 'Stores individual messages within conversations';
COMMENT ON COLUMN messages.role IS 'Message sender: user, assistant, or system';
COMMENT ON COLUMN messages.sources IS 'JSON array of article sources that informed the assistant response';

-- ============================================
-- EXAMPLE QUERIES
-- ============================================
-- List all conversations (most recent first):
-- SELECT * FROM conversations ORDER BY updated_at DESC LIMIT 50;

-- Get conversation with all messages:
-- SELECT c.*, json_agg(m ORDER BY m.created_at) as messages
-- FROM conversations c
-- LEFT JOIN messages m ON m.conversation_id = c.id
-- WHERE c.id = 1
-- GROUP BY c.id;

-- Create new conversation:
-- INSERT INTO conversations (title) VALUES ('My First Chat') RETURNING *;

-- Add message to conversation:
-- INSERT INTO messages (conversation_id, role, content, sources)
-- VALUES (1, 'user', 'What are the key insights?', NULL) RETURNING *;

-- Delete old conversations (keep last 100):
-- DELETE FROM conversations
-- WHERE id NOT IN (
--   SELECT id FROM conversations ORDER BY updated_at DESC LIMIT 100
-- );
