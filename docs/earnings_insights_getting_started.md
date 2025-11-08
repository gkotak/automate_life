# Earnings Insights - Getting Started

Quick start guide to set up and run the earnings insights system.

## Implementation Complete! ✅

All core components have been created:
- ✅ Database schema (SQL migration)
- ✅ Transcript aligner (shared core utility)
- ✅ Seeking Alpha scraper
- ✅ Company management scripts
- ✅ Earnings processor (main orchestrator)
- ✅ Claude analyzer with prompts
- ✅ CLI scripts for all operations

---

## Step-by-Step Setup

### Step 1: Create Database Tables

1. Open Supabase Dashboard
2. Go to SQL Editor
3. Copy contents of `/supabase/migrations/014_create_earnings_tables.sql`
4. Paste and run

**Verify:**
```sql
SELECT table_name FROM information_schema.tables
WHERE table_name LIKE 'earnings_%';
```

Should return: `earnings_companies`, `earnings_calls`, `earnings_insights`

---

### Step 2: Install Dependencies

```bash
cd programs/earnings_insights
pip install -r requirements.txt
playwright install chromium
```

**Verify:**
```bash
python -c "import playwright; print('✅ Playwright installed')"
python -c "import deepgram; print('✅ Deepgram SDK installed')"
python -c "import anthropic; print('✅ Anthropic SDK installed')"
```

---

### Step 3: Set Environment Variables

Add to `.env.local` (in project root):

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Deepgram (sign up at deepgram.com)
DEEPGRAM_API_KEY=your_deepgram_api_key

# Anthropic (sign up at anthropic.com)
ANTHROPIC_API_KEY=your_anthropic_api_key
```

**Verify:**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ All keys set' if all([os.getenv('SUPABASE_URL'), os.getenv('DEEPGRAM_API_KEY'), os.getenv('ANTHROPIC_API_KEY')]) else '❌ Missing keys')"
```

---

### Step 4: Initialize Companies

```bash
python scripts/earnings_insights/initialize_companies.py
```

**Expected output:**
```
✅ Added: AAPL   - Apple Inc.
✅ Added: MSFT   - Microsoft Corporation
...
✅ Inserted: 50 companies
```

**Customize:** Edit `INITIAL_COMPANIES` list in `initialize_companies.py`

---

### Step 5: Discover IR URLs (Optional)

```bash
python scripts/earnings_insights/discover_ir_urls.py
```

This finds investor relations pages. Can skip if using Seeking Alpha only.

---

### Step 6: Backfill Earnings Calls

**Start small - test with one company:**
```bash
python scripts/earnings_insights/backfill_earnings_calls.py --symbol AAPL --quarters 1
```

**Expected output:**
```
🔍 [SEEKING ALPHA] Fetching 1 earnings calls for AAPL
   📄 Article 1: Apple Inc. (AAPL) Q4 2024 Earnings Call Transcript...
      ✅ Extracted: AAPL Q4 2024
✅ [SEEKING ALPHA] Extracted 1 earnings calls for AAPL
   ✅ Added: AAPL Q4 2024
```

**Then backfill all companies:**
```bash
python scripts/earnings_insights/backfill_earnings_calls.py --quarters 4
```

This will take ~10-20 minutes for 50 companies.

---

### Step 7: Process One Earnings Call (Test)

```bash
python scripts/earnings_insights/process_single_earning.py --symbol AAPL --quarter "Q4 2024"
```

**Expected output:**
```
================================================================================
PROCESSING EARNINGS CALL ID: 1
================================================================================

📊 AAPL Q4 2024
✅ Both audio and transcript available - aligning timestamps
🤖 [CLAUDE] Analyzing AAPL Q4 2024 earnings call
   ✅ Received response: 5432 chars
✅ [INSIGHTS] AAPL Q4 2024 analysis complete:
   - Key metrics: 8 items
   - Business highlights: 5 items
   - Guidance: 3 items
   - Risks/concerns: 4 items
   - Positives: 6 items
   - Notable quotes: 4 items
   ✅ Saved summary_json to earnings_calls
   ✅ Saved structured insights to earnings_insights

✅ Successfully processed AAPL Q4 2024
```

---

### Step 8: Process All Pending Calls

```bash
# Start with 10 to test
python scripts/earnings_insights/process_all_pending.py --limit 10

# Then process all
python scripts/earnings_insights/process_all_pending.py
```

**Expected time:** ~3-5 minutes per call (alignment + Claude analysis)

---

## Verify Everything Works

### Check Database

