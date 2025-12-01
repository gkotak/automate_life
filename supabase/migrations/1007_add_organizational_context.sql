-- Add organizational_context field to organizations table
-- This field stores domain keywords and context for AI summarization

ALTER TABLE organizations
ADD COLUMN organizational_context TEXT;

COMMENT ON COLUMN organizations.organizational_context IS 'Domain-specific keywords and context for AI content analysis and summarization';
