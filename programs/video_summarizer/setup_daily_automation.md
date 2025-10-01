# Daily Post Automation Setup

This guide helps you set up daily automation to check for new posts and run the video summarizer.

## Quick Start

1. **Update Newsletter Links**
   - Edit `programs/video_summarizer/newsletter_podcast_links.md`
   - Replace example URLs with real newsletter/podcast feeds you want to monitor

2. **Test the Script**
   ```bash
   cd /Users/gauravkotak/cursor-projects-1/automate_life
   ./programs/video_summarizer/daily_check.sh
   ```

3. **Set up Daily Automation**
   Choose one of the options below:

## Option 1: macOS Launchd (Recommended for Mac)

Create a launchd plist file:

```bash
# Create the plist file
cat > ~/Library/LaunchAgents/com.automate_life.daily_checker.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.automate_life.daily_checker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/gauravkotak/cursor-projects-1/automate_life/programs/video_summarizer/daily_check.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>/Users/gauravkotak/cursor-projects-1/automate_life</string>
    <key>StandardOutPath</key>
    <string>/Users/gauravkotak/cursor-projects-1/automate_life/programs/video_summarizer/logs/daily_checker.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/gauravkotak/cursor-projects-1/automate_life/programs/video_summarizer/logs/daily_checker_error.log</string>
</dict>
</plist>
EOF

# Load the job
launchctl load ~/Library/LaunchAgents/com.automate_life.daily_checker.plist

# Check if it's loaded
launchctl list | grep com.automate_life.daily_checker
```

## Option 2: Cron Job

Add to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 9 AM):
0 9 * * * /Users/gauravkotak/cursor-projects-1/automate_life/programs/video_summarizer/daily_check.sh >> /Users/gauravkotak/cursor-projects-1/automate_life/programs/video_summarizer/logs/daily_checker.log 2>&1
```

## Option 3: Manual Daily Run

Simply run the script manually each day:

```bash
cd /Users/gauravkotak/cursor-projects-1/automate_life
./programs/video_summarizer/daily_check.sh
```

## How It Works

1. **URL Monitoring**: Reads platform URLs from `video_summarizer/newsletter_podcast_links.md`
2. **Post Detection**: Checks each platform for new posts using platform-specific parsing
3. **Duplicate Prevention**: Tracks processed posts in `processed_posts.json` to avoid re-processing
4. **Video Summarizer**: Automatically runs the video summarizer on new posts
5. **Logging**: Keeps detailed logs in `programs/video_summarizer/logs/`

## Supported Platforms

- **Substack**: Detects new newsletter posts
- **Medium**: Finds new articles
- **YouTube**: Identifies new videos
- **Ghost**: Monitors blog posts
- **Generic**: Works with most blog/news sites

## Files Created

- `programs/video_summarizer/daily_post_checker.py` - Main Python script
- `programs/video_summarizer/daily_check.sh` - Simple bash wrapper
- `programs/video_summarizer/view_extraction_logs.sh` - Log viewer utility
- `programs/video_summarizer/newsletter_podcast_links.md` - Platform URLs to monitor
- `programs/video_summarizer/processed_posts.json` - Tracking file (auto-created)
- `programs/video_summarizer/logs/new_posts_extraction_YYYYMMDD.log` - Detailed extraction logs

## Configuration

### Environment Variables

If you need authentication for premium content, add to `.env.local`:

```bash
# Substack
SUBSTACK_EMAIL=your-email@example.com
SUBSTACK_PASSWORD=your-password

# Medium
MEDIUM_SESSION_COOKIE=your-session-cookie

# Generic session cookies
NEWSLETTER_SESSION_COOKIES="name1=value1; name2=value2"
```

### Customization

Edit `video_summarizer/daily_post_checker.py` to:
- Adjust post detection logic
- Change how recent posts are identified (currently 7 days)
- Modify platform-specific parsing
- Add new platform support

## Troubleshooting

1. **No posts found**: Check if URLs in `video_summarizer/newsletter_podcast_links.md` are correct
2. **Permission denied**: Ensure scripts are executable (`chmod +x daily_check.sh`)
3. **Claude CLI not found**: Make sure Claude Code is installed and in PATH
4. **Python dependencies**: Script auto-installs `requests` and `beautifulsoup4`

## Monitoring

### Detailed Extraction Logs

The system creates comprehensive logs at `programs/video_summarizer/logs/new_posts_extraction_YYYYMMDD.log` that track:

- **URL Extraction**: Every URL found in `newsletter_podcast_links.md`
- **Platform Detection**: How each URL is categorized
- **Post Discovery**: All posts found on each platform
- **Date Checking**: Whether each post is recent (last 7 days)
- **Processing Status**: Success/failure of video summarizer
- **Session Summary**: Complete statistics for each run

### Viewing Logs

Use the built-in log viewer:
```bash
./programs/video_summarizer/view_extraction_logs.sh
```

Options include:
1. **Full log** - Complete extraction session details
2. **Last 50 lines** - Recent activity
3. **Session summary** - Key statistics only
4. **Follow log** - Live monitoring during execution
5. **Search** - Find specific posts or errors

### Example Log Output

```
================================================================================
NEW POSTS EXTRACTION SESSION STARTED
Session Time: 2025-09-30 16:33:35
Looking for posts from last 7 days (since 2025-09-23)
================================================================================

📖 Reading platform URLs from: video_summarizer/newsletter_podcast_links.md
✅ Extracted inline URL: https://example.substack.com

📡 PLATFORM 1/8: https://example.substack.com
🏷️ Platform type: substack
✅ Successfully fetched content (Status: 200, Size: 107343 bytes)
📋 Found 23 total links on page
   📝 Post 1: Heroes who came to look for "Example"....
   🆔 Post hash: 22d88f100e6ac8f40325603bd2607ccc
   ✅ Post is NEW (not in tracking database)
   ✅ Post is RECENT (within last 7 days)
   📝 NEW POST QUALIFIED FOR PROCESSING
   🚀 Launching video summarizer for post...
   ✅ POST SUCCESSFULLY PROCESSED AND TRACKED

📊 FINAL SESSION SUMMARY
🌐 Platforms checked: 8
📝 Total posts found: 12
🆕 New posts discovered: 3
✅ Successfully processed: 2
```

### Log Features

- **Timestamped entries** with `[NEW POSTS]` prefix for easy filtering
- **Emoji indicators** for quick visual scanning
- **Detailed URL parsing** showing exactly what was extracted
- **Platform-specific extraction** with link counts and types
- **Date validation** attempts with multiple date format parsing
- **Complete session statistics** for monitoring trends