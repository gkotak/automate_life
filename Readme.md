# Automate Life - Personal Content Processing System

Hey! Let me show you what I've built - it's a personal automation system that helps me process and manage all the content I consume (articles, podcasts, YouTube videos) in one place.

## What Does It Do?

Think of it as a **smart content library with AI-powered summaries**. I can throw any URL at it - a Stratechery article, a podcast episode, a YouTube video - and it will:

1. **Extract the content** (text, audio, video transcripts)
2. **Generate an AI summary** with key insights and quotes
3. **Create clickable timestamps** for audio/video content
4. **Store everything in a searchable database**
5. **Give me a beautiful web interface** to browse and search everything.

There are also scripts that find the right URL (new posts, youtube videos or podcasts), and automatically summarizes them using the steps above

Over time, I plan to have 1000s of articles / content. You can access it here - https://automate-life.vercel.app/. Here you can:

- Browse all my processed content
- Filter by content type (video, audio, article)
- Filter by source (Stratechery, Lenny's Newsletter, etc.)
- Search semantically: "articles about supply chain dynamics"
- Click timestamps to jump to specific moments in audio/video

## Why Did I Build This?

I consume a lot of content - articles, podcasts, videos - and wanted a better way to:
1. **Remember what I've learned** (keyword and semantic search across all content added to the database)
2. For new content, **quickly peruse the summaries to determine if worth going through the whole content** which could be an hour-long podcast
3. **Learn how to code using AI.** I built all this in less than a week using claude code and some manual coding. It's over 30K lines of code. I think it has lots of cool features. You can see both features, architecture and code base below.

## The Cool Parts

### 🎯 Smart Content Detection
The system automatically figures out what kind of content you're giving it:
- **YouTube videos**: Extracts transcripts and creates timestamp-based summaries
- **Podcasts** (Pocket Casts, Apple Podcasts): Downloads audio, transcribes it with Whisper AI
- **Articles** (Substack, Stratechery, blogs): Extracts text and handles paywalls intelligently

### 🤖 AI-Powered Analysis
Uses Claude AI to generate:
- Concise summaries (~1000 words)
- Key insights with timestamps
- Memorable quotes with exact timestamps
- Topic tags and metadata

### 🎵 Audio Transcription Magic
- Automatically transcribes podcast audio using OpenAI Whisper
- Handles large files by chunking them into 10-minute segments
- Creates clickable timestamps that sync with 2x speed playback
- Works with 60+ minute podcasts without issues

### 🔍 Semantic Search
- Search your entire library using natural language
- "Find articles about AI and China" actually understands what you mean
- Uses embeddings for smart matching beyond keyword search

### 🌐 Smart Authentication
- Handles paywalled content (Substack, Medium, Stratechery)
- Detects when URLs already have access tokens
- Falls back to browser automation (Playwright) only when needed
- Supports multiple platforms with stored credentials

### 📡 Automated Content Discovery (`check_new_posts`)
The system can automatically discover new content without manual input, then optionally processes each post and add it to the database

**Newsletter & Blog Monitoring:**
- Reads a list of RSS feeds and newsletter URLs from `newsletter_podcast_links.md`
- Checks for new posts in the last 3 days

**Podcast Listening History (Pocket Casts Integration):**
- Connects to Pocket Casts API with your credentials
- Fetches your listening history


## The Tech Stack

### Backend Processing
- **Python** - Core processing logic
- **BeautifulSoup** - Web scraping and content extraction
- **Playwright** - Browser automation for paywalled content
- **Whisper API** - Audio transcription (OpenAI)
- **pydub** - Audio file manipulation and chunking
- **Claude AI** - Content summarization and analysis

### Storage & Search
- **Supabase** - PostgreSQL database for all content
- **pgvector** - Vector storage for semantic search
- **OpenAI Embeddings** - Generate searchable vector representations

### Web Interface
- **Next.js 15** - Modern React framework
- **TypeScript** - Type-safe frontend code
- **Tailwind CSS** - Beautiful, responsive UI
- **Vercel** - Production hosting (see below)

### Development Tools
- **Claude Code** - AI pair programming assistant (that's me!)
- **OpenAI Codex** - Automated code review on commits
- **Git hooks** - Pre-commit code quality checks

## Hosting Architecture

### Current Setup (Hybrid)

**Frontend (Next.js Web App):**
- ✅ **Hosted on Vercel** - https://automate-life.vercel.app/
- Connects to Supabase for database queries
- Provides web interface for browsing and searching
- Fully deployed and accessible from anywhere

**Backend (Python Processing):**
- 🖥️ **Runs locally** on your machine
- Handles article/podcast processing
- Performs AI summarization (Claude API)
- Manages audio transcription (Whisper API)
- Monitors RSS feeds and Pocket Casts

**Why This Split?**
- Frontend can be hosted cheaply/free on Vercel
- Python backend requires API keys and local file processing
- Processing is heavy (audio transcription, AI analysis)
- Currently triggered manually via slash commands. In the future, I'll build a dockerized python server

**Database & Search:**
- **Supabase** - Cloud-hosted PostgreSQL
- Accessible from both local Python and Vercel frontend
- Stores all processed content and embeddings

## Source Code

The full source code is available on GitHub:
**https://github.com/gkotak/automate_life**

Feel free to fork, explore, or contribute!

## Cool Features I'm Proud Of

### 1. **Intelligent Platform Detection**
The system knows how to handle each platform differently:
- **Stratechery**: Detects access tokens, uses og:title for accurate titles
- **Pocket Casts**: Finds embedded MP3 links, extracts podcast metadata
- **YouTube**: Gets transcripts directly, no transcription needed
- **Substack**: Handles authentication, extracts clean article text

### 2. **Audio Chunking System**
When a podcast is >25MB (Whisper API limit), it:
- Splits into 10-minute chunks automatically
- Transcribes each chunk in sequence
- Adjusts timestamps to account for offsets
- Reassembles into one seamless transcript

### 3. **Semantic Search with pgvector + OpenAI Embeddings**
The web app uses hybrid search combining traditional keywords with AI-powered semantic understanding:
- **Vector Embeddings**: Each article converted to 1536-dimensional vectors using OpenAI's `text-embedding-3-small`
- **pgvector Storage**: Vectors stored in PostgreSQL using pgvector extension for efficient similarity search
- **Cosine Similarity**: Finds semantically similar content even without exact keyword matches
- **Hybrid Ranking**: Combines keyword relevance with vector similarity for optimal results
- **Real Example**: Search "China's economic strategy" → finds articles about manufacturing, trade policy, geopolitics

### 4. **Automated Code Review**
Before every git commit:
- OpenAI Codex reviews the code changes
- Blocks commits if critical issues (🔥) are found
- Saves review to `.codex/last_review.md`
- Can bypass with `SKIP_CODEX=1` if needed

## Project Structure

```
automate_life/
├── programs/
│   ├── article_summarizer/        # Main content processor
│   │   ├── scripts/               # Core Python scripts
│   │   │   └── article_summarizer.py
│   │   ├── common/                # Shared utilities
│   │   │   ├── authentication.py  # Paywall handling
│   │   │   ├── content_detector.py # Video/audio detection
│   │   │   └── browser_fetcher.py # Playwright automation
├── web-apps/
│   └── article-summarizer/        # Next.js frontend
│       └── src/
│           ├── components/        # React components
│           └── app/               # Next.js app router
│   └── check_new_posts/           # Automated content discovery
│       ├── processors/
│       │   ├── post_checker.py    # Newsletter/RSS monitoring
│       │   └── podcast_checker.py # Pocket Casts integration
│       ├── scripts/
│       │   ├── post_manager.py    # CLI for managing discovered posts
│       │   └── quick_process.sh   # Batch processing wrapper
│       ├── common/
│       │   ├── podcast_auth.py    # Pocket Casts authentication
│       │   └── url_utils.py       # URL normalization
│       ├── output/
│       │   ├── processed_posts.json    # Newsletter/blog tracking
│       │   └── processed_podcasts.json # Podcast history tracking
│       └── newsletter_podcast_links.md # Content source configuration
├── scripts/
│   └── run_codex_review.sh        # Pre-commit code review
├── .claude/
│   └── commands/                  # Custom slash commands
└── CLAUDE.md                      # AI assistant instructions
```


## Future Ideas

### Near-Term Improvements

**1. Move Python Backend to Server**
Currently, Python processing runs locally. The plan is to deploy it as a separate service:

- **Architecture**: Python FastAPI server
- **Hosting Options**: Railway, Fly.io, or dedicated VPS
- **Benefits**:
  - Process content from anywhere (not just local machine)
  - Scheduled background jobs (automated RSS checking)
  - Webhook support (process on-demand via API)
  - Better resource management for long-running tasks


### Other features I'm thinking about:
- **Mobile app** for reading on the go, or at least a better responsibe user interface
- **Email integration** to process newsletter emails directly by forward to an address
- **Export to notebookLM** to benefit from additional summarization there
- **Browser extension** for one-click content processing
- **Dedicted intelligence for my earnings calls and stock recommendation articles**

## How to Get Started

### For Users (Just Browse)

Visit the live web app: **https://automate-life.vercel.app/**

You can browse my processed content library without any setup!

### For Developers (Run It Yourself)

1. **Clone the repo from GitHub**:
   ```bash
   git clone https://github.com/gkotak/automate_life.git
   cd automate_life
   ```

2. **Set up environment variables** (`.env.local`):
   - Supabase credentials (database URL + anon key)
   - OpenAI API key (for Whisper transcription + embeddings)
   - Anthropic API key (for Claude AI summaries)
   - Optional: Pocket Casts credentials for podcast tracking

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pydub  # For audio chunking
   brew install ffmpeg  # Required by pydub
   ```

4. **Install frontend dependencies**:
   ```bash
   cd web-apps/article-summarizer
   npm install
   ```

5. **Run the web app locally**:
   ```bash
   npm run dev
   # Visit http://localhost:3000
   ```

6. **Process your first article** (requires Claude Code or Python):
   ```bash
   /article_summarizer https://example.com/article
   # Or run Python directly:
   python3 programs/article_summarizer/scripts/article_summarizer.py "URL"
   ```

7. **Set up automated content discovery** (optional):
   - Edit `programs/check_new_posts/newsletter_podcast_links.md`
   - Add your RSS feeds and newsletter URLs
   - Run `python3 programs/check_new_posts/processors/post_checker.py`


---

## Questions or Want to Contribute?

- 📦 **Source Code**: https://github.com/gkotak/automate_life
- 💬 **Issues/Suggestions**: Open an issue on GitHub

Feel free to:
- Fork the repo and customize it for your needs
- Submit pull requests with improvements
- Open issues for bugs or feature requests
- Star the repo if you find it useful!
