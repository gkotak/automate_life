# Authentication & Cookie Management

This document explains how to manage browser sessions for accessing paywalled content.

## Overview

The backend needs authenticated browser sessions (cookies) to access paywalled content from sites like:
- Substack newsletters
- Medium premium articles
- Seeking Alpha
- And other subscription-based content

## Current Workflow

### 1. Create Browser Session Locally

Run this script on your **local machine** (NOT on Railway):

```bash
cd programs/article_summarizer_backend
python auth/create_session.py
```

**What this does:**
1. Opens a Chromium browser window (visible, not headless)
2. Navigates to Substack login page
3. Waits for you to manually log in
4. Press Enter after you've logged in
5. Saves your authenticated session to `auth/storage_state.json`

**Important:**
- The browser window will open on your screen
- You need to manually log in to all the sites you want to access
- Currently the script only goes to Substack, but you can modify it to visit other sites
- Your session includes cookies for all domains you visit during the session

### 2. Upload Session to Supabase

After creating the session file, upload it to Supabase:

```bash
cd programs/article_summarizer_backend
python auth/upload_session_to_supabase.py --platform all
```

**What this does:**
1. Reads `auth/storage_state.json`
2. Uploads cookies and session data to Supabase `browser_sessions` table
3. Railway backend will automatically load these cookies on startup

**Environment Variables Required:**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SECRET_KEY` - Your Supabase secret key

### 3. Railway Backend Automatically Loads Cookies

When the backend starts on Railway, it:
1. Loads cookies from Supabase via `core/authentication.py`
2. Injects these cookies into all HTTP requests
3. Falls back to Playwright browser if needed

## When to Re-Export Cookies

You need to re-export and upload cookies when:
- **Sessions expire** (usually after 30-90 days)
- **You change your password** on any platform
- **You add new subscription sites** that need authentication
- **Cookies stop working** (you'll see authentication errors in logs)

## Files Involved

### Active Files (all in `auth/` folder):
- `auth/create_session.py` - Creates local browser session (run this first)
- `auth/upload_session_to_supabase.py` - Uploads session to Supabase (run this second)
- `auth/create_sessions_table.sql` - Database schema
- `auth/storage_state.json` - Local session file (gitignored)

### Core Code:
- `core/authentication.py` - Loads cookies on Railway startup

### Database:
- Supabase table: `browser_sessions`
- Schema: See `auth/create_sessions_table.sql`

## Troubleshooting

### "No active browser session found"
- You need to create and upload a session first
- Run: `python auth/create_session.py` then `python auth/upload_session_to_supabase.py`

### "Authentication failed" or "Paywall detected"
- Your session may have expired
- Re-run the export workflow to refresh cookies

### Playwright not available
- Install: `pip install playwright && playwright install chromium`

## Security Notes

- Session files contain authentication cookies - never commit to git
- Cookies are stored in Supabase with encryption at rest
- Sessions expire after 30 days (configurable)
- Only store cookies for sites you personally have access to
