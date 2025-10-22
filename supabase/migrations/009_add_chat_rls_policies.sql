-- Enable RLS on conversations and messages tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow public read access to conversations" ON conversations;
DROP POLICY IF EXISTS "Allow public insert access to conversations" ON conversations;
DROP POLICY IF EXISTS "Allow public update access to conversations" ON conversations;
DROP POLICY IF EXISTS "Allow public delete access to conversations" ON conversations;

DROP POLICY IF EXISTS "Allow public read access to messages" ON messages;
DROP POLICY IF EXISTS "Allow public insert access to messages" ON messages;
DROP POLICY IF EXISTS "Allow public update access to messages" ON messages;
DROP POLICY IF EXISTS "Allow public delete access to messages" ON messages;

-- Create policies to allow public access (for MVP)
-- Note: In production, these should be restricted to authenticated users

-- Conversations policies
CREATE POLICY "Allow public read access to conversations"
ON conversations FOR SELECT
USING (true);

CREATE POLICY "Allow public insert access to conversations"
ON conversations FOR INSERT
WITH CHECK (true);

CREATE POLICY "Allow public update access to conversations"
ON conversations FOR UPDATE
USING (true);

CREATE POLICY "Allow public delete access to conversations"
ON conversations FOR DELETE
USING (true);

-- Messages policies
CREATE POLICY "Allow public read access to messages"
ON messages FOR SELECT
USING (true);

CREATE POLICY "Allow public insert access to messages"
ON messages FOR INSERT
WITH CHECK (true);

CREATE POLICY "Allow public update access to messages"
ON messages FOR UPDATE
USING (true);

CREATE POLICY "Allow public delete access to messages"
ON messages FOR DELETE
USING (true);

-- Add comment explaining these are MVP policies
COMMENT ON TABLE conversations IS 'Chat conversations - RLS enabled with public access for MVP. TODO: Restrict to authenticated users in production.';
COMMENT ON TABLE messages IS 'Chat messages - RLS enabled with public access for MVP. TODO: Restrict to authenticated users in production.';
