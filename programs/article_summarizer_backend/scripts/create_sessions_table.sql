-- Browser Sessions Table for Playwright Authentication
-- Stores browser session state (cookies, localStorage) for different platforms

CREATE TABLE IF NOT EXISTS browser_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL UNIQUE, -- 'substack', 'medium', 'seekingalpha', etc.
    storage_state JSONB NOT NULL, -- Playwright storage_state.json content
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE, -- Optional expiry
    is_active BOOLEAN DEFAULT TRUE
);

-- Index for quick platform lookup
CREATE INDEX IF NOT EXISTS idx_browser_sessions_platform ON browser_sessions(platform);
CREATE INDEX IF NOT EXISTS idx_browser_sessions_active ON browser_sessions(is_active) WHERE is_active = TRUE;

-- Enable RLS
ALTER TABLE browser_sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Allow service role to manage sessions
CREATE POLICY "Service role can manage browser sessions"
    ON browser_sessions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_browser_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at
DROP TRIGGER IF EXISTS browser_sessions_updated_at ON browser_sessions;
CREATE TRIGGER browser_sessions_updated_at
    BEFORE UPDATE ON browser_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_browser_sessions_updated_at();

COMMENT ON TABLE browser_sessions IS 'Stores Playwright browser session state for authenticated content access';
COMMENT ON COLUMN browser_sessions.platform IS 'Platform identifier (substack, medium, etc.)';
COMMENT ON COLUMN browser_sessions.storage_state IS 'Playwright storage_state JSON (cookies, localStorage, sessionStorage)';
