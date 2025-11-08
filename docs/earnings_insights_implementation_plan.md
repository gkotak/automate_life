# Earnings Insights Implementation Plan

## Overview

This document outlines the implementation plan for the **earnings_insights** program, which analyzes public company earnings calls by extracting transcripts, audio files, and presentations from Seeking Alpha and investor relations websites, then uses AI to generate structured insights.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Database Schema](#database-schema)
3. [Core Components & Reusability](#core-components--reusability)
4. [Processing Flow](#processing-flow)
5. [Implementation Phases](#implementation-phases)
6. [Scripts & Tools](#scripts--tools)
7. [Seeking Alpha Scraping Strategy](#seeking-alpha-scraping-strategy)
8. [Transcript Alignment](#transcript-alignment)
9. [Claude Analysis](#claude-analysis)
10. [Testing & Validation](#testing--validation)

---

## System Architecture

### Directory Structure

```
programs/
├── article_summarizer_backend/
│   └── core/                           # SHARED CORE UTILITIES (source of truth)
│       ├── transcript_aligner.py       # NEW: Align text to audio timestamps
│       ├── browser_fetcher.py          # Playwright automation
│       ├── authentication.py           # Browser session management
│       ├── content_detector.py         # Detect video/audio/PDF
│       ├── claude_client.py            # AI analysis
│       └── file_transcriber.py         # Deepgram transcription
│
├── earnings_insights/                  # NEW PROGRAM
│   ├── app/
│   │   ├── main.py                     # FastAPI server (port 8002)
│   │   ├── routes/
│   │   │   ├── process.py              # Process earnings endpoint
│   │   │   └── companies.py            # Manage companies
│   │   ├── services/
│   │   │   ├── earnings_processor.py   # Main orchestrator
│   │   │   ├── company_discoverer.py   # Find IR URLs
│   │   │   └── earnings_scraper.py     # Extract call data
│   │   ├── models/
│   │   │   └── earnings_models.py      # Pydantic models
│   │   └── middleware/
│   │       └── auth.py                 # API authentication
│   ├── core/
│   │   └── __init__.py                 # Re-exports from article_summarizer/core
│   ├── scrapers/
│   │   ├── seekingalpha_scraper.py     # Seeking Alpha earnings scraper
│   │   └── ir_website_scraper.py       # Generic IR page scraper
│   ├── processors/
│   │   └── earnings_analyzer.py        # Claude-based analysis
│   ├── prompts/
│   │   └── earnings_prompts.py         # Earnings-specific prompts
│   └── requirements.txt                # Dependencies
│
└── scripts/
    └── earnings_insights/
        ├── initialize_companies.py          # Load initial 50 companies
        ├── discover_ir_urls.py              # Find investor relations pages
        ├── backfill_earnings_calls.py       # Get latest 4 quarters per company
        ├── process_single_earning.py        # Process one earnings call
        └── regenerate_summaries.py          # Re-run AI analysis
```

### Key Architectural Decisions

**1. Shared Core Utilities**
- `transcript_aligner.py` lives in `article_summarizer_backend/core/`
- Both article_summarizer AND earnings_insights use the same alignment logic
- Benefits: DRY principle, consistent behavior, easier maintenance
- Article summarizer can also benefit (Substack audio posts, YouTube videos with articles)

**2. Separate Database Tables**
- Same Supabase database as article_summarizer
- Completely separate tables (no shared `articles` table)
- Clean separation of concerns

**3. Port Allocation**
- article_summarizer_backend: Port 8000
- content_checker_backend: Port 8001
- earnings_insights: Port 8002

---

## Database Schema

### 1. `earnings_companies` Table

Stores the list of companies to track.

```sql
CREATE TABLE earnings_companies (
  id SERIAL PRIMARY KEY,
  symbol TEXT UNIQUE NOT NULL,           -- Stock ticker (e.g., "AAPL")
  name TEXT NOT NULL,                     -- Company name (e.g., "Apple Inc.")
  sector TEXT,                            -- Industry sector
  investor_relations_url TEXT,            -- IR page URL
  seekingalpha_url TEXT,                  -- Seeking Alpha company page
  is_active BOOLEAN DEFAULT true,         -- Whether to track this company
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX earnings_companies_symbol_idx ON earnings_companies(symbol);
CREATE INDEX earnings_companies_active_idx ON earnings_companies(is_active);
```

### 2. `earnings_calls` Table

Stores raw earnings call data (transcript, audio, presentation).

```sql
CREATE TABLE earnings_calls (
  id SERIAL PRIMARY KEY,
  company_id INTEGER REFERENCES earnings_companies(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  quarter TEXT NOT NULL,                  -- e.g., "Q1 2024"
  fiscal_year INTEGER NOT NULL,
  earnings_date DATE,                     -- Actual earnings release date
  call_date TIMESTAMP,                    -- When call occurred

  -- Transcript storage (TWO columns)
  transcript_text TEXT,                   -- Original Seeking Alpha transcript (clean, human-edited)
  transcript_json JSONB,                  -- Aligned version with timestamps
  transcript_source TEXT,                 -- 'seekingalpha', 'investor_relations', 'deepgram'

  -- Audio
  audio_url TEXT,                         -- MP3/audio file URL
  audio_source TEXT,                      -- 'seekingalpha', 'investor_relations'
  audio_duration_seconds INTEGER,

  -- Presentation
  presentation_url TEXT,                  -- PDF/slides URL
  presentation_source TEXT,

  -- AI-generated summary (full JSON output from Claude)
  summary_json JSONB,

  -- Semantic search
  embedding VECTOR(1536),                 -- OpenAI embedding

  -- Processing status
  processing_status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
  error_message TEXT,

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  UNIQUE(company_id, quarter, fiscal_year)
);

-- Indexes
CREATE INDEX earnings_calls_company_idx ON earnings_calls(company_id);
CREATE INDEX earnings_calls_symbol_idx ON earnings_calls(symbol);
CREATE INDEX earnings_calls_quarter_idx ON earnings_calls(quarter, fiscal_year);
CREATE INDEX earnings_calls_status_idx ON earnings_calls(processing_status);
CREATE INDEX earnings_calls_date_idx ON earnings_calls(call_date DESC);
CREATE INDEX earnings_calls_embedding_idx ON earnings_calls USING ivfflat(embedding vector_cosine_ops);
```

**Why two transcript columns?**
- `transcript_text`: Original clean transcript for backup, search, export
- `transcript_json`: Aligned version with timestamps for Claude analysis and web app

### 3. `earnings_insights` Table

Extracted key insights for fast queries (denormalized from `summary_json`).

```sql
CREATE TABLE earnings_insights (
  id SERIAL PRIMARY KEY,
  earnings_call_id INTEGER REFERENCES earnings_calls(id) ON DELETE CASCADE,
  company_id INTEGER REFERENCES earnings_companies(id) ON DELETE CASCADE,
  symbol TEXT NOT NULL,
  quarter TEXT NOT NULL,

  -- AI-extracted insights (all include timestamps from aligned transcript)
  key_metrics JSONB,              -- { "metric_name": { "value": "...", "timestamp": "05:30", "speaker": "CFO" } }
  business_highlights JSONB[],    -- [{ "text": "...", "timestamp": "03:20", "speaker": "CEO" }]
  guidance JSONB,                 -- { "q3_revenue": { "value": "...", "timestamp": "08:45" } }
  risks_concerns JSONB[],         -- [{ "text": "...", "timestamp": "10:30", "speaker": "CEO", "context": "concern" }]
  positives JSONB[],              -- [{ "text": "...", "timestamp": "05:30", "speaker": "CFO" }]
  notable_quotes JSONB[],         -- [{ "quote": "...", "timestamp": "15:45", "speaker": "CEO", "context": "..." }]

  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX earnings_insights_call_idx ON earnings_insights(earnings_call_id);
CREATE INDEX earnings_insights_company_idx ON earnings_insights(company_id);
CREATE INDEX earnings_insights_symbol_quarter_idx ON earnings_insights(symbol, quarter);
```

**Why separate insights table?**
- Fast queries without parsing JSONB: "Show all Q3 2024 earnings"
- Easy to add computed columns later (sentiment scores, etc.)
- Clean separation: raw data vs processed intelligence

### 4. Enable RLS (Row Level Security)

```sql
ALTER TABLE earnings_companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE earnings_insights ENABLE ROW LEVEL SECURITY;

-- Policies (adjust based on your auth requirements)
CREATE POLICY "Users can view all companies" ON earnings_companies FOR SELECT USING (true);
CREATE POLICY "Users can manage companies" ON earnings_companies FOR ALL USING (true);

CREATE POLICY "Users can view all earnings_calls" ON earnings_calls FOR SELECT USING (true);
CREATE POLICY "Users can manage earnings_calls" ON earnings_calls FOR ALL USING (true);

CREATE POLICY "Users can view all earnings_insights" ON earnings_insights FOR SELECT USING (true);
CREATE POLICY "Users can manage earnings_insights" ON earnings_insights FOR ALL USING (true);
```

---

## Core Components & Reusability

### Shared Core Utilities (from article_summarizer_backend/core)

**Used by both article_summarizer AND earnings_insights:**

| Module | Purpose | Owner |
|--------|---------|-------|
| `transcript_aligner.py` | Align text to audio timestamps using Deepgram | article_summarizer (NEW) |
| `browser_fetcher.py` | Playwright automation for complex scraping | article_summarizer |
| `authentication.py` | Browser session management (cookies, storage state) | article_summarizer |
| `content_detector.py` | Detect video/audio/PDF on pages | article_summarizer |
| `claude_client.py` | Claude API client for AI analysis | article_summarizer |
| `file_transcriber.py` | Deepgram audio → text transcription | article_summarizer |

### How earnings_insights Imports Shared Core

```python
# earnings_insights/core/__init__.py
"""
Re-export shared utilities from article_summarizer_backend
"""
import sys
from pathlib import Path

# Add article_summarizer to path
article_summarizer_path = Path(__file__).parent.parent.parent / 'article_summarizer_backend'
sys.path.insert(0, str(article_summarizer_path))

# Re-export shared utilities
from core.transcript_aligner import TranscriptAligner
from core.browser_fetcher import BrowserFetcher
from core.authentication import AuthenticationManager
from core.content_detector import ContentTypeDetector
from core.claude_client import ClaudeClient
from core.file_transcriber import FileTranscriber

__all__ = [
    'TranscriptAligner',
    'BrowserFetcher',
    'AuthenticationManager',
    'ContentTypeDetector',
    'ClaudeClient',
    'FileTranscriber'
]
```

Then in earnings_insights services:
```python
from core import TranscriptAligner, ClaudeClient  # Clean import
```

### Program-Specific Components

**earnings_insights only:**

| Module | Purpose |
|--------|---------|
| `scrapers/seekingalpha_scraper.py` | Navigate Seeking Alpha, extract earnings data |
| `scrapers/ir_website_scraper.py` | Generic IR page scraper |
| `processors/earnings_analyzer.py` | Claude-based earnings analysis |
| `prompts/earnings_prompts.py` | Earnings-specific prompts |

---

## Processing Flow

### High-Level Flow

```
1. Initialize Companies (one-time)
   ↓
2. Discover IR URLs (one-time)
   ↓
3. Backfill Earnings Calls (one-time + periodic)
   ↓
4. Process Each Call:
   a. Download Audio (always)
   b. Extract Transcript (always)
   c. Align Transcript with Audio (if both available)
   d. Format for Claude (with timestamps)
   e. Claude Analysis → Insights
   f. Save to Database
```

### Detailed Processing Flow

```python
# In services/earnings_processor.py

async def process_earnings_call(earnings_call_id: int):
    """
    Main processing function for a single earnings call
    """

    # 1. Load call from database
    call = await db.get_earnings_call(earnings_call_id)
    logger.info(f"Processing {call.symbol} {call.quarter}")

    # 2. Download/verify audio exists (ALWAYS)
    if not call.audio_url:
        logger.info("🔍 Searching for audio file...")
        audio_url = await scraper.find_audio(call.symbol, call.quarter)
        if audio_url:
            await db.update_call(earnings_call_id, audio_url=audio_url)
            call.audio_url = audio_url
        else:
            logger.warning("⚠️ No audio found")

    # 3. Extract transcript (ALWAYS)
    if not call.transcript_text:
        logger.info("🔍 Extracting transcript from Seeking Alpha...")
        transcript = await scraper.extract_transcript(call.symbol, call.quarter)
        if transcript:
            await db.update_call(earnings_call_id, transcript_text=transcript)
            call.transcript_text = transcript
        else:
            logger.warning("⚠️ No transcript found")

    # 4. Align transcript with audio timestamps
    transcript_for_claude = None

    if call.audio_url and call.transcript_text:
        logger.info("✅ Both audio and transcript available - aligning timestamps")

        aligner = TranscriptAligner()
        aligned_data = await aligner.align_transcript(
            call.audio_url,
            call.transcript_text
        )

        # Save aligned version to database
        await db.update_call(earnings_call_id,
            transcript_json={
                "aligned_transcript": aligned_data["aligned_transcript"],
                "source": "seekingalpha_aligned_with_deepgram"
            }
        )

        # Format for Claude with timestamps: [MM:SS] Speaker: Text
        transcript_for_claude = format_aligned_transcript_for_claude(aligned_data)

    elif call.audio_url and not call.transcript_text:
        logger.info("⚠️ Audio only - transcribing with Deepgram")

        transcriber = FileTranscriber()
        dg_result = await transcriber.transcribe_audio(call.audio_url)

        transcript_text = dg_result['transcript']
        await db.update_call(earnings_call_id,
            transcript_text=transcript_text,
            transcript_json={
                "deepgram_transcript": dg_result,
                "source": "deepgram_only"
            }
        )

        # Format Deepgram output for Claude (has timestamps)
        transcript_for_claude = format_deepgram_for_claude(dg_result)

    elif call.transcript_text and not call.audio_url:
        logger.warning("⚠️ Transcript only - no timestamps available")
        transcript_for_claude = call.transcript_text

    else:
        logger.error("❌ No audio or transcript available - cannot process")
        await db.update_call(earnings_call_id,
            processing_status='failed',
            error_message='No audio or transcript available'
        )
        return

    # 5. Run Claude analysis
    logger.info("🤖 Running Claude analysis...")
    analyzer = EarningsAnalyzer()
    insights = await analyzer.analyze_earnings_call(
        transcript_text=transcript_for_claude,
        company_symbol=call.symbol,
        quarter=call.quarter
    )

    # 6. Save insights to database
    await db.insert_earnings_insights({
        "earnings_call_id": earnings_call_id,
        "company_id": call.company_id,
        "symbol": call.symbol,
        "quarter": call.quarter,
        "key_metrics": insights["key_metrics"],
        "business_highlights": insights["business_highlights"],
        "guidance": insights["guidance"],
        "risks_concerns": insights["risks_concerns"],
        "positives": insights["positives"],
        "notable_quotes": insights["notable_quotes"]
    })

    # 7. Save full summary_json to earnings_calls
    await db.update_call(earnings_call_id,
        summary_json=insights,
        processing_status='completed'
    )

    logger.info(f"✅ Processing complete for {call.symbol} {call.quarter}")
```

---

## Implementation Phases

### Phase 1: Database Setup

**Goal**: Create all database tables and migrations

**Tasks**:
1. Create migration file: `supabase/migrations/014_create_earnings_tables.sql`
2. Add all three tables: `earnings_companies`, `earnings_calls`, `earnings_insights`
3. Add indexes for performance
4. Enable RLS and create policies
5. Run migration: Apply to Supabase database

**Scripts to run**:
```bash
# Create migration file with schema
# Then apply via Supabase dashboard or CLI
supabase db push
```

**Deliverables**:
- Migration file with complete schema
- Tables visible in Supabase dashboard

---

### Phase 2: Core Utilities - Transcript Alignment

**Goal**: Implement `transcript_aligner.py` in `article_summarizer_backend/core/`

**Tasks**:
1. Create `TranscriptAligner` class
2. Implement Deepgram transcription with word-level timestamps
3. Implement text alignment algorithm (fuzzy matching)
4. Parse Seeking Alpha transcript format (speaker detection)
5. Format aligned transcript for Claude (`[MM:SS] Speaker: Text`)
6. Test with sample audio + transcript

**Key Methods**:
```python
class TranscriptAligner:
    async def align_transcript(audio_url: str, transcript_text: str) -> dict
    async def _transcribe_with_deepgram(audio_url: str) -> dict
    def _parse_seekingalpha_transcript(transcript: str) -> list
    def _find_text_in_transcript(target_text: str, dg_words: list) -> tuple
    def format_aligned_transcript_for_claude(aligned_data: dict) -> str
```

**Testing**:
```bash
# Test with sample earnings call
python -m pytest tests/test_transcript_aligner.py
```

**Deliverables**:
- `article_summarizer_backend/core/transcript_aligner.py`
- Unit tests
- Sample aligned output

---

### Phase 3: Seeking Alpha Scraper

**Goal**: Scrape earnings calls from Seeking Alpha

**Tasks**:
1. Create `seekingalpha_scraper.py`
2. Implement navigation to symbol page
3. Find latest earnings call articles
4. Extract transcript HTML → clean text
5. Find audio URL (using existing `content_detector._detect_seekingalpha_audio()`)
6. Find presentation PDF links
7. Handle authentication if needed (use `AuthenticationManager`)

**Key Methods**:
```python
class SeekingAlphaScraper:
    async def get_latest_earnings_calls(symbol: str, num_quarters: int) -> list
    async def extract_transcript(article_url: str) -> str
    async def find_audio_url(article_url: str) -> str
    async def find_presentation_url(article_url: str) -> str
```

**Navigation Flow**:
1. Go to `https://seekingalpha.com/symbol/{SYMBOL}`
2. Click "Earnings" tab
3. Find first N earnings call articles
4. For each article:
   - Extract transcript from article page
   - Check for audio: `https://static.seekingalpha.com/cdn/s3/transcripts_audio/{article_id}.mp3`
   - Look for presentation PDF links

**Testing**:
```bash
# Test with a known stock
python scripts/earnings_insights/test_seekingalpha_scraper.py --symbol AAPL
```

**Deliverables**:
- `earnings_insights/scrapers/seekingalpha_scraper.py`
- Test script
- Sample output (transcript + audio URL)

---

### Phase 4: Scripts - Company Management

**Goal**: Initialize companies and discover IR URLs

**Script 1: `initialize_companies.py`**

```python
"""
Load initial list of 50 companies into database
"""

INITIAL_COMPANIES = [
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
    # ... 47 more
]

async def main():
    for company in INITIAL_COMPANIES:
        await db.insert_company(company)
        logger.info(f"✅ Added {company['symbol']}")
```

**Script 2: `discover_ir_urls.py`**

```python
"""
Find investor relations URLs for all companies
"""

async def discover_ir_url(symbol: str, company_name: str):
    # Method 1: Search Google for "[company name] investor relations"
    # Method 2: Try common patterns:
    #   - https://investor.{company}.com
    #   - https://ir.{company}.com
    #   - https://{company}.com/investor-relations
    # Method 3: Use Playwright to verify page exists

    ir_url = await search_and_verify_ir_url(company_name)
    seekingalpha_url = f"https://seekingalpha.com/symbol/{symbol}"

    await db.update_company(symbol,
        investor_relations_url=ir_url,
        seekingalpha_url=seekingalpha_url
    )
```

**Usage**:
```bash
# Initialize all companies
python scripts/earnings_insights/initialize_companies.py

# Discover IR URLs
python scripts/earnings_insights/discover_ir_urls.py
```

**Deliverables**:
- `scripts/earnings_insights/initialize_companies.py`
- `scripts/earnings_insights/discover_ir_urls.py`
- 50 companies in database with IR URLs

---

### Phase 5: Scripts - Backfill Earnings Calls

**Goal**: Fetch last N quarters of earnings calls for all companies

**Script: `backfill_earnings_calls.py`**

```python
"""
Backfill earnings calls from Seeking Alpha

Usage:
    python backfill_earnings_calls.py --quarters 4
    python backfill_earnings_calls.py --symbol AAPL --quarters 8
"""

async def backfill_company_earnings(symbol: str, num_quarters: int):
    logger.info(f"Backfilling {num_quarters} quarters for {symbol}")

    # 1. Get latest earnings calls from Seeking Alpha
    scraper = SeekingAlphaScraper()
    earnings_data = await scraper.get_latest_earnings_calls(symbol, num_quarters)

    # 2. Insert each call into database
    for call in earnings_data:
        await db.insert_earnings_call({
            "company_id": company_id,
            "symbol": symbol,
            "quarter": call["quarter"],
            "fiscal_year": call["fiscal_year"],
            "call_date": call["call_date"],
            "transcript_text": call["transcript"],
            "transcript_source": "seekingalpha",
            "audio_url": call["audio_url"],
            "audio_source": "seekingalpha",
            "presentation_url": call["presentation_url"],
            "processing_status": "pending"
        })
        logger.info(f"✅ Added {symbol} {call['quarter']} to database")

async def main(args):
    if args.symbol:
        await backfill_company_earnings(args.symbol, args.quarters)
    else:
        # Backfill all active companies
        companies = await db.get_active_companies()
        for company in companies:
            await backfill_company_earnings(company.symbol, args.quarters)
```

**Usage**:
```bash
# Backfill last 4 quarters for all companies
python scripts/earnings_insights/backfill_earnings_calls.py --quarters 4

# Backfill specific company
python scripts/earnings_insights/backfill_earnings_calls.py --symbol AAPL --quarters 8
```

**Deliverables**:
- `scripts/earnings_insights/backfill_earnings_calls.py`
- All companies have 4 quarters in `earnings_calls` table with status='pending'

---

### Phase 6: Claude Analysis - Earnings Insights

**Goal**: Implement Claude-based earnings analysis with timestamps

**Task 1: Create Earnings Prompt**

```python
# earnings_insights/prompts/earnings_prompts.py

EARNINGS_INSIGHTS_PROMPT = """
You are analyzing an earnings call transcript with timestamps. The transcript format is:
[MM:SS] Speaker: Text content

Example:
[00:45] CEO: We delivered record revenue of $52.3 billion, up 15% year-over-year...
[05:30] CFO: Our operating margins expanded to 28%, the highest in company history...
[12:15] Analyst - Goldman Sachs: Can you discuss the sustainability of these margins?

Extract the following insights as JSON:

{
  "key_metrics": {
    // Financial highlights with timestamps
    // Examples: revenue growth, profitability, margins
    "revenue_growth": {
      "value": "15% year-over-year to $52.3B",
      "timestamp": "00:45",
      "speaker": "CEO"
    },
    "operating_margin": {
      "value": "Expanded to 28%, highest ever",
      "timestamp": "05:30",
      "speaker": "CFO"
    }
  },

  "business_highlights": [
    // Key business updates (not financial metrics)
    {
      "text": "Launched new AI assistant with 50 million active users in first month",
      "timestamp": "03:20",
      "speaker": "CEO"
    }
  ],

  "guidance": {
    // Forward-looking statements from management
    "q3_revenue": {
      "value": "Expected between $54B - $56B",
      "timestamp": "08:45",
      "speaker": "CFO"
    }
  },

  "risks_concerns": [
    // ANY concerns mentioned - by management OR raised by analysts
    {
      "text": "Increased competitive pressure from new entrants with aggressive pricing",
      "timestamp": "10:30",
      "speaker": "CEO",
      "context": "management_remark"
    },
    {
      "text": "Analyst questioned sustainability of margin expansion given increased AI R&D spending",
      "timestamp": "12:15",
      "speaker": "Analyst - Goldman Sachs",
      "context": "analyst_question"
    }
  ],

  "positives": [
    // Positive developments, achievements, strengths highlighted
    {
      "text": "Operating margins reached 28%, highest in company history",
      "timestamp": "05:30",
      "speaker": "CFO"
    }
  ],

  "notable_quotes": [
    // Memorable quotes that capture key themes or strong statements
    {
      "quote": "We're not just riding the AI wave, we're building the infrastructure that powers it",
      "timestamp": "15:45",
      "speaker": "CEO",
      "context": "strategic_vision"
    }
  ]
}

IMPORTANT RULES:
1. **Use EXACT timestamps from the transcript** - do NOT guess or estimate
2. If a metric/highlight appears in the transcript, include its timestamp
3. For risks_concerns: Use "context" field to distinguish management remarks vs analyst questions
4. Include 3-5 notable quotes that capture key themes or strong statements
5. Be specific and include numbers/percentages where mentioned
6. Keep each point concise (1-2 sentences max)

Now extract from this timestamped earnings call transcript:

{transcript}
"""
```

**Task 2: Implement Analyzer**

```python
# earnings_insights/processors/earnings_analyzer.py

from core import ClaudeClient
from prompts.earnings_prompts import EARNINGS_INSIGHTS_PROMPT

class EarningsAnalyzer:
    def __init__(self):
        self.claude = ClaudeClient()

    async def analyze_earnings_call(
        self,
        transcript_text: str,
        company_symbol: str,
        quarter: str
    ) -> dict:
        """
        Analyze earnings call transcript and extract insights

        Args:
            transcript_text: Formatted transcript with timestamps
            company_symbol: Stock ticker
            quarter: e.g., "Q1 2024"

        Returns:
            Structured insights dict
        """
        logger.info(f"🤖 Analyzing {company_symbol} {quarter} with Claude...")

        # Send to Claude
        prompt = EARNINGS_INSIGHTS_PROMPT.format(transcript=transcript_text)
        response = await self.claude.generate(
            prompt,
            model="claude-sonnet-4",
            max_tokens=4000,
            response_format="json"
        )

        # Parse JSON response
        insights = json.loads(response)

        # Validate structure
        required_keys = ["key_metrics", "business_highlights", "guidance",
                        "risks_concerns", "positives", "notable_quotes"]
        for key in required_keys:
            if key not in insights:
                logger.warning(f"Missing key in Claude response: {key}")
                insights[key] = {} if key in ["key_metrics", "guidance"] else []

        logger.info(f"✅ Analysis complete: {len(insights['notable_quotes'])} quotes, "
                   f"{len(insights['positives'])} positives, {len(insights['risks_concerns'])} concerns")

        return insights
```

**Testing**:
```bash
# Test with sample transcript
python scripts/earnings_insights/test_claude_analysis.py
```

**Deliverables**:
- `earnings_insights/prompts/earnings_prompts.py`
- `earnings_insights/processors/earnings_analyzer.py`
- Test script with sample output

---

### Phase 7: Main Processing Script

**Goal**: Process all pending earnings calls

**Script: `process_single_earning.py`**

```python
"""
Process a single earnings call

Usage:
    python process_single_earning.py --call-id 123
    python process_single_earning.py --symbol AAPL --quarter "Q1 2024"
"""

from services.earnings_processor import process_earnings_call

async def main(args):
    if args.call_id:
        await process_earnings_call(args.call_id)
    elif args.symbol and args.quarter:
        call = await db.get_call_by_symbol_quarter(args.symbol, args.quarter)
        if call:
            await process_earnings_call(call.id)
        else:
            logger.error(f"No call found for {args.symbol} {args.quarter}")
    else:
        logger.error("Must provide --call-id or --symbol + --quarter")
```

**Batch Processing**:

```python
# Process all pending calls
async def process_all_pending():
    calls = await db.get_calls_by_status('pending')
    logger.info(f"Found {len(calls)} pending calls")

    for call in calls:
        try:
            await process_earnings_call(call.id)
        except Exception as e:
            logger.error(f"Failed to process {call.symbol} {call.quarter}: {e}")
```

**Usage**:
```bash
# Process specific call
python scripts/earnings_insights/process_single_earning.py --call-id 123

# Process all pending
python scripts/earnings_insights/process_all_pending.py
```

**Deliverables**:
- `scripts/earnings_insights/process_single_earning.py`
- `scripts/earnings_insights/process_all_pending.py`
- Processed earnings calls with insights in database

---

### Phase 8: FastAPI Backend (Optional - for automation)

**Goal**: REST API for processing earnings calls

**Endpoints**:

```python
# earnings_insights/app/main.py

from fastapi import FastAPI
from routes import process, companies

app = FastAPI(title="Earnings Insights API")

app.include_router(process.router, prefix="/api/process")
app.include_router(companies.router, prefix="/api/companies")

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}
```

**Routes**:

```python
# earnings_insights/app/routes/process.py

from fastapi import APIRouter, BackgroundTasks

router = APIRouter()

@router.post("/earning/{call_id}")
async def process_earning(call_id: int, background_tasks: BackgroundTasks):
    """Process a single earnings call"""
    background_tasks.add_task(process_earnings_call, call_id)
    return {"status": "processing", "call_id": call_id}

@router.get("/status/{call_id}")
async def get_status(call_id: int):
    """Get processing status"""
    call = await db.get_earnings_call(call_id)
    return {
        "call_id": call_id,
        "status": call.processing_status,
        "error": call.error_message
    }
```

**Usage**:
```bash
# Start server
cd programs/earnings_insights
uvicorn app.main:app --port 8002 --reload

# Process via API
curl -X POST http://localhost:8002/api/process/earning/123
```

**Deliverables**:
- FastAPI server running on port 8002
- REST API for processing

---

## Seeking Alpha Scraping Strategy

### Navigation Flow

**Step 1: Company Page**
```
URL: https://seekingalpha.com/symbol/{SYMBOL}
Example: https://seekingalpha.com/symbol/AAPL
```

**Step 2: Find Earnings Tab**
```python
await page.click('a:has-text("Earnings")')
# or
await page.goto(f'https://seekingalpha.com/symbol/{symbol}/earnings')
```

**Step 3: Extract Earnings Call Articles**
```python
# Find all earnings call articles (sorted by date, newest first)
articles = await page.query_selector_all('.article-card')

for article in articles[:num_quarters]:
    title = await article.query_selector('h3').inner_text()
    url = await article.get_attribute('href')
    date = await article.query_selector('.date').inner_text()

    # Parse quarter from title: "Apple Inc. (AAPL) Q1 2024 Earnings Call Transcript"
    quarter_match = re.search(r'(Q[1-4])\s+(\d{4})', title)
```

**Step 4: Extract Transcript from Article Page**
```python
await page.goto(article_url)

# Find transcript content (specific selectors depend on SA HTML structure)
transcript_element = await page.query_selector('article.transcript')
transcript_html = await transcript_element.inner_html()

# Parse HTML to extract clean text with speaker labels
transcript_text = parse_transcript_html(transcript_html)
```

**Step 5: Find Audio URL**
```python
# Extract article ID from URL
# Example: https://seekingalpha.com/article/4737214-... → article_id = 4737214
article_id = extract_article_id(article_url)

# Check if audio exists
audio_url = f'https://static.seekingalpha.com/cdn/s3/transcripts_audio/{article_id}.mp3'
response = requests.head(audio_url)

if response.status_code == 200:
    logger.info(f"✅ Audio found: {audio_url}")
else:
    logger.info(f"⚠️ No audio available for this call")
```

**Note**: `content_detector._detect_seekingalpha_audio()` already implements this check!

**Step 6: Find Presentation PDF**
```python
# Look for links to PDF files or "Earnings Materials" section
pdf_links = await page.query_selector_all('a[href$=".pdf"]')

for link in pdf_links:
    href = await link.get_attribute('href')
    text = await link.inner_text()

    if 'presentation' in text.lower() or 'slides' in text.lower():
        presentation_url = href
        break
```

### Authentication

If Seeking Alpha requires login:
```python
auth_manager = AuthenticationManager(base_dir, session)

# Check if we need auth
needs_auth, reason = auth_manager.check_authentication_required(url, 'seekingalpha')

if needs_auth:
    # Use browser with stored cookies/session
    success, html, msg = await auth_manager.fetch_with_browser_async(url)
```

---

## Transcript Alignment

### Overview

**Goal**: Align Seeking Alpha transcript (no timestamps) with audio file to add precise timestamps for Claude analysis.

### Architecture Decision

**Location**: `article_summarizer_backend/core/transcript_aligner.py`

**Why?**
- Shared by both article_summarizer AND earnings_insights
- Article summarizer also needs this (Substack audio posts, YouTube videos with articles)
- DRY principle: write once, use everywhere

### Alignment Process

**Step 1: Transcribe Audio with Deepgram**

```python
async def _transcribe_with_deepgram(self, audio_url: str):
    """Transcribe audio with word-level timestamps"""
    dg = Deepgram(os.getenv('DEEPGRAM_API_KEY'))

    response = await dg.transcription.prerecorded(
        {'url': audio_url},
        {
            'punctuate': True,
            'diarize': True,          # Speaker diarization
            'utterances': True,       # Group words into sentences
            'smart_format': True,
            'model': 'nova-2',        # Best accuracy
            'language': 'en'
        }
    )

    return response
```

**Output**: Word-level timestamps
```json
{
  "words": [
    {"word": "We", "start": 45.2, "end": 45.4, "confidence": 0.99},
    {"word": "delivered", "start": 45.5, "end": 45.9, "confidence": 0.98},
    ...
  ]
}
```

**Step 2: Parse Seeking Alpha Transcript**

```python
def _parse_seekingalpha_transcript(self, transcript: str) -> list:
    """
    Parse Seeking Alpha transcript into speaker segments

    SA format:
    Operator
    Good day, and thank you for standing by...

    John Doe - CEO
    Thank you for joining us today...
    """
    segments = []
    current_speaker = None
    current_text = []

    lines = transcript.split('\n')

    for line in lines:
        if self._is_speaker_line(line):
            # Save previous segment
            if current_speaker and current_text:
                segments.append({
                    "speaker": current_speaker,
                    "text": ' '.join(current_text)
                })

            current_speaker = line
            current_text = []
        else:
            current_text.append(line)

    return segments
```

**Output**: Speaker segments
```python
[
  {
    "speaker": "CEO",
    "text": "Thank you for joining us today. We delivered record revenue..."
  },
  {
    "speaker": "CFO",
    "text": "Our operating margins expanded to 28%..."
  }
]
```

**Step 3: Align Segments to Timestamps**

```python
def _find_text_in_transcript(self, target_text: str, dg_words: list) -> tuple:
    """
    Find target text in Deepgram word list and return (start_idx, end_idx)

    Uses fuzzy matching since Deepgram might have slight differences
    """
    target_words = target_text.lower().split()
    dg_text_words = [w['word'].lower() for w in dg_words]

    # Use sliding window to find best match
    best_match_score = 0
    best_match_start = None
    best_match_end = None

    for i in range(len(dg_text_words) - len(target_words) + 1):
        window = dg_text_words[i:i + len(target_words)]

        # Calculate similarity using SequenceMatcher
        similarity = SequenceMatcher(None, target_words, window).ratio()

        if similarity > best_match_score:
            best_match_score = similarity
            best_match_start = i
            best_match_end = i + len(target_words) - 1

    # Only return if match is good enough (>80% similarity)
    if best_match_score > 0.8:
        return best_match_start, best_match_end

    return None, None
```

**Step 4: Format for Claude**

```python
def format_aligned_transcript_for_claude(aligned_data: dict) -> str:
    """
    Convert aligned transcript into Claude-friendly format

    Output format:
    [00:45] CEO: We delivered record revenue of $52.3 billion...
    [02:30] CFO: Our operating margins expanded to 28%...
    """
    formatted_lines = []

    for segment in aligned_data['aligned_transcript']:
        timestamp = format_timestamp(segment['start'])
        speaker = segment['speaker']
        text = segment['text']

        formatted_lines.append(f"[{timestamp}] {speaker}: {text}")

    return '\n\n'.join(formatted_lines)

def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
```

**Final Output for Claude**:
```
[00:45] CEO: Thank you for joining us today. We delivered record revenue of $52.3 billion, up 15% year-over-year.

[05:30] CFO: Our operating margins expanded to 28%, the highest in company history.

[12:15] Analyst - Goldman Sachs: Can you discuss the sustainability of these margins?

[12:45] CEO: We're confident in maintaining margins despite AI investments...
```

### Cost Estimate

**Deepgram Pricing**: ~$0.0043/minute

**Average earnings call**: 60 minutes

**Cost per call**: $0.26

**For 50 companies × 4 quarters**: 200 calls × $0.26 = **$52 total**

---

## Claude Analysis

### Prompt Structure

**Input**: Timestamped transcript
```
[00:45] CEO: We delivered record revenue of $52.3 billion...
[05:30] CFO: Our operating margins expanded to 28%...
```

**Output**: Structured JSON with timestamps
```json
{
  "key_metrics": {
    "revenue_growth": {
      "value": "15% year-over-year to $52.3B",
      "timestamp": "00:45",
      "speaker": "CEO"
    }
  },
  "notable_quotes": [
    {
      "quote": "We're not just riding the AI wave...",
      "timestamp": "15:45",
      "speaker": "CEO"
    }
  ]
}
```

### Key Instructions to Claude

1. **Use exact timestamps** - don't guess or estimate
2. **Capture context** - distinguish management remarks vs analyst questions
3. **Be specific** - include numbers and percentages
4. **Prioritize material information** - focus on what matters to investors

### Response Format

**All insights include timestamps**:
- `key_metrics`: Financial highlights with timestamps
- `business_highlights`: Business updates with timestamps
- `guidance`: Forward guidance with timestamps
- `risks_concerns`: Concerns with timestamps + context (management vs analyst)
- `positives`: Positive developments with timestamps
- `notable_quotes`: Memorable quotes with timestamps

---

## Testing & Validation

### Unit Tests

**Test 1: Transcript Alignment**
```python
# tests/test_transcript_aligner.py

async def test_align_transcript():
    aligner = TranscriptAligner()

    # Use sample audio + transcript
    aligned = await aligner.align_transcript(
        audio_url="https://example.com/sample.mp3",
        transcript_text="CEO\nWe delivered record revenue..."
    )

    assert "aligned_transcript" in aligned
    assert len(aligned["aligned_transcript"]) > 0
    assert "start" in aligned["aligned_transcript"][0]
```

**Test 2: Seeking Alpha Scraper**
```python
# tests/test_seekingalpha_scraper.py

async def test_extract_transcript():
    scraper = SeekingAlphaScraper()

    transcript = await scraper.extract_transcript(
        "https://seekingalpha.com/article/4737214-..."
    )

    assert transcript is not None
    assert len(transcript) > 1000
    assert "CEO" in transcript or "CFO" in transcript
```

**Test 3: Claude Analysis**
```python
# tests/test_earnings_analyzer.py

async def test_analyze_earnings():
    analyzer = EarningsAnalyzer()

    sample_transcript = "[00:45] CEO: We delivered record revenue..."

    insights = await analyzer.analyze_earnings_call(
        transcript_text=sample_transcript,
        company_symbol="TEST",
        quarter="Q1 2024"
    )

    assert "key_metrics" in insights
    assert "notable_quotes" in insights
```

### Integration Tests

**Test End-to-End Processing**:
```bash
# Test with Apple Q4 2024 earnings (or any recent call)
python scripts/earnings_insights/test_e2e.py --symbol AAPL --quarter "Q4 2024"
```

**Expected flow**:
1. Scrape transcript from Seeking Alpha ✓
2. Download audio file ✓
3. Align transcript with audio ✓
4. Format for Claude ✓
5. Claude analysis ✓
6. Save to database ✓

### Manual Validation

**Validate insights accuracy**:
1. Pick 3-5 processed earnings calls
2. Read original transcript
3. Compare Claude's insights against manual reading
4. Check timestamp accuracy (click timestamps in web app, verify audio matches)

---

## Cost Estimates

| Service | Cost | Usage | Total |
|---------|------|-------|-------|
| Deepgram | $0.0043/min | 50 companies × 4 calls × 60 min | $52 |
| Claude API | ~$3/million tokens | 200 calls × 50k tokens | $30 |
| Supabase | Free tier | < 500 MB database | $0 |
| **Total (one-time backfill)** | | | **$82** |

**Ongoing costs** (per quarter):
- 50 companies × 1 new call × ($0.26 Deepgram + $0.15 Claude) = **$20/quarter**

---

## Future Enhancements

### Phase 9+: Additional Features

1. **Web Interface**
   - View all earnings for a company
   - Interactive audio player with clickable timestamps
   - Search across all earnings calls
   - Compare quarters/years

2. **Advanced Analysis**
   - Sentiment analysis over time
   - Compare management tone quarter-over-quarter
   - Track recurring themes/concerns
   - Generate earnings summary reports

3. **Alerts & Notifications**
   - Email when new earnings call is processed
   - Alert on significant guidance changes
   - Track companies with repeated concerns

4. **Export & Sharing**
   - Export insights to PDF
   - Share earnings summaries
   - API for external integrations

5. **Additional Data Sources**
   - Investor relations websites (backup for Seeking Alpha)
   - Transcripts from other providers
   - Financial data APIs (validate Claude extractions)

---

## Success Criteria

**Phase 1-7 Complete When**:
- ✅ 50 companies in database
- ✅ 200 earnings calls backfilled (50 × 4 quarters)
- ✅ All calls processed with insights
- ✅ Transcripts aligned with audio timestamps
- ✅ Claude analysis includes timestamps for all insights
- ✅ Database populated with structured insights

**Quality Checks**:
- Transcript alignment accuracy > 90%
- Claude analysis includes all required fields
- Timestamps match audio within 2-3 seconds
- Notable quotes are actual quotes from transcript

---

## Timeline Estimate

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| 1. Database Setup | Create tables, migrations | 2 hours |
| 2. Transcript Aligner | Core alignment logic | 6-8 hours |
| 3. Seeking Alpha Scraper | Navigation, extraction | 8-10 hours |
| 4. Company Management | Initialize, discover IR URLs | 3-4 hours |
| 5. Backfill Script | Fetch earnings calls | 4-5 hours |
| 6. Claude Analysis | Prompts, analyzer | 4-5 hours |
| 7. Processing Script | Main orchestrator | 3-4 hours |
| 8. Testing & Validation | Unit + integration tests | 4-6 hours |
| **Total** | | **34-44 hours** |

---

## Getting Started

**Immediate Next Steps**:

1. **Create database migration**
   ```bash
   # Create migration file
   touch supabase/migrations/014_create_earnings_tables.sql
   # Add schema from this document
   # Apply migration
   ```

2. **Prepare company list**
   - Compile list of 50 stock symbols
   - Add to `scripts/earnings_insights/initialize_companies.py`

3. **Set up Deepgram account**
   - Sign up at deepgram.com
   - Get API key
   - Add to `.env.local`: `DEEPGRAM_API_KEY=...`

4. **Test Seeking Alpha access**
   - Check if login required
   - If yes, set up authentication in browser sessions table

5. **Implement core utilities first**
   - Start with `transcript_aligner.py`
   - Test with sample audio + transcript
   - Validate alignment accuracy

---

## Questions to Resolve Before Starting

1. **Stock list**: Do you have the 50 companies selected? Which sectors/industries?
2. **Seeking Alpha access**: Can you access transcripts without login? Or need authentication?
3. **Priority**: Which companies should we process first for testing?
4. **Deepgram account**: Do you already have one, or should I include setup instructions?
5. **Timeline**: Do you want to implement this in one go, or phase by phase?

---

*End of Implementation Plan*