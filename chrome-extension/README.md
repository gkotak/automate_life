# Particles - Chrome Extension

AI-powered article summarizer that processes any web page with one click. Features real-time progress tracking, duplicate detection, and seamless integration with your Particles account.

## Features

- **One-Click Processing**: Summarize the current page instantly from the side panel
- **Real-Time Progress**: Watch as your article is fetched, analyzed, and summarized with live SSE updates
- **Smart Duplicate Detection**: Automatically detects if an article was already processed
- **Force Reprocessing**: Option to reprocess articles even if they already exist
- **Authentication Integration**: Seamlessly detects your Particles session
- **Demo Video Support**: Toggle to extract frames from demo/screen-share videos
- **Private Articles**: Option to save articles privately to your organization

## Installation

### Development Mode (For Testing)

1. **Download or clone the extension**:
   ```bash
   cd chrome-extension
   ```

2. **Add your icon files** (see `icons/icon-creation-instructions.txt`):
   - Place `icon-16.png`, `icon-48.png`, and `icon-128.png` in the `icons/` folder

3. **Open Chrome and navigate to**:
   ```
   chrome://extensions/
   ```

4. **Enable Developer Mode**:
   - Toggle the switch in the top-right corner

5. **Click "Load unpacked"**:
   - Select the `chrome-extension` folder

6. **Pin the extension** (optional but recommended):
   - Click the puzzle icon in Chrome toolbar
   - Find "Particles - Article Summarizer"
   - Click the pin icon

### Production Distribution (For Sharing)

1. **Create a ZIP file**:
   ```bash
   cd chrome-extension
   zip -r automate-life-extension.zip . -x "*.git*" -x "README.md" -x "icon-creation-instructions.txt"
   ```

2. **Share the ZIP file** via:
   - GitHub Releases
   - Google Drive / Dropbox
   - Direct download link

3. **Users install by**:
   - Downloading and extracting the ZIP
   - Following the "Development Mode" instructions above

### Chrome Web Store Distribution (Future)

When ready for public distribution:

1. Create a Chrome Web Store developer account ($5 one-time fee)
2. Prepare store assets:
   - Screenshots (1280x800 or 640x400)
   - Promotional tile (440x280)
   - Detailed description
   - Privacy policy
3. Submit for review (typically 1-3 days)
4. Get public URL: `chrome.google.com/webstore/detail/[extension-id]`

## Usage

### First Time Setup

1. **Click the extension icon** in Chrome toolbar
2. **Sign in prompt appears** if you're not logged into Particles
3. **Click "Sign In"** - opens login page in new tab
4. **Sign in to Particles** with your credentials
5. **Return to extension** - it will automatically detect your session

### Processing an Article

1. **Navigate to any article** you want to summarize
2. **Click the extension icon** - side panel opens
3. **Review the page info** displayed at the top
4. **Optional: Toggle settings**:
   - ☑️ Extract demo video frames (for screen shares)
   - ☑️ Save as private article
5. **Click "Summarize This Page"**
6. **Watch real-time progress**:
   - ✅ Fetching article
   - ✅ Extracting content
   - ✅ Processing transcript
   - ✅ Generating AI summary
   - ✅ Saving to database
7. **View the article** when complete!

### Handling Duplicates

If an article was already processed:

1. **Duplicate warning appears** with date it was processed
2. **Two options**:
   - **View Existing**: Opens the existing article
   - **Reprocess Anyway**: Forces reprocessing (updates the article)

### Troubleshooting

**"Sign In Required" keeps appearing**:
- Make sure you're logged into https://tryparticles.com in another tab
- Try clicking "Sign In" and logging in fresh
- Check that cookies are enabled for the web app

**"Connection lost" error**:
- Check your internet connection
- Verify the backend is running (Railway may have cold starts)
- Try refreshing the page info and processing again

**Extension icon doesn't show**:
- Go to `chrome://extensions/`
- Find "Particles - Article Summarizer"
- Click the "refresh" icon to reload the extension
- Pin the extension from the puzzle icon menu

