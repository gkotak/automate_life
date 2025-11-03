# check_podcasts

Execute the podcast checker to scan your in-progress podcast episodes from PocketCasts via the content_checker_backend API.

```bash
python3 scripts/check_podcasts.py
```

## Usage Examples

### Check for New Podcasts
```
/check_podcasts
```
Checks PocketCasts listening history for new episodes and saves them to the database.

## What This Does

1. Calls the content_checker_backend API (`POST /api/podcasts/check`)
2. Backend checks PocketCasts listening history using authenticated browser automation
3. Discovers new episodes and saves them to the `content_queue` table
4. Finds YouTube URLs via `known_podcasts` table or PocketCasts page scraping
5. Returns summary of newly discovered episodes

To process discovered podcasts:
- View them at http://localhost:3000/admin/podcasts
- Click "Process" on any episode to summarize it
- Or use `/article_summarizer <url>` to process directly

## Output

After completion, you'll see:
- Total number of new episodes found
- Total number of podcasts checked
- List of newly discovered episode IDs

Example:
```
🎙️  Checking for new podcast episodes...
📡 API: http://localhost:8001

✅ Found 3 new podcast episodes
📊 New episodes: 3
📊 Podcasts checked: 15

🆕 Newly discovered episodes (3):
   - abc123-def456-...
   - xyz789-uvw012-...
   - ghi345-jkl678-...
```

## Requirements

Backend must be running: `content_checker_backend` on port 8001

Environment variables in `programs/content_checker_backend/.env.local`:
```
POCKETCASTS_EMAIL=your-email@example.com
POCKETCASTS_PASSWORD=your-password
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_ROLE_KEY=your-supabase-key
```

## Technical Details

- CLI wrapper: `scripts/check_podcasts.py`
- Backend API: `content_checker_backend` (FastAPI, async)
- Service: `app/services/podcast_checker.py`
- Uses Playwright for PocketCasts authentication
- YouTube discovery via free scraping (PocketCasts pages + YouTube playlists/channels)
- `known_podcasts` table for reliable YouTube URL associations
- Data stored in: `content_queue` table (Supabase)
- View UI at: http://localhost:3000/admin/podcasts
