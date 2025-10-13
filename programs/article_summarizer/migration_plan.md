# Database Schema Migration Plan

## Problem Statement
Currently storing HTML/CSS/JS in `summary_html` column, violating separation of concerns. Need to extract structured data and move presentation logic to React components.

## Current Schema Issues
- HTML markup stored in database
- CSS classes hardcoded in data
- JavaScript event handlers in database
- Difficult to change UI without data migration
- Poor performance with large HTML blobs

## Proposed New Schema

```sql
-- New structured approach
ALTER TABLE articles ADD COLUMN key_insights JSONB;
ALTER TABLE articles ADD COLUMN main_points JSONB;
ALTER TABLE articles ADD COLUMN quotes JSONB;
ALTER TABLE articles ADD COLUMN takeaways TEXT[];
ALTER TABLE articles ADD COLUMN duration_minutes INTEGER;
ALTER TABLE articles ADD COLUMN word_count INTEGER;
ALTER TABLE articles ADD COLUMN topics TEXT[];
ALTER TABLE articles ADD COLUMN sentiment TEXT;
ALTER TABLE articles ADD COLUMN complexity_level TEXT;

-- Example data structure:
-- key_insights: [
--   {
--     "insight": "The IDI Framework provides structure for thoughtful AI interaction",
--     "timestamp": "105",
--     "time_formatted": "1:45"
--   }
-- ]

-- main_points: [
--   {
--     "point": "A barbell approach balances defensive and offensive AI strategies",
--     "details": "...",
--     "timestamp": "120"
--   }
-- ]

-- quotes: [
--   {
--     "quote": "AI excels at reflecting themes and patterns",
--     "speaker": "presenter",
--     "timestamp": "214",
--     "context": "..."
--   }
-- ]
```

## Migration Strategy

### Phase 1: Parse Existing HTML
1. Extract insights, timestamps, and structure from existing `summary_html`
2. Convert to structured JSONB format
3. Populate new columns with parsed data

### Phase 2: Update React Components
1. Create `InsightsList` component to render key_insights
2. Create `MainPointsList` component for main_points
3. Create `QuotesList` component for quotes
4. Add timestamp click handlers in React (not in data)

### Phase 3: Update Article Generation
1. Modify Claude processing to output structured data
2. Update migration scripts to populate new fields
3. Stop generating HTML summaries

### Phase 4: Cleanup
1. Deprecate `summary_html` column
2. Update TypeScript types
3. Remove HTML templates

## Benefits After Migration

✅ **Separation of Concerns**: Data vs Presentation
✅ **Better Performance**: No large HTML blobs
✅ **Flexible UI**: Easy to change layouts without data migration
✅ **API Ready**: Clean JSON responses for mobile apps
✅ **Better Search**: Can search specific insight types
✅ **Analytics Friendly**: Can analyze insight patterns
✅ **A/B Testing**: Easy to test different UI presentations

## Implementation Priority

1. **High Priority**: Phase 1 & 2 (parse existing data, update components)
2. **Medium Priority**: Phase 3 (update generation pipeline)
3. **Low Priority**: Phase 4 (cleanup old columns)

This approach makes the app much more maintainable and follows React/Next.js best practices.