# Check New Posts

Check for new newsletter and blog posts from configured RSS feeds and content sources via the content_checker_backend API.

```bash
python3 scripts/check_posts.py
```

## What This Does

1. Calls the content_checker_backend API (`POST /api/posts/check`)
2. Backend scans all active content sources from the `content_sources` table
3. Extracts posts from RSS/Atom feeds and web pages
4. Filters posts by recency (last 3 days)
5. Saves newly discovered posts to `content_queue` table
6. Returns summary of newly discovered posts

## Output

After completion, you'll see:
- Total number of new posts found
- Total number of sources checked
- List of newly discovered post IDs

Example:
```
📰 Checking for new newsletter/blog posts...
📡 API: http://localhost:8001

✅ Found 5 new posts from 4 sources
📊 New posts: 5
📊 Sources checked: 4

🆕 Newly discovered posts (5):
   - abc123-def456-...
   - xyz789-uvw012-...
   - ghi345-jkl678-...
```

## Next Steps

To process discovered posts:
- View them at http://localhost:3000/admin/posts
- Click "Process" on any post to summarize it
- Or use `/article_summarizer <url>` to process directly

## Requirements

Backend must be running: `content_checker_backend` on port 8001

Environment variables in `programs/content_checker_backend/.env.local`:
```
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-supabase-key
```

## Technical Details

- CLI wrapper: `scripts/check_posts.py`
- Backend API: `content_checker_backend` (FastAPI, async)
- Service: `app/services/post_checker.py`
- Uses feedparser for RSS/Atom parsing
- Platform detection for Substack, Medium, generic blogs
- Data stored in: `content_queue` table (Supabase)
- View UI at: http://localhost:3000/admin/posts
