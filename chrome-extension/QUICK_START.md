# Quick Start Guide - Particles Chrome Extension

Get up and running in 5 minutes!

## Prerequisites

- Google Chrome browser
- An account on https://tryparticles.com

## Installation (2 minutes)

### Step 1: Get the Extension Files

**Option A: Clone from GitHub**
```bash
git clone https://github.com/gkotak/particles.git
cd particles/chrome-extension
```

**Option B: Download ZIP**
- Download the extension ZIP file
- Extract to a folder on your computer

### Step 2: Add Icon Files

You'll need to add 3 icon files to the `icons/` folder:
- `icon-16.png` (16x16 pixels)
- `icon-48.png` (48x48 pixels)
- `icon-128.png` (128x128 pixels)

See `icons/icon-creation-instructions.txt` for how to create these from your logo.

### Step 3: Load in Chrome

1. Open Chrome and go to: **`chrome://extensions/`**
2. **Enable "Developer mode"** (toggle in top-right)
3. Click **"Load unpacked"**
4. Select the `chrome-extension` folder
5. ✅ Extension is now installed!

### Step 4: Pin the Extension (Recommended)

1. Click the **puzzle icon** 🧩 in Chrome toolbar
2. Find **"Particles - Article Summarizer"**
3. Click the **pin icon** 📌 to keep it visible

## First Use (1 minute)

### Sign In

1. **Click the extension icon** in toolbar
2. **Side panel opens** on the right
3. If not logged in, click **"Sign In to Particles"**
4. **Log in** on the web app
5. **Return to extension** - you're now authenticated!

### Process Your First Article

1. **Navigate to any article** (e.g., stratechery.com, lennysnewsletter.com)
2. **Click the extension icon** - side panel opens
3. **Verify the page info** is correct
4. Click **"Summarize This Page"** button
5. **Watch the progress** in real-time!
6. Click **"View Article"** when done

## Tips & Tricks

### ⚡ Keyboard Shortcut
- You can set a keyboard shortcut to open the extension:
  1. Go to `chrome://extensions/shortcuts`
  2. Find "Particles - Article Summarizer"
  3. Set a shortcut like `Ctrl+Shift+A` (or `Cmd+Shift+A` on Mac)

### 🔄 Reprocessing Articles
- If you see a duplicate warning, you have 2 options:
  - **View Existing**: Opens the previously processed article
  - **Reprocess Anyway**: Forces a fresh summary (useful if content was updated)

### 🎥 Demo Videos
- Processing a screen share or demo video?
- Check **"Extract demo video frames"** before processing
- This captures key frames for visual reference

### 🔒 Private Articles
- Want to keep an article private to your organization?
- Check **"Save as private article"** before processing
- Article will only be visible to your organization members

## Troubleshooting

### "Sign In Required" Keeps Appearing

**Solution**: Make sure you're logged into https://tryparticles.com
1. Open the web app in a new tab
2. Sign in with your credentials
3. Return to extension and try again

### Extension Icon Not Showing

**Solution**: Refresh the extension
1. Go to `chrome://extensions/`
2. Find "Particles - Article Summarizer"
3. Click the refresh icon (circular arrow)

### "Connection Lost" Error

**Causes**:
- Backend may be starting up (Railway cold start - wait 30 seconds)
- Internet connection issues
- Backend is down

**Solution**: Wait a moment and try again

### Content Not Extracted Properly

**Solution**:
- Some sites use heavy JavaScript rendering
- Try refreshing the page first
- If persistent, the backend uses Playwright to handle complex pages

## What Gets Processed?

The extension can handle:
- ✅ **Articles**: Blog posts, news, newsletters
- ✅ **YouTube videos**: Extracts transcript automatically
- ✅ **Podcasts**: Downloads audio and transcribes
- ✅ **Paywalled content**: Uses your existing subscriptions
- ✅ **Complex sites**: Substack, Medium, Stratechery, etc.

## Privacy & Data

- **No tracking**: Extension only talks to your Particles backend
- **Your data**: All summaries saved to your private Supabase database
- **Secure**: All communication over HTTPS
- **Open source**: Full code available on GitHub

## Need Help?

- 📖 **Full Documentation**: See `README.md` in the extension folder
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💬 **Questions**: Check the main Particles documentation

## Next Steps

Now that you're set up, try:
1. Processing articles from your favorite newsletters
2. Summarizing YouTube videos you've been meaning to watch
3. Building your searchable knowledge base of everything you read
4. Using the web app to search semantically across all your content

Happy reading! 📚✨
