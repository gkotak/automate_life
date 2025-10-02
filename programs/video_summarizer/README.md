# Video Summarizer Program

## Purpose

The Video Summarizer is an intelligent content analysis system designed to automatically discover, process, and summarize video-rich articles from newsletters, blogs, and podcast platforms. It transforms long-form video content into accessible, interactive summaries with accurate timestamps and key insights.

### Key Objectives
- **Automated Content Discovery**: Monitor RSS feeds and platform URLs for new posts
- **Intelligent Video Analysis**: Extract and analyze YouTube transcripts from embedded videos
- **Interactive Summaries**: Generate HTML summaries with clickable timestamps
- **Knowledge Management**: Build a searchable collection of processed content
- **Daily Automation**: Run continuously with minimal manual intervention

## Workflow

### 1. Daily Content Discovery
```
RSS Feeds & Platform URLs → New Post Detection → Recency Filter (3 days) → Queue for Processing
```

- **Input Sources**: RSS feeds, newsletter URLs, blog platforms
- **Detection Logic**: Parse feeds and web pages for new article links
- **Recency Filter**: Only process content from the last 3 days
- **Duplicate Prevention**: Track processed posts to avoid reprocessing

### 2. Content Analysis Pipeline
```
Article URL → Platform Detection → Authentication → Video Extraction → Transcript Processing → AI Analysis
```

- **Platform Detection**: Identify content type (Substack, Medium, YouTube, etc.)
- **Smart Authentication**: Test access before attempting login, handle paywalls gracefully
- **Video Extraction**: Locate embedded YouTube videos and extract video IDs
- **Transcript Processing**: Fetch official YouTube transcripts (150k character limit)
- **AI Analysis**: Generate summaries, insights, and accurate timestamps using Claude

### 3. Output Generation
```
AI Analysis → HTML Template → Interactive Summary → Git Commit → Index Update
```

- **HTML Generation**: Create rich, interactive summaries with embedded video players
- **Timestamp Integration**: Clickable timestamps that jump to specific video moments
- **Index Management**: Maintain searchable collection with metadata
- **Version Control**: Automatically commit and push to GitHub

## High-Level Architecture

### Core Components

#### 1. Daily Post Checker (`daily_post_checker.py`)
- **RSS Feed Parser**: Uses feedparser for robust XML/RSS parsing
- **Platform Monitors**: Specialized extractors for different content platforms
- **Recency Engine**: 3-day sliding window for content freshness
- **Tracking Database**: JSON-based duplicate detection and cleanup

#### 2. Video Article Summarizer (`video_article_summarizer.py`)
- **Platform Detection Engine**: Identifies content source and authentication needs
- **Authentication Manager**: Smart login system with rate limiting and fallbacks
- **Media Extraction Pipeline**: Finds and processes YouTube video embeds
- **Transcript Processor**: 150k character YouTube transcript integration
- **AI Analysis Engine**: Claude-powered content analysis with strict validation

#### 3. Template System (`templates/`)
- **Interactive HTML Templates**: Rich UI with video embedding and timestamp navigation
- **Responsive Design**: Mobile-friendly layouts with modern CSS
- **JavaScript Integration**: Video control and timestamp jumping functionality

#### 4. Automation Infrastructure
- **Daily Check Script**: Shell wrapper for easy cron scheduling
- **Logging System**: Comprehensive session-based logging with rotation
- **Git Integration**: Automatic version control and GitHub synchronization

### Data Flow Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   RSS Feeds     │────│  Daily Checker   │────│  Post Queue     │
│   Platform URLs │    │  (New Content)   │    │  (3-day filter) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Auth System   │────│ Video Summarizer │────│ Transcript API  │
│  (Smart Login)  │    │   (Processing)   │    │   (YouTube)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Claude API     │────│   AI Analysis    │────│ HTML Generation│
│ (Summarization) │    │  (Insights + TS) │    │ (Interactive)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Git Repository │────│   Index Update   │────│  HTML Output    │
│ (Version Ctrl)  │    │  (Searchable)    │    │  (Summaries)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Key Design Principles

#### 1. **Accuracy Over Completeness**
- Strict timestamp validation prevents AI hallucination
- Only use timestamps from actual transcript data
- Graceful degradation when transcript unavailable

#### 2. **Intelligent Authentication**
- Test content access before attempting login
- Platform-specific authentication strategies
- Rate limiting and graceful failure handling

#### 3. **Scalable Processing**
- 150k character transcript limit for comprehensive coverage
- Efficient duplicate detection and cleanup
- Configurable recency windows and processing limits

#### 4. **Maintainable Architecture**
- Modular design with clear separation of concerns
- Comprehensive logging for debugging and monitoring
- Git-based version control for all generated content

## Configuration

### Essential Files
- `newsletter_podcast_links.md`: Platform URLs and RSS feeds to monitor
- `output/processed_posts.json`: Tracking database for duplicate prevention
- `.env.local`: Authentication credentials for various platforms
- `templates/article_summary.html`: HTML template for generated summaries

### Environment Variables
```bash
# Authentication (optional but recommended)
SUBSTACK_EMAIL=your_email@domain.com
SUBSTACK_PASSWORD=your_password
MEDIUM_SESSION_COOKIE=your_cookie
PATREON_SESSION_COOKIE=your_cookie
```

### Automation Setup
```bash
# Daily cron job (run at 9 AM daily)
0 9 * * * cd /path/to/video_summarizer && ./daily_check.sh

# Manual execution
./daily_check.sh
```

## Output

### Generated Files
- **HTML Summaries**: Interactive articles with embedded videos and clickable timestamps
- **Index Page**: Searchable collection with metadata and statistics
- **Processing Logs**: Detailed session logs for debugging and monitoring
- **Tracking Data**: JSON database of processed content

### Features
- **Interactive Video Player**: 2x speed default with timestamp navigation
- **Searchable Content**: Full-text search across all summaries
- **Mobile Responsive**: Optimized for all device sizes
- **Version Control**: All content automatically committed to Git

The Video Summarizer represents a complete solution for automated video content analysis, combining intelligent content discovery, robust processing pipelines, and rich interactive output generation.