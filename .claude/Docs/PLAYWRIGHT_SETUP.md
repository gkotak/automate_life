# Playwright Browser Automation Setup

## Overview

Playwright integration enables the article summarizer to bypass anti-bot measures on sites like Seeking Alpha that use Cloudflare protection, CAPTCHA, or JavaScript-based bot detection.

## Installation

```bash
# Install Playwright
pip install playwright

# Download Chromium browser (required)
playwright install chromium
```

## Quick Start

1. **Add domains that need browser automation to your `.env` file:**
   ```bash
   BROWSER_FETCH_DOMAINS=seekingalpha.com
   ```

2. **Run article summarizer normally:**
   ```bash
   python programs/article_summarizer/scripts/article_summarizer.py "https://seekingalpha.com/article/..."
   ```

The system will automatically detect the domain and use browser automation.

## How It Works

### Detection Strategy

The system uses browser automation when:

1. **Domain is in `BROWSER_FETCH_DOMAINS`** (always use browser)
2. **Cloudflare challenge detected** in response
3. **CAPTCHA detected** in response
4. **Access denied / 403 errors** in response
5. **Bot blocking messages** detected

### Authentication Flow

```
┌─────────────────────────────────────────────────┐
│ 1. Standard Request (Fast)                     │
│    - Use requests library                       │
│    - Apply Chrome cookies                       │
│    - Check response                             │
└─────────────────────────────────────────────────┘
                    ↓
         [Bot blocking detected?]
                    ↓
┌─────────────────────────────────────────────────┐
│ 2. Browser Fallback (Robust)                   │
│    - Launch Playwright/Chromium                 │
│    - Inject Chrome cookies                      │
│    - Execute JavaScript                         │
│    - Extract rendered HTML                      │
└─────────────────────────────────────────────────┘
```

### Cookie Injection

- Automatically loads Chrome cookies (from Seeking Alpha, etc.)
- Injects them into Playwright browser context
- Browser appears as logged-in user
- No manual login required!

## Configuration

Add to `.env` or `.env.local`:

```bash
# Required: Domains that always use browser automation
BROWSER_FETCH_DOMAINS=seekingalpha.com,othersite.com

# Optional: Run in visible mode for debugging
PLAYWRIGHT_HEADLESS=false

# Optional: Increase timeout for slow sites (milliseconds)
PLAYWRIGHT_TIMEOUT=60000

# Optional: Save screenshots on errors
PLAYWRIGHT_SCREENSHOT_ON_ERROR=true
```

## Performance

- **Standard Request**: ~0.5 seconds
- **Browser Automation**: ~3-5 seconds

Browser automation is only used when necessary to minimize performance impact.

## Debugging

### Enable Visible Browser

```bash
PLAYWRIGHT_HEADLESS=false
```

This launches a visible browser window so you can see what's happening.

### Enable Screenshots

```bash
PLAYWRIGHT_SCREENSHOT_ON_ERROR=true
```

Saves screenshots to `/tmp/` when errors occur.

### Check Logs

Look for these log messages:

- `🌐 [BROWSER FETCH] Launching browser...` - Browser starting
- `🍪 [BROWSER FETCH] Injected X cookies` - Cookies loaded
- `✅ [BROWSER FETCH] Successfully fetched` - Success
- `❌ [BROWSER FETCH] Error:` - Failure

## Supported Platforms

Currently configured for:
- **Seeking Alpha** (requires subscription)
- **Any site with Cloudflare protection**
- **Sites requiring JavaScript execution**

## Adding New Platforms

To always use browser automation for a new site:

1. **Add domain to `.env`:**
   ```bash
   BROWSER_FETCH_DOMAINS=seekingalpha.com,newsite.com
   ```

2. **Make sure you're logged in to the site in Chrome**
   - Chrome cookies will be automatically extracted and used

## Troubleshooting

### "Playwright not available"

```bash
pip install playwright
playwright install chromium
```

### "No cookies injected"

- Make sure you're logged into the site in Chrome
- Chrome cookies are automatically extracted
- Check Chrome profile is in default location

### "Timeout errors"

Increase timeout in `.env`:
```bash
PLAYWRIGHT_TIMEOUT=60000
```

### "Still getting blocked"

Try visible mode to see what's happening:
```bash
PLAYWRIGHT_HEADLESS=false
```

Check if manual CAPTCHA is required (not automatable).

## Security Notes

- Playwright uses your local Chrome cookies
- No credentials are stored or transmitted
- Browser runs locally on your machine
- Same security model as opening Chrome yourself

## Architecture

### Files Modified

- `programs/article_summarizer/common/browser_fetcher.py` - Core Playwright logic
- `programs/article_summarizer/common/authentication.py` - Integration with auth system
- `programs/article_summarizer/scripts/article_summarizer.py` - Fallback detection
- `programs/article_summarizer/scripts/requirements.txt` - Added playwright dependency

### Key Classes

- **`BrowserFetcher`**: Handles Playwright browser automation
  - `fetch_with_playwright()` - Main fetch method
  - `_inject_cookies()` - Cookie injection
  - `should_use_browser_fetch()` - Detection logic

- **`AuthenticationManager`**: Coordinates authentication
  - `fetch_with_browser()` - Public interface for browser fetch
  - `should_use_browser_fetch()` - Delegates to BrowserFetcher

## Examples

### Example 1: Seeking Alpha with automatic browser

```bash
# Add to .env
BROWSER_FETCH_DOMAINS=seekingalpha.com

# Process article (automatically uses browser)
python programs/article_summarizer/scripts/article_summarizer.py \
  "https://seekingalpha.com/article/4567890-some-article"
```

### Example 2: Debug mode with visible browser

```bash
# Add to .env
BROWSER_FETCH_DOMAINS=seekingalpha.com
PLAYWRIGHT_HEADLESS=false
PLAYWRIGHT_SCREENSHOT_ON_ERROR=true

# Watch browser automation in action
python programs/article_summarizer/scripts/article_summarizer.py \
  "https://seekingalpha.com/article/4567890-some-article"
```

### Example 3: Cloudflare detection (automatic)

```bash
# No configuration needed - automatic detection
# System will detect Cloudflare and switch to browser automatically
python programs/article_summarizer/scripts/article_summarizer.py \
  "https://some-cloudflare-protected-site.com/article"
```

## Limitations

- **CAPTCHA**: Manual CAPTCHAs require human interaction
- **Rate Limits**: Browser automation doesn't bypass rate limits
- **Performance**: ~3-5 seconds overhead per request
- **Resources**: Launches full browser instance (memory intensive)

## Next Steps

After installation:

1. ✅ Install Playwright: `pip install playwright && playwright install chromium`
2. ✅ Configure domains in `.env`
3. ✅ Log into sites in Chrome (for cookie extraction)
4. ✅ Test with a Seeking Alpha URL
5. ✅ Monitor logs for successful browser fetch
