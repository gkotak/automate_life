# Earnings Insights

AI-powered earnings call analysis system that extracts transcripts, audio files, and presentations from Seeking Alpha, then uses Claude to generate structured insights with timestamps.

## Quick Start

### 1. Database Setup

Run the SQL migration in Supabase UI:
```bash
# Copy contents of supabase/migrations/014_create_earnings_tables.sql
# Paste into Supabase SQL Editor and run
```

### 2. Install Dependencies

```bash
cd programs/earnings_insights
pip install -r requirements.txt
playwright install chromium
```

### 3. Environment Variables

Add to `.env.local`:
```bash
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Deepgram (for audio transcription)
DEEPGRAM_API_KEY=your_deepgram_api_key

# Anthropic (for Claude analysis)
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 4. Initialize Companies

```bash
python scripts/earnings_insights/initialize_companies.py
```

This loads 50 companies into the database. Edit the `INITIAL_COMPANIES` list in the script to customize.

### 5. Discover IR URLs

```bash
python scripts/earnings_insights/discover_ir_urls.py
```

Finds investor relations pages for each company.

### 6. Backfill Earnings Calls

```bash
# Fetch last 4 quarters for all companies
python scripts/earnings_insights/backfill_earnings_calls.py --quarters 4

# Or specific company
python scripts/earnings_insights/backfill_earnings_calls.py --symbol AAPL --quarters 8
```

This scrapes Seeking Alpha for:
- Transcripts
- Audio files (MP3)
- Presentation PDFs

### 7. Process Earnings Calls

```bash
# Process single call
python scripts/earnings_insights/process_single_earning.py --call-id 123
python scripts/earnings_insights/process_single_earning.py --symbol AAPL --quarter "Q1 2024"

# Process all pending calls
python scripts/earnings_insights/process_all_pending.py

# Process first 10 pending
python scripts/earnings_insights/process_all_pending.py --limit 10
```

This runs the full pipeline:
1. Download audio
2. Extract transcript
3. Align transcript with audio (add timestamps)
4. Claude analysis
5. Save insights to database

---

## Architecture

### Database Tables

**earnings_companies** - List of tracked companies
- symbol, name, sector
- investor_relations_url, seekingalpha_url

**earnings_calls** - Raw call data
- transcript_text (original clean transcript)
- transcript_json (aligned with timestamps)
- audio_url, presentation_url
- summary_json (full Claude output)

**earnings_insights** - Structured insights
- key_metrics, business_highlights, guidance
- risks_concerns, positives, notable_quotes
- All with timestamps

### Core Components

**Shared Utilities** (from article_summarizer_backend/core)
- `TranscriptAligner` - Align text to audio timestamps
- `BrowserFetcher` - Playwright automation
- `ClaudeClient` - AI analysis

**Earnings-Specific**
- `SeekingAlphaScraper` - Scrape Seeking Alpha
- `EarningsAnalyzer` - Claude-powered insights
- `EarningsProcessor` - Main orchestrator

### Processing Flow

```
1. Scrape Seeking Alpha
   ↓
2. Download audio + transcript
   ↓
3. Align with Deepgram (add timestamps)
   ↓
4. Format for Claude [MM:SS] Speaker: Text
   ↓
5. Claude extracts insights
   ↓
6. Save to database (2 tables)
```

---

## Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `initialize_companies.py` | Load 50 companies | One-time setup |
| `discover_ir_urls.py` | Find IR pages | One-time setup |
| `backfill_earnings_calls.py` | Fetch calls from SA | One-time + periodic |
| `process_single_earning.py` | Process one call | As needed |
| `process_all_pending.py` | Batch process pending | After backfill |

---

## Cost Estimates

**One-time backfill (50 companies × 4 quarters = 200 calls)**
- Deepgram: 200 calls × $0.26/call = $52
- Claude: 200 calls × $0.15/call = $30
- **Total: ~$82**

**Ongoing (per quarter)**
- 50 new calls × ($0.26 + $0.15) = **~$20/quarter**

---

## Example Usage

### Quick Test with Apple

```bash
# 1. Add Apple to database
python scripts/earnings_insights/initialize_companies.py

# 2. Fetch Apple's latest earnings
python scripts/earnings_insights/backfill_earnings_calls.py --symbol AAPL --quarters 1

# 3. Process it
python scripts/earnings_insights/process_single_earning.py --symbol AAPL --quarter "Q4 2024"
```

### Query Insights

```sql
-- Get all insights for Apple
SELECT * FROM earnings_insights WHERE symbol = 'AAPL';

-- Get all Q4 2024 calls
SELECT * FROM earnings_calls WHERE quarter LIKE '%Q4 2024%';

-- Find concerns across all companies
SELECT symbol, quarter, jsonb_array_elements(risks_concerns) as concern
FROM earnings_insights
ORDER BY symbol, quarter;
```

---

## Troubleshooting

**Seeking Alpha Scraping Issues**
- Check if login required: Update `AuthenticationManager`
- Rate limiting: Add delays in `backfill_earnings_calls.py`

**Deepgram Errors**
- Check API key: `echo $DEEPGRAM_API_KEY`
- Verify audio URL is accessible
- Check Deepgram quota

**Claude Analysis Errors**
- Check API key: `echo $ANTHROPIC_API_KEY`
- Verify transcript has timestamps
- Check prompt length (max ~180k tokens for Sonnet)

**Database Errors**
- Verify Supabase keys
- Check RLS policies (should allow all operations)
- Ensure tables exist (run migration)

---

## Next Steps

- [ ] Add web UI to view insights
- [ ] Implement search across all earnings
- [ ] Add sentiment analysis over time
- [ ] Compare quarters/years
- [ ] Export insights to PDF
- [ ] Alert on significant guidance changes

---

## Related Documentation

- Full implementation plan: `/docs/earnings_insights_implementation_plan.md`
- Database schema: `/supabase/migrations/014_create_earnings_tables.sql`
- Shared utilities: `/programs/article_summarizer_backend/core/`
