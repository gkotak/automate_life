# Railway Backend - Continuation Plan

**Status**: Core infrastructure and modules complete. Ready for service implementation.

**Last Updated**: October 20, 2025

---

## ✅ What's Been Completed

### Commit 1: Infrastructure Setup
- ✅ FastAPI application structure (main.py, routes, middleware)
- ✅ Dockerfile with Playwright + Chromium + ffmpeg
- ✅ Railway configuration (railway.json)
- ✅ Requirements.txt with all dependencies
- ✅ API authentication middleware (Bearer tokens)
- ✅ Comprehensive documentation

### Commit 2: Core Modules & Processors
- ✅ All core modules copied from `article_summarizer/common/` to `backend/core/`
- ✅ Authentication.py adapted for Railway (uses storage_state.json instead of Chrome cookies)
- ✅ All processors copied (transcript_processor, file_transcriber)
- ✅ Browser fetcher ready for anti-bot protection

---

## 🔄 Next Steps - Simplified Implementation Guide

**Updated Approach**: We're using **Option 2 (Browser-in-Docker with Playwright)** from BACKEND_AUTH_PLAN.md with **Method A (Interactive Setup)** only. Cookie extraction script has been removed as it's not needed for MVP.

**Steps Overview**:
1. Create article_processor.py service (45 min)
2. Create setup_auth.py script (45 min)
3. ~~Extract cookies~~ (SKIP - not needed)
4. Test backend locally (1-2 hours)
5. Deploy to Railway (30 min)
6. Configure auth with interactive setup (30 min)
7. Frontend integration (1-2 hours)
8. Add admin panel & command automation (2-3 hours) - *Optional but recommended*

**Core functionality time**: 4-5 hours
**With admin panel**: 6-8 hours total

---

## 🔄 Detailed Implementation Guide

### Step 1: Create Article Processor Service

**File**: `programs/article_summarizer_backend/app/services/article_processor.py`

**What to do**:
1. Copy `article_summarizer.py` to this location
2. Rename class from `ArticleSummarizer` to `ArticleProcessor`
3. Update import paths:
   ```python
   # Change:
   from common.base import BaseProcessor
   # To:
   from core.base import BaseProcessor

   # Change:
   from common.config import Config
   # To:
   from core.config import Config

   # And so on for all imports...
   ```
4. Update path resolution for Railway:
   ```python
   # Instead of looking for .env.local in parent directories
   # Use environment variables directly (already set in Railway)
   ```
5. Keep all processing logic the same (no changes needed)

**Estimated time**: 30-45 minutes

---

### Step 2: Create Authentication Setup Script

**File**: `programs/article_summarizer_backend/scripts/setup_auth.py`

**Purpose**: One-time script to login to platforms and save browser session

**Implementation**:

```python
#!/usr/bin/env python3
"""
Authentication Setup Script for Railway

This script helps you configure browser authentication for paywalled content.
Run this once on Railway to establish persistent browser sessions.

Usage:
    # In Railway shell
    python3 scripts/setup_auth.py --platform substack
    python3 scripts/setup_auth.py --platform medium
    python3 scripts/setup_auth.py --platform seekingalpha
"""

import os
import sys
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


PLATFORM_URLS = {
    'substack': 'https://substack.com/sign-in',
    'medium': 'https://medium.com/m/signin',
    'seekingalpha': 'https://seekingalpha.com/login',
    'patreon': 'https://www.patreon.com/login',
    'tegus': 'https://www.tegus.com/login',
}


def setup_platform_auth(platform: str, headless: bool = False):
    """
    Open browser, navigate to login page, wait for manual login,
    then save browser state to storage_state.json

    Args:
        platform: Platform to authenticate (substack, medium, etc.)
        headless: Whether to run browser in headless mode
    """

    if platform not in PLATFORM_URLS:
        print(f"❌ Unknown platform: {platform}")
        print(f"   Supported platforms: {', '.join(PLATFORM_URLS.keys())}")
        sys.exit(1)

    storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
    storage_state_file = Path(storage_dir) / 'storage_state.json'

    # Create storage directory if needed
    os.makedirs(storage_dir, exist_ok=True)

    print(f"🌐 Setting up authentication for {platform}")
    print(f"   Login URL: {PLATFORM_URLS[platform]}")
    print(f"   Storage: {storage_state_file}")
    print()
    print("Instructions:")
    print("1. Browser will open to login page")
    print("2. Complete login manually (enter username/password)")
    print("3. Once logged in, press Enter in this terminal")
    print("4. Browser session will be saved for future use")
    print()

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        # Create context (load existing state if available)
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        }

        if storage_state_file.exists():
            print(f"📂 Loading existing browser state...")
            context_options['storage_state'] = str(storage_state_file)

        context = browser.new_context(**context_options)
        page = context.new_page()

        # Navigate to login page
        print(f"🔗 Opening {PLATFORM_URLS[platform]}...")
        page.goto(PLATFORM_URLS[platform])

        # Wait for user to login
        input("\n⏸️  Complete login in the browser, then press Enter here to save session...")

        # Save browser state
        print(f"💾 Saving browser session...")
        context.storage_state(path=str(storage_state_file))

        print(f"✅ Authentication configured for {platform}!")
        print(f"   Session saved to: {storage_state_file}")

        browser.close()


def main():
    parser = argparse.ArgumentParser(description='Setup authentication for Railway backend')
    parser.add_argument('--platform', required=True, help='Platform to authenticate')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')

    args = parser.parse_args()

    try:
        setup_platform_auth(args.platform, args.headless)
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
```

**Testing locally**:
```bash
cd programs/article_summarizer_backend
python3 scripts/setup_auth.py --platform substack
```

**Estimated time**: 45 minutes

---

### Step 3: ~~Create Cookie Extraction Script~~ (SKIP - Not Needed for MVP)

**Status**: ❌ **Skip this step**

**Why skip**:
- Interactive setup (Step 2) works for 95% of cases
- Adds complexity without immediate benefit
- Can be created later if needed

**When you might need it**:
- Interactive setup fails on Railway (rare)
- Need to refresh sessions frequently (unlikely)
- Want to automate cookie rotation (future optimization)

**If you need it later**: See RAILWAY_MIGRATION_GUIDE.md section on "Option A: Upload Cookies"

---

### Step 4: Test Backend Locally

**Before deploying to Railway, test everything works locally:**

```bash
cd programs/article_summarizer_backend

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set up environment
cp .env.example .env.local
# Edit .env.local with your API keys

# Run FastAPI server
uvicorn app.main:app --reload --port 8000
```

**Test endpoints**:

```bash
# 1. Health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "playwright": true,
  "storage": true,
  "session_configured": false  # true if you ran setup_auth.py
}

# 2. Process article (requires API key)
curl -X POST http://localhost:8000/api/process-article \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'

# Expected: Article processed, ID returned

# 3. Check auth status
curl http://localhost:8000/api/auth/status \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Common issues**:

| Issue | Solution |
|-------|----------|
| "Playwright not found" | Run `playwright install chromium` |
| "API key invalid" | Check API_KEY in .env.local matches your curl request |
| "Storage directory not found" | Create: `mkdir -p storage` |
| "Import errors" | Check all paths use `core.*` and `processors.*` |

**Estimated time**: 1-2 hours (including debugging)

---

### Step 5: Deploy to Railway

**Railway Dashboard Steps**:

1. **Create New Service**
   - Go to https://railway.app/dashboard
   - Click "New Project" → "Deploy from GitHub"
   - Select your repository
   - Set root directory: `programs/article_summarizer_backend`

2. **Configure Build**
   - Railway auto-detects Dockerfile ✅
   - No manual build commands needed

3. **Add Environment Variables**
   ```bash
   ANTHROPIC_API_KEY=sk-ant-xxxxx
   OPENAI_API_KEY=sk-xxxxx
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_ANON_KEY=eyJxxx...
   API_KEY=<generate-with: python3 -c "import secrets; print(secrets.token_urlsafe(48))">
   PLAYWRIGHT_HEADLESS=true
   PLAYWRIGHT_TIMEOUT=30000
   STORAGE_DIR=/app/storage
   ENVIRONMENT=production
   ```

4. **Add Persistent Volume**
   - Volumes tab → "New Volume"
   - Mount path: `/app/storage`
   - Size: 1GB

5. **Deploy**
   - Click "Deploy"
   - Wait 5-10 minutes (first build with Playwright is slow)
   - Railway provides URL: `https://your-app.up.railway.app`

6. **Verify Deployment**
   ```bash
   # Health check
   curl https://your-app.up.railway.app/health

   # Should show:
   {
     "status": "healthy",
     "playwright": true,
     "storage": true,
     "session_configured": false
   }
   ```

**Estimated time**: 30 minutes setup + 10 minutes build

---

### Step 6: Configure Authentication on Railway

**Option A: Interactive Setup (Recommended)**

```bash
# Connect to Railway container
railway connect

# Inside container, run setup script
python3 scripts/setup_auth.py --platform substack

# Browser opens (if headless=false) or instructions shown
# Complete login
# Session saved to /app/storage/storage_state.json
```

**Option B: Upload Cookies**

```bash
# On your desktop
python3 scripts/extract_cookies.py > cookies.json

# Upload to Railway
curl -X POST https://your-app.up.railway.app/api/auth/upload-cookies \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @cookies.json
```

**Verify authentication**:
```bash
curl https://your-app.up.railway.app/api/auth/status \
  -H "Authorization: Bearer YOUR_API_KEY"

# Should show configured platforms
```

**Estimated time**: 20-30 minutes per platform

---

### Step 7: Update Frontend to Use Railway Backend

**File**: `web-apps/article-summarizer/src/lib/backend-api.ts`

```typescript
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
const API_KEY = process.env.BACKEND_API_KEY

export async function processArticle(url: string) {
  const response = await fetch(`${BACKEND_URL}/api/process-article`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`
    },
    body: JSON.stringify({ url })
  })

  if (!response.ok) {
    throw new Error(`Backend error: ${response.statusText}`)
  }

  return response.json()
}
```

**Update environment**:
`web-apps/article-summarizer/.env.local`
```bash
NEXT_PUBLIC_BACKEND_URL=https://your-app.up.railway.app
BACKEND_API_KEY=<same-as-railway-api-key>
```

**Create submission page** (see RAILWAY_MIGRATION_GUIDE.md for full code)

**Estimated time**: 1-2 hours

---

### Step 8: Add Admin Panel & Command Automation (Optional but Recommended)

**Purpose**: Enable running commands on Railway without local machine access

Once deployed, you'll want to invoke commands (process article, check posts, check podcasts) easily. This step adds:
- Web-based admin panel for one-click command execution
- Railway cron jobs for automated recurring tasks
- No local machine dependency

**See detailed implementation**: `RAILWAY_MIGRATION_GUIDE.md` → "Running Commands on Railway" section

**Quick Summary**:

1. **Create Admin Panel** (`web-apps/article-summarizer/src/app/admin/page.tsx`)
   - Button to process article URL
   - Buttons to trigger post/podcast checks
   - Status display

2. **Add Command Routes** (`app/routes/commands.py`)
   - `/trigger/check-posts` endpoint
   - `/trigger/check-podcasts` endpoint
   - Executes Python scripts via subprocess

3. **Configure Cron Jobs** (update `railway.json`)
   ```json
   "cron": [
     {
       "name": "check-new-posts",
       "schedule": "0 */4 * * *",
       "command": "python3 scripts/check_new_posts.py"
     },
     {
       "name": "check-podcasts",
       "schedule": "0 */6 * * *",
       "command": "python3 scripts/podcast_checker.py"
     }
   ]
   ```

4. **Copy Scripts to Backend**
   ```bash
   cp programs/check_new_posts/*.py programs/article_summarizer_backend/scripts/
   # Update import paths: common.* → core.*
   ```

**Access**: `http://localhost:3000/admin` (or Railway frontend URL)

**Estimated time**: 2-3 hours

**When to do this**: After Step 7 (frontend integration) is complete and working

---

## 📋 Checklist Before Going Live

### Local Testing
- [ ] Backend runs locally with `uvicorn`
- [ ] Health endpoint responds correctly
- [ ] Can process a simple YouTube video
- [ ] Can process a text article
- [ ] API key authentication works
- [ ] Error handling works (invalid URL, etc.)

### Railway Deployment
- [ ] Dockerfile builds successfully
- [ ] All environment variables set
- [ ] Persistent volume configured
- [ ] Health check passes
- [ ] Can process article via API

### Authentication
- [ ] Storage state file exists in Railway volume
- [ ] Can process paywalled Substack article
- [ ] Can process paywalled Medium article
- [ ] Session persists across container restarts

### Frontend Integration
- [ ] Frontend can call Railway API
- [ ] Article submission works end-to-end
- [ ] Errors are displayed properly
- [ ] Articles save to Supabase correctly

---

## 🐛 Troubleshooting Guide

### Backend Won't Start

**Symptom**: Railway container crashes on startup

**Possible causes**:
1. Missing environment variable → Check Railway Variables tab
2. Import errors → Check all imports use `core.*` and `processors.*`
3. Playwright installation failed → Check build logs

**Fix**:
```bash
# View Railway logs
railway logs

# Common fixes in Dockerfile:
RUN playwright install chromium --with-deps
```

### Authentication Not Working

**Symptom**: Paywalled articles return 403/401

**Possible causes**:
1. No storage_state.json file
2. Cookies expired
3. Wrong domain in cookies

**Fix**:
```bash
# Check storage state exists
railway run ls -la /app/storage/

# Re-run auth setup
railway run python3 scripts/setup_auth.py --platform substack
```

### High Railway Costs

**Symptom**: Bill higher than expected

**Possible causes**:
1. Too many Playwright instances
2. Memory leaks
3. Long-running processes

**Optimization**:
1. Add request timeout limits
2. Implement caching for recent articles
3. Use Playwright only when needed (not for all requests)
4. Consider splitting into two services (fast + Playwright)

---

## 📊 Expected Performance & Costs

### Processing Time
- Simple article (no auth): 5-10 seconds
- YouTube video with transcript: 15-30 seconds
- Paywalled article (Playwright): 20-40 seconds
- Long video (>1hr with transcription): 1-3 minutes

### Railway Costs
- **Hobby Plan**: $5/month (includes $5 credit)
- **Estimated usage**: $15-20/month
- **Out of pocket**: ~$10-15/month

**Cost breakdown**:
- CPU: ~$8-10/month (Playwright is CPU-intensive)
- Memory: ~$5-7/month (2GB RAM for Chromium)
- Storage: ~$1-2/month (Docker image + volume)

---

## 🎯 Success Criteria

You'll know everything is working when:

1. ✅ Can process articles via Railway API
2. ✅ Frontend successfully submits URLs and displays results
3. ✅ Authenticated content (Substack/Medium) processes correctly
4. ✅ Sessions persist across deployments
5. ✅ No local Python execution needed
6. ✅ Costs are within budget ($15-20/month)

---

## 📚 Reference Documents

- **Full Migration Guide**: `.claude/Docs/RAILWAY_MIGRATION_GUIDE.md`
- **Auth Strategy**: `.claude/Docs/BACKEND_AUTH_PLAN.md`
- **Dependencies**: `programs/article_summarizer_backend/DEPENDENCIES.md`
- **Backend README**: `programs/article_summarizer_backend/README.md`

---

## 🚀 Quick Command Reference

**Local Development**:
```bash
cd programs/article_summarizer_backend
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```

**Railway Deployment**:
```bash
git push origin main          # Auto-deploys to Railway
railway logs --follow         # Watch deployment
railway connect              # SSH into container
```

**Testing**:
```bash
# Health
curl https://your-app.up.railway.app/health

# Process article
curl -X POST https://your-app.up.railway.app/api/process-article \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "URL_HERE"}'
```

---

**Document Version**: 1.0
**Status**: Ready for Implementation
**Next Session**: Start with Step 1 (Create Article Processor Service)
