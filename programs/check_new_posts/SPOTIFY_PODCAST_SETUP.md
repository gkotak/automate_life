# Spotify Podcast Tracking Setup

This guide will help you set up the Spotify podcast tracking feature to automatically track podcast episodes you've recently listened to.

## Overview

The podcast tracker integrates with Spotify's API to:
- Fetch your recently played podcast episodes (last 50 items)
- Track which episodes are new since the last check
- Store episode details including show name, episode title, play time, and Spotify URLs
- Maintain a database similar to the existing post tracking system

## Initial Setup

### 1. Create a Spotify Application

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click **"Create app"**
4. Fill in the details:
   - **App name**: "Podcast Tracker" (or any name you prefer)
   - **App description**: "Personal podcast tracking automation"
   - **Redirect URI**: `http://localhost:8888/callback`
   - **API/SDKs**: Select "Web API"
5. Check the terms of service agreement
6. Click **"Save"**
7. On the app page, click **"Settings"**
8. Copy your **Client ID** and **Client Secret**

### 2. Configure Environment Variables

1. Open your `.env.local` file (or create it from `.env.example`)
2. Add the following lines with your credentials:

```bash
# Spotify API Credentials
SPOTIFY_CLIENT_ID=your-client-id-here
SPOTIFY_CLIENT_SECRET=your-client-secret-here
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
```

**Important**: Keep your Client Secret confidential. Never commit `.env.local` to version control.

### 3. First-Time Authentication

The first time you run the podcast checker, it will:

1. Open your browser automatically
2. Ask you to log in to Spotify (if not already logged in)
3. Request permission to access your recently played tracks
4. Redirect you to a local callback page
5. Save authentication tokens for future use

The tokens are stored in: `programs/check_new_posts/output/.spotify_tokens.json`

These tokens will be automatically refreshed when they expire, so you only need to authenticate once.

## Usage

### Using the Claude Command

The easiest way to check for new podcasts:

```bash
/check_podcasts
```

This command will:
- Authenticate with Spotify (or use cached tokens)
- Fetch your recently played episodes
- Show new episodes discovered since last run
- Save all data to `processed_podcasts.json`

### Using the Python Script Directly

```bash
python3 programs/check_new_posts/processors/podcast_checker.py
```

### Expected Output

When new podcast episodes are found:

```
🎧 Starting Spotify podcast check...
📋 Loaded 5 previously tracked podcasts
🎵 Fetching last 50 recently played items from Spotify...
✅ Retrieved 50 recently played items
🔍 Processing 50 recently played items...
   🎙️ EPISODE 1: The Future of AI in Product Development
      📺 Show: Lenny's Podcast
      ✅ Episode is NEW (not in tracking database)
      📋 NEW PODCAST ADDED TO TRACKING

📋 Found 3 new podcast episodes:
================================================================================
1. The Future of AI in Product Development
   🎙️ Lenny's Podcast | ⏰ Played: 2025-10-14 10:30
   🔗 https://open.spotify.com/episode/abc123...

2. Building in Public: A Founder's Journey
   🎙️ How I Built This | ⏰ Played: 2025-10-13 15:45
   🔗 https://open.spotify.com/episode/def456...

3. The Science of Decision Making
   🎙️ Huberman Lab | ⏰ Played: 2025-10-12 08:00
   🔗 https://open.spotify.com/episode/ghi789...
================================================================================
💡 These podcast episodes have been tracked.
   Future integration: Process with article summarizer for transcripts

🎉 SUCCESS: Found 3 new podcast episodes!
```

## Data Storage

### Tracked Podcasts File

Location: `programs/check_new_posts/output/processed_podcasts.json`

Structure:
```json
{
  "episode_hash_123": {
    "episode_title": "Episode Name",
    "episode_description": "Brief description...",
    "show_name": "Podcast Name",
    "show_publisher": "Publisher Name",
    "show_id": "spotify_show_id",
    "episode_id": "spotify_episode_id",
    "episode_url": "spotify:episode:xxx",
    "web_url": "https://open.spotify.com/episode/xxx",
    "show_rss_feed": null,
    "duration_ms": 3600000,
    "release_date": "2025-10-01",
    "played_at": "2025-10-14T10:30:00Z",
    "found_at": "2025-10-14T13:00:00",
    "status": "discovered",
    "platform": "spotify_podcast"
  }
}
```

### Token Storage

Location: `programs/check_new_posts/output/.spotify_tokens.json`

This file contains:
- Access token (expires after 1 hour)
- Refresh token (used to get new access tokens)
- Expiration timestamp

**Note**: This file is automatically managed. Do not edit manually.

## Troubleshooting

### "Spotify credentials not found in environment"

**Solution**: Make sure you've added `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` to your `.env.local` file.

### "Failed to receive authorization code"

**Solution**:
- Check that the redirect URI is exactly: `http://localhost:8888/callback`
- Make sure port 8888 is not already in use
- Verify the redirect URI is added in your Spotify app settings

### "Token expired" or authentication errors

**Solution**:
- Delete `.spotify_tokens.json` and re-authenticate
- The system will automatically refresh tokens, but if it fails, manual re-auth is needed

### No podcast episodes found

**Possible reasons**:
- You haven't listened to any podcasts recently on Spotify
- All episodes have already been tracked (run the script again after listening to new episodes)
- The Spotify API only returns items from approximately the last 30 days

## Integration with Existing System

The podcast tracking system is designed to mirror the existing post tracking system:

### Similar Features
- Uses `BaseProcessor` for logging and session management
- Stores data in JSON format with similar structure
- Status tracking: "discovered", "processing", "completed", etc.
- Automatic cleanup of old entries (30 days)
- Hash-based deduplication

### Future Enhancements
- Integration with article summarizer to process podcast transcripts
- Batch processing commands via `post_manager.py`
- RSS feed fetching for episodes (when available)
- Export episode lists to other formats

## Architecture

```
programs/check_new_posts/
├── common/
│   ├── spotify_auth.py          # OAuth 2.0 authentication handler
│   └── base.py                   # Shared base processor
├── processors/
│   └── podcast_checker.py        # Main podcast tracking logic
├── output/
│   ├── processed_podcasts.json   # Tracked episodes database
│   └── .spotify_tokens.json      # OAuth tokens (auto-generated)
└── logs/
    └── podcast_checker.log       # Execution logs
```

## Privacy & Security

- **OAuth tokens are stored locally** in `.spotify_tokens.json`
- **No passwords are stored** - uses OAuth 2.0 flow
- **Minimal permissions requested** - only "user-read-recently-played"
- **Data stays local** - all podcast data is stored on your machine
- **Tokens auto-refresh** - no need to re-authenticate frequently

## API Rate Limits

Spotify's API has rate limits, but for personal use (checking recently played podcasts once or a few times per day), you should never hit these limits.

If you see rate limit errors:
- Wait a few minutes before trying again
- Reduce checking frequency
- The API allows approximately 180 requests per minute for most endpoints

## Additional Resources

- [Spotify Web API Documentation](https://developer.spotify.com/documentation/web-api)
- [OAuth 2.0 Authorization Guide](https://developer.spotify.com/documentation/web-api/concepts/authorization)
- [Recently Played Endpoint Reference](https://developer.spotify.com/documentation/web-api/reference/get-recently-played)