```sql
-- Count companies
SELECT COUNT(*) FROM earnings_companies;  -- Should be 50

-- Count earnings calls
SELECT COUNT(*) FROM earnings_calls;      -- Should be ~200 (50 × 4)

-- Count processed
SELECT processing_status, COUNT(*)
FROM earnings_calls
GROUP BY processing_status;

-- View sample insights
SELECT symbol, quarter,
       jsonb_array_length(business_highlights) as highlights,
       jsonb_array_length(positives) as positives,
       jsonb_array_length(notable_quotes) as quotes
FROM earnings_insights
LIMIT 10;
```

### Query Insights

```sql
-- Get all Apple insights
SELECT * FROM earnings_insights WHERE symbol = 'AAPL';

-- Get all Q4 2024 calls
SELECT symbol, quarter, key_metrics->>'revenue_growth' as revenue
FROM earnings_insights
WHERE quarter LIKE '%Q4 2024%';

-- Find all concerns across companies
SELECT symbol, quarter,
       jsonb_array_elements(risks_concerns)->>'text' as concern,
       jsonb_array_elements(risks_concerns)->>'timestamp' as timestamp
FROM earnings_insights
ORDER BY symbol;
```

---

## Troubleshooting

### Issue: "Playwright not found"
**Fix:**
```bash
pip install playwright
playwright install chromium
```

### Issue: "DEEPGRAM_API_KEY not set"
**Fix:**
1. Sign up at deepgram.com
2. Get API key
3. Add to `.env.local`: `DEEPGRAM_API_KEY=...`

### Issue: "Seeking Alpha returns 403"
**Fix:** May need authentication
1. Update `SeekingAlphaScraper` to use `AuthenticationManager`
2. Store browser session in Supabase

### Issue: "Claude analysis fails"
**Check:**
1. Transcript has timestamps: `[MM:SS] Speaker: Text`
2. API key is valid
3. Prompt length < 180k tokens

### Issue: "No earnings calls found for symbol"
**Fix:**
- Check if company exists: `SELECT * FROM earnings_companies WHERE symbol = 'AAPL';`
- Run backfill: `python scripts/earnings_insights/backfill_earnings_calls.py --symbol AAPL --quarters 4`

---

## Next Steps

### Immediate
- [ ] Process all 200 calls: `process_all_pending.py`
- [ ] Verify insights quality by spot-checking 3-5 companies
- [ ] Query database to explore insights

### Future Enhancements
- [ ] Build web UI to view insights (in article-summarizer web app)
- [ ] Add semantic search across all earnings
- [ ] Compare quarters over time (Q4 2024 vs Q4 2023)
- [ ] Generate executive summaries
- [ ] Alert on significant guidance changes

---

## Cost Tracking

**Expected costs for 200 calls:**
- Deepgram transcription: $52
- Claude analysis: $30
- **Total: ~$82**

**Monitor usage:**
- Deepgram dashboard: usage.deepgram.com
- Anthropic dashboard: console.anthropic.com

---

## Files Created

### Core System
- ✅ `supabase/migrations/014_create_earnings_tables.sql`
- ✅ `programs/article_summarizer_backend/core/transcript_aligner.py`
- ✅ `programs/earnings_insights/scrapers/seekingalpha_scraper.py`
- ✅ `programs/earnings_insights/processors/earnings_analyzer.py`
- ✅ `programs/earnings_insights/app/services/earnings_processor.py`
- ✅ `programs/earnings_insights/prompts/earnings_prompts.py`

### Scripts
- ✅ `scripts/earnings_insights/initialize_companies.py`
- ✅ `scripts/earnings_insights/discover_ir_urls.py`
- ✅ `scripts/earnings_insights/backfill_earnings_calls.py`
- ✅ `scripts/earnings_insights/process_single_earning.py`
- ✅ `scripts/earnings_insights/process_all_pending.py`

### Documentation
- ✅ `programs/earnings_insights/README.md`
- ✅ `docs/earnings_insights_implementation_plan.md`
- ✅ `docs/earnings_insights_getting_started.md` (this file)

---

## Quick Reference

```bash
# Setup (one-time)
pip install -r programs/earnings_insights/requirements.txt
playwright install chromium
python scripts/earnings_insights/initialize_companies.py
python scripts/earnings_insights/backfill_earnings_calls.py --quarters 4

# Processing
python scripts/earnings_insights/process_single_earning.py --symbol AAPL --quarter "Q4 2024"
python scripts/earnings_insights/process_all_pending.py --limit 10

# Maintenance (periodic)
python scripts/earnings_insights/backfill_earnings_calls.py --quarters 1
python scripts/earnings_insights/process_all_pending.py
```

---

## Support

Questions? Check:
1. Full plan: `/docs/earnings_insights_implementation_plan.md`
2. README: `/programs/earnings_insights/README.md`
3. Code comments in each module

Happy analyzing! 🎉
