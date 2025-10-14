# Check Podcasts

Run the Spotify podcast checker to scan your recently played podcasts and track new episodes.

## Instructions

1. Run the podcast checker script to fetch recently played episodes from Spotify
2. First run will require Spotify authentication (browser will open)
3. Subsequent runs will use stored tokens automatically
4. Wait for the script to complete and capture the output
5. After completion, display a summary of the newly discovered podcast episodes showing:
   - Total number of new episodes found
   - List of new episodes with show names and play times
   - Episode URLs for reference
6. If no new episodes were found, clearly state that
7. Provide information about tracked podcasts

## Technical Details

- Podcast checker location: `programs/check_new_posts/processors/podcast_checker.py`
- Tracking file: `programs/check_new_posts/output/processed_podcasts.json`
- Token storage: `programs/check_new_posts/output/.spotify_tokens.json`
- All newly discovered episodes will have status "discovered"
- Fetches last 50 recently played items from Spotify
- Filters for podcast episodes only
- Requires Spotify API credentials in `.env.local`

## Setup (First Time Only)

If not already configured:
1. Go to https://developer.spotify.com/dashboard
2. Create a new app
3. Add redirect URI: `http://localhost:8888/callback`
4. Copy Client ID and Client Secret to `.env.local`:
   ```
   SPOTIFY_CLIENT_ID=your-client-id
   SPOTIFY_CLIENT_SECRET=your-client-secret
   SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
   ```
