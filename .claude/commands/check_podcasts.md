# check_podcasts

Execute the podcast checker to scan your in-progress podcast episodes from PocketCasts, and optionally process them with article_summarizer.

```bash
python3 programs/check_new_posts/processors/podcast_checker.py $ARGUMENTS
```

## Usage Examples

### Check Only (no arguments)
```
/check_podcasts
```
Just checks for new podcasts without processing.

### Process N Podcasts
```
/check_podcasts 5
```
Checks for new podcasts AND processes the 5 most recent unprocessed ones.

### Interactive Mode
```
/check_podcasts --process
```
Checks for new podcasts, shows list, and prompts for how many to process.

## What This Does

1. **Always**: Checks PocketCasts for in-progress episodes and tracks new ones
2. **If number provided**: Processes that many of the most recent unprocessed podcasts with article_summarizer
3. **If --process flag**: Shows interactive prompt to select how many to process

When processing podcasts:
- Queries Supabase to find which podcasts are already processed
- Sorts unprocessed podcasts by discovery date (most recent first)
- Calls article_summarizer.py for each selected podcast URL
- Prefers YouTube URLs over PocketCasts URLs (better transcripts)
- Shows success/failure status for each
- 10-minute timeout per podcast

## Output

After completion, you'll see:
- Summary of newly discovered podcast episodes
- List of processed podcasts (if processing mode used)
- Success/failure status for each processed podcast
- Episode URLs and article IDs for reference

## Requirements

First-time setup requires credentials in `.env.local`:
```
POCKETCASTS_EMAIL=your-email@example.com
POCKETCASTS_PASSWORD=your-password
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
```

## Technical Details

- Uses unofficial PocketCasts API to fetch in-progress episodes
- Tracks episodes in: `programs/check_new_posts/output/processed_podcasts.json`
- Checks Supabase `articles` table to find unprocessed podcasts
- Processes via: `programs/article_summarizer_backend/app/services/article_processor.py`
- Processed articles viewable at: http://localhost:3000
- Does not require PocketCasts Plus subscription
