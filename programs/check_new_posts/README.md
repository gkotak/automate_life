# Check New Posts

A program to automatically check for new posts from configured newsletter/podcast feeds and track them for processing.

## Overview

This program monitors RSS feeds and newsletter platforms for new content, tracks discovered posts, and prepares them for processing by the article summarizer.

## Features

- **Multi-platform Support**: RSS feeds, Substack, Medium, YouTube, and more
- **Smart Duplicate Detection**: Uses URL normalization to prevent duplicate tracking
- **Post Management**: CLI tools to list, filter, and batch process discovered posts
- **Recency Filtering**: Only tracks posts from the last 3 days
- **Status Tracking**: Tracks posts through discovered → processing → completed states

## Directory Structure

```
check_new_posts/
├── common/                         # Shared utilities
│   ├── base.py                     # Base processor class
│   ├── config.py                   # Configuration constants
│   └── url_utils.py                # URL normalization utilities
├── processors/
│   └── post_checker.py             # Main post checking logic
├── scripts/
│   ├── post_manager.py             # Post management CLI
│   └── quick_process.sh            # Quick wrapper script
├── newsletter_podcast_links.md     # List of feeds to monitor
├── logs/                           # Processing logs
└── README.md                       # This file
```

## Configuration

### Newsletter Links

Edit [newsletter_podcast_links.md](newsletter_podcast_links.md) to configure which feeds to monitor:

```markdown
# Newsletter links

## RSS Feeds
https://stratechery.passport.online/feed/podcast/2veiQRnCGxpwgPx1N8i91Q

## Newsletter Sites
https://www.lennysnewsletter.com/
https://creatoreconomy.so/
```

## Usage

### Check for New Posts

Run the post checker to scan all configured feeds:

```bash
cd programs/check_new_posts
python3 processors/post_checker.py
```

This will:
1. Read feed URLs from newsletter_podcast_links.md
2. Check each feed for new posts
3. Filter for posts from the last 3 days
4. Add new posts to processed_posts.json with status "discovered"

### Manage Posts

Use the post manager CLI for advanced operations:

```bash
cd programs/check_new_posts/scripts

# List discovered posts
python3 post_manager.py list --status=discovered

# List posts with filters
python3 post_manager.py list --status=discovered --source=stratechery --limit=5

# View statistics
python3 post_manager.py stats

# Update post status
python3 post_manager.py update <post_id> --status=skipped

# Process posts (calls article summarizer)
python3 post_manager.py process <post_id1> <post_id2>

# Bulk process discovered posts
python3 post_manager.py bulk --status=discovered --action=process --limit=5
```

### Quick Process Script

Use the wrapper script for common operations:

```bash
cd programs/check_new_posts/scripts

# Check for new posts
./quick_process.sh check

# View statistics
./quick_process.sh stats

# Process first 3 discovered posts
./quick_process.sh process 3

# Show only Stratechery posts
./quick_process.sh stratechery

# Show only Lenny's Newsletter posts
./quick_process.sh lenny

# Export URLs for external processing
./quick_process.sh urls stratechery

# Bulk process 10 posts
./quick_process.sh bulk 10
```

## Post Tracking

Posts are tracked in Supabase database (content_queue table)

Each post has:
- **post_id**: Unique hash based on title and normalized URL
- **title**: Post title
- **url**: Full URL
- **platform**: Detected platform (rss_feed, substack, etc.)
- **status**: Current state (discovered, processing, completed, failed, skipped)
- **found_at**: Timestamp when discovered
- **source_feed**: Original feed URL
- **published_date**: Publication date (if available)

## Post Statuses

- **discovered**: Found but not yet processed
- **processing**: Currently being processed
- **completed**: Successfully processed
- **failed**: Processing failed
- **skipped**: Manually marked to skip
- **queued**: Queued for future processing

## Integration

This program integrates with the article_summarizer backend:

- **Shared Data**: Uses Supabase database (content_queue table) for tracking
- **Processing**: Calls article_summarizer backend processor
- **Output**: Processed summaries are stored in Supabase articles table

## Logs

Processing logs are stored in `logs/`:
- `post_checker.log`: Post checking operations
- `post_manager.log`: Post management operations

Logs automatically rotate when they exceed 10MB.

## Dependencies

Python packages required:
- requests
- beautifulsoup4
- feedparser
- python-dotenv

Install with:
```bash
pip3 install requests beautifulsoup4 feedparser python-dotenv
```

## Environment Variables

Optional authentication for protected content:
- `NEWSLETTER_SESSION_COOKIES`: Session cookies for authenticated feeds
- `USER_AGENT`: Custom user agent string

See root `.env.local` or `.env` file for configuration.
