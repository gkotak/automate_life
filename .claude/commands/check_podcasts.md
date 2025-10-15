# Check Podcasts

Run the podcast checker to scan your in-progress podcast episodes from PocketCasts.

## Instructions

1. Run the podcast checker script to fetch in-progress episodes
2. First run will require PocketCasts credentials in `.env.local`
3. Wait for the script to complete and capture the output
4. After completion, display a summary of the newly discovered podcast episodes showing:
   - Total number of new episodes found
   - List of new episodes with podcast names and progress
   - Episode URLs for reference
5. If no new episodes were found, clearly state that
6. Provide information about tracked podcasts

## Technical Details

- Podcast checker location: `programs/check_new_posts/processors/podcast_checker.py`
- Tracking file: `programs/check_new_posts/output/processed_podcasts.json`
- Uses unofficial PocketCasts API via direct API calls
- Fetches all in-progress episodes (episodes you've started listening to)
- Requires PocketCasts account credentials in `.env.local`

## Setup (First Time Only)

If not already configured, add credentials to `.env.local`:
```
POCKETCASTS_EMAIL=your-email@example.com
POCKETCASTS_PASSWORD=your-password
```

## Notes

- This uses the **unofficial** PocketCasts API
- Only tracks episodes that are "in progress" (started but not finished)
- Does not require PocketCasts Plus subscription
- Episode URLs are in format: https://pocketcasts.com/episode/{uuid}