## Architecture

### File Structure

```
chrome-extension/
├── manifest.json              # Extension configuration (Manifest V3)
├── background.js              # Service worker for tab management
├── icons/                     # Extension icons
│   ├── icon-16.png
│   ├── icon-48.png
│   └── icon-128.png
├── sidepanel/
│   ├── sidepanel.html        # Main UI
│   ├── sidepanel.css         # Styles (matches web app)
│   └── sidepanel.js          # Controller + SSE client
└── lib/
    └── auth.js               # Authentication utilities
```

### How It Works

1. **Background Service Worker** (`background.js`):
   - Opens side panel when extension icon is clicked
   - Provides current tab info to side panel
   - Opens new tabs for viewing articles

2. **Authentication** (`lib/auth.js`):
   - Checks extension storage for cached token
   - Extracts token from web app's localStorage if available
   - Falls back to login redirect if no token found

3. **Side Panel** (`sidepanel/sidepanel.js`):
   - Manages UI state (auth, processing, results)
   - Establishes SSE connection to backend
   - Listens to 20+ event types for granular progress
   - Updates UI in real-time with step statuses

4. **Backend Integration**:
   - Calls `/api/process-direct` endpoint on Railway
   - Passes Supabase JWT token for authentication
   - Streams SSE events for live progress
   - Reuses all existing backend logic (no changes needed!)

### SSE Event Flow

The extension listens to the same events as the web app:

```
ping → started → fetch_start → fetch_complete →
detecting_video/audio/text_only → content_extract_start →
content_extracted → processing_audio → downloading_audio →
transcribing_audio → transcribing_chunk (x N) →
transcript_complete → ai_start → ai_complete →
save_start → save_complete → completed
```

**Special events**:
- `duplicate_detected`: Article already exists
- `error`: Processing failed

## Development

### Local Testing

1. Make changes to any file
2. Go to `chrome://extensions/`
3. Click the refresh icon on the extension card
4. Open side panel and test changes

### Backend Configuration

The extension points to:
- **Production Backend**: `https://article-summarizer-backend-production.up.railway.app`
- **Production Web App**: `https://tryparticles.com`

To test with local backend, edit `sidepanel/sidepanel.js`:
```javascript
const API_URL = 'http://localhost:8000';  // Change this
const WEB_APP_URL = 'http://localhost:3000';  // Change this
```

### Debugging

1. **Open DevTools for side panel**:
   - Right-click in side panel
   - Select "Inspect"
   - View console logs

2. **View background service worker logs**:
   - Go to `chrome://extensions/`
   - Click "service worker" link under the extension
   - View console in DevTools

3. **Check stored data**:
   ```javascript
   // In DevTools console
   chrome.storage.local.get(null, console.log)
   ```

## Design System

The extension matches the web app's design system:

- **Primary Color**: `#077331` (green)
- **Background**: `#ffffff` (white)
- **Text**: `#030712` (dark)
- **Border Radius**: `10px` (medium), `16px` (large)
- **Spacing**: `12px`, `16px`, `20px`, `24px`

All styles are defined in `sidepanel/sidepanel.css` using CSS variables.

## Privacy & Security

- **No data collection**: Extension only communicates with your Particles backend
- **Token storage**: JWT tokens cached locally in Chrome storage (cleared on logout)
- **HTTPS only**: All backend communication over encrypted HTTPS
- **Minimal permissions**: Only requests `activeTab`, `storage`, `tabs`, and `sidePanel`

## Version History

### v1.0.0 (Current)
- ✅ Initial release
- ✅ Side panel UI matching web app design
- ✅ SSE streaming with real-time progress
- ✅ Duplicate detection and reprocessing
- ✅ Authentication via web app session
- ✅ Support for demo video frames and private articles

## License

Part of the Particles project. See main repository for license details.

## Links

- **Web App**: https://tryparticles.com
- **GitHub**: https://github.com/gkotak/particles
- **Backend**: Railway (see main docs)
