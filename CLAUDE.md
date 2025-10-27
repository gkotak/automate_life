# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code configuration repository that automates content analysis and summarization. The primary focus is the article summarizer tool which processes articles, extracts video/audio content, and generates comprehensive summaries with interactive features.

## Key Commands

### Article Summarizer
- `/article_summarizer` - Processes articles and saves summaries to Supabase database
  - Extracts video/audio content from URLs
  - Generates AI-powered summaries with timestamps
  - Saves structured data to Supabase for dynamic rendering
  - View articles at http://localhost:3000 via Next.js web app

### Content Checker
- `python3 scripts/check_podcasts.py` - Checks PocketCasts for new podcast episodes
  - Scans listening history for new episodes
  - Uses SERPAPI for YouTube discovery (whitelisted podcasts)
  - Saves discoveries to content_queue table
  - View at http://localhost:3000/admin/podcasts

- `python3 scripts/check_posts.py` - Checks RSS feeds and newsletters for new posts
  - Scans content_sources table for active feeds
  - Extracts posts from RSS/Atom feeds and web pages
  - Filters by recency (last 3 days)
  - View at http://localhost:3000/admin/posts

## Architecture Overview

### Core System Components

**Article Summarizer Backend** (`programs/article_summarizer_backend/`)
- FastAPI backend for article processing with SSE streaming support
- Intelligent article content extraction with media detection
- YouTube transcript extraction and analysis
- AI-powered content summarization using Claude API
- Saves all data to Supabase database (no static files)
- Smart authentication for protected content (Substack, Medium, etc.)
- Railway deployment support with Docker

**Content Checker Backend** (`programs/content_checker_backend/`)
- FastAPI backend for discovering new content (podcasts and newsletters)
- Podcast checking via PocketCasts API with Playwright automation
- RSS/Atom feed parsing for newsletter/blog posts
- SERPAPI integration for YouTube video discovery
- Async architecture for efficient content scanning
- Railway deployment support with Docker

**File Organization**:
```
programs/article_summarizer_backend/
├── app/                        # FastAPI application
│   ├── main.py                 # API server
│   ├── routes/                 # API endpoints
│   ├── services/               # Article processor
│   └── middleware/             # Authentication
├── core/                       # Shared utilities
│   ├── authentication.py       # Playwright-based auth
│   ├── content_detector.py     # Media detection
│   └── event_emitter.py        # SSE events
└── processors/                 # Content processors

programs/content_checker_backend/
├── app/                        # FastAPI application
│   ├── main.py                 # API server (port 8001)
│   ├── routes/                 # API endpoints (podcasts, posts)
│   ├── services/               # Content checkers
│   ├── models/                 # Pydantic models
│   └── middleware/             # Authentication
└── core/                       # Shared utilities
    ├── podcast_auth.py         # PocketCasts authentication
    ├── browser_fetcher.py      # Playwright automation
    └── config.py               # Configuration

web-apps/article-summarizer/   # Next.js web interface (runs on port 3000)
├── src/                        # React components and pages
│   ├── app/admin/podcasts/     # Podcast admin page
│   └── app/admin/posts/        # Newsletter/blog admin page
├── public/                     # Static assets
└── package.json                # Dependencies

supabase/                       # Database infrastructure
├── migrations/                 # Historical schema changes
├── schemas/                    # Table definitions
├── functions/                  # SQL functions
└── tools/                      # Migration utilities

scripts/
├── check_podcasts.py           # CLI wrapper for podcast checking
├── check_posts.py              # CLI wrapper for post checking
└── article_summarizer/         # Utility scripts
    ├── backfill_embeddings.py  # Regenerate embeddings
    ├── backfill_sources.py     # Fix source names
    └── fix_pocketcasts_sources.py  # Data cleanup
```

**Configuration**:
```
.claude/
├── settings.local.json         # Claude Code permissions
└── commands/                   # Custom slash commands
```

### Processing Flow

1. **Content Extraction**: Analyze URL and detect video/audio/text content
2. **Media Processing**: Extract YouTube transcripts, identify main audio content
3. **AI Analysis**: Generate structured summary with timestamps using Claude
4. **Database Storage**: Save all data to Supabase (structured JSON data)
5. **Web App**: View articles dynamically at http://localhost:3000/article/{id}

### Content Standards

**Summary Output**: Structured JSON data saved to Supabase database
**Media Integration**: Web app provides 2x speed playback, clickable timestamps, interactive navigation
**Authentication**: Smart detection and handling of paywalled content
**Storage**: Database-first approach - no static HTML files generated

## Development Notes

- All processing uses Claude Code CLI for AI analysis
- System prioritizes main content over related/promotional material
- Timestamps are validated against actual transcript data
- Database stores structured JSON (key_insights, quotes, transcripts, etc.)
- Web app dynamically renders from Supabase - no static files
- Authentication framework supports multiple platforms (Substack, Medium, Patreon, etc.)
- To view summaries: `cd web-apps/article-summarizer && npm run dev`

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
Try to avoid duplicate code by creating utility functions/method where relevant and feasible
For python code, avoid having large functions/methods that do multiple things. try breaking into smallers methods and created high-level methods that call these specific smaller methods
NEVER start local servers for backend or frontend yourself. ask me to do so in the terminal when you need it


      IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.