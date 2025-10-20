# Railway Backend Migration Guide

**Date**: October 20, 2025
**Objective**: Move Python article summarizer backend to Railway with zero local dependencies

---

## Overview

This guide provides step-by-step instructions for deploying the article summarizer Python backend to Railway as a FastAPI service. We're using **Option 2: Browser-in-Docker (Playwright)** for authentication, which eliminates all desktop dependencies.

###

 Why This Approach?
- ✅ **Zero local dependencies** - Everything runs on Railway
- ✅ **Solves both auth + anti-bot** - Playwright handles Cloudflare, JavaScript sites, and authentication
- ✅ **Reuses 90% of existing code** - browser_fetcher.py already exists
- ✅ **Persistent sessions** - Browser state saved to Railway volume
- ✅ **Production-ready** - Proper API authentication and error handling

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Container                        │
│                                                             │
│  ┌──────────────┐         ┌─────────────────┐             │
│  │   FastAPI    │────────▶│   Article       │             │
│  │   Server     │         │   Processor     │             │
│  └──────┬───────┘         └────────┬────────┘             │
│         │                          │                       │
│         │                          ▼                       │
│         │                  ┌─────────────────┐             │
│         │                  │   Playwright    │             │
│         │                  │   + Chromium    │             │
│         │                  └────────┬────────┘             │
│         │                           │                       │
│         │                           ▼                       │
│         │                  ┌─────────────────┐             │
│         │                  │  storage_state  │             │
│         │                  │   .json         │             │
│         │                  │  (Volume)       │             │
│         │                  └─────────────────┘             │
│         │                                                   │
│         └──────────────▶ Supabase Database                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Create FastAPI Backend Service

### 1.1 Backend Directory Structure

```
programs/article_summarizer_backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── article.py              # POST /api/process-article
│   │   └── auth.py                 # POST /api/auth/setup-session
│   ├── services/
│   │   ├── __init__.py
│   │   └── article_processor.py    # ArticleSummarizer class
│   └── middleware/
│       ├── __init__.py
│       └── auth.py                  # API key authentication
├── core/                            # Adapted from common/
│   ├── __init__.py
│   ├── config.py
│   ├── browser_fetcher.py
│   ├── authentication.py            # Modified for Railway
│   ├── content_detector.py
│   ├── claude_client.py
│   └── base.py
├── processors/                      # Copied from processors/
│   ├── __init__.py
│   ├── transcript_processor.py
│   └── file_transcriber.py
├── scripts/
│   ├── setup_auth.py                # One-time browser login
│   └── health_check.py
├── storage/                         # Will be Railway volume mount point
│   └── storage_state.json           # Browser session (created at runtime)
├── Dockerfile
├── requirements.txt
├── railway.json                     # Railway configuration
├── .env.example
└── README.md
```

### 1.2 Key Endpoints

**Health Check**
```
GET /health
Response: {"status": "healthy", "playwright": true}
```

**Process Article**
```
POST /api/process-article
Headers: Authorization: Bearer YOUR_API_KEY
Body: {"url": "https://example.com/article"}
Response: {"article_id": 123, "status": "success"}
```

**Setup Authentication (One-Time)**
```
POST /api/auth/setup-session
Headers: Authorization: Bearer YOUR_API_KEY
Body: {"platform": "substack", "cookies": {...}}
Response: {"status": "success", "message": "Session saved"}
```

---

## Phase 2: Railway Setup

### 2.1 Create Railway Project

**Step 1: Sign up / Log in to Railway**
1. Go to https://railway.app
2. Sign up with GitHub (recommended)
3. Verify email if needed

**Step 2: Create New Project**
1. Click **"New Project"** button
2. Select **"Deploy from GitHub repo"**
3. Authorize Railway to access your GitHub
4. Select repository: `automate_life`
5. Select branch: `main` (or your working branch)

**Step 3: Configure Build Settings**
1. Railway auto-detects Dockerfile
2. Set **Root Directory**: `programs/article_summarizer_backend`
3. Railway will automatically use the Dockerfile in that directory
4. Build command: (auto-detected from Dockerfile)
5. Start command: (auto-detected from Dockerfile CMD)

### 2.2 Add Environment Variables

In Railway Dashboard → Your Service → **Variables** tab, add:

```bash
# Required API Keys
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx...

# Backend Security
API_KEY=<generate-random-64-char-string>

# Playwright Settings
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_TIMEOUT=30000
PLAYWRIGHT_SCREENSHOT_ON_ERROR=false

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**How to generate secure API_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2.3 Add Persistent Volume

**Why do we need a volume?**
- Stores `storage_state.json` (browser session cookies + localStorage)
- Persists across container restarts
- Session survives deployments

**Steps:**
1. In Railway Dashboard → Your Service → **Volumes** tab
2. Click **"New Volume"**
3. Mount Path: `/app/storage`
4. Volume Size: 1GB (default)
5. Click **"Add Volume"**

**Important**: The `storage/` directory in your code will map to `/app/storage` in the container.

### 2.4 Deploy

1. Click **"Deploy"** button
2. Watch build logs in real-time
3. Initial build takes **5-10 minutes** (installing Playwright + Chromium)
4. Subsequent builds are faster (~2-3 minutes)
5. Once deployed, Railway provides a public URL:
   ```
   https://your-app-name.up.railway.app
   ```

**Note the URL** - you'll need it for:
- Frontend API calls
- Testing
- Authentication setup

---

## Phase 3: Authentication Setup (One-Time)

This is the **critical step** where we establish persistent browser sessions on Railway.

### Option A: Upload Cookies from Desktop (Quickest)

**Step 1: Extract cookies locally**
```bash
cd programs/article_summarizer_backend
python3 scripts/extract_cookies.py
```
This creates `cookies.json` with your Chrome session cookies.

**Step 2: Upload to Railway**
```bash
curl -X POST https://your-app.up.railway.app/api/auth/upload-cookies \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @cookies.json
```

**Step 3: Verify**
```bash
curl https://your-app.up.railway.app/api/auth/status \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Option B: Interactive Browser Login (Most Reliable)

**This is the recommended approach for production.**

**Step 1: Enable Railway Shell Access**
1. In Railway Dashboard → Your Service
2. Click **"Connect"** button (top right)
3. Opens a terminal in your running container

**Step 2: Run Interactive Setup Script**
```bash
# Inside Railway shell
python3 scripts/setup_auth.py --platform substack
```

**Step 3: What Happens**
1. Script launches Playwright browser (temporarily non-headless)
2. Opens login page for the platform
3. Waits for you to complete login manually
4. Saves authenticated browser state to `/app/storage/storage_state.json`
5. Future requests use this saved state

**Step 4: Test Authentication**
```bash
# Still in Railway shell
python3 scripts/test_auth.py --url "https://lennysnewsletter.com/p/some-article"
```

**Step 5: Repeat for Other Platforms**
```bash
python3 scripts/setup_auth.py --platform medium
python3 scripts/setup_auth.py --platform seekingalpha
# etc.
```

### Session Persistence

**How long do sessions last?**
- Most platforms: 30-90 days
- Saved to Railway volume (survives restarts)
- Auto-refreshed on each use (extends expiration)

**What happens when session expires?**
1. Backend detects authentication failure
2. Logs warning with platform name
3. Returns error to frontend
4. You'll need to re-run setup_auth.py for that platform

**Monitoring:**
```bash
# Check session health
curl https://your-app.up.railway.app/api/auth/health \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Phase 4: Frontend Integration

### 4.1 Add Backend API Client

**Create**: `web-apps/article-summarizer/src/lib/backend-api.ts`

```typescript
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
const API_KEY = process.env.BACKEND_API_KEY

export async function processArticle(url: string): Promise<{article_id: number, status: string}> {
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

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BACKEND_URL}/health`)
    const data = await response.json()
    return data.status === 'healthy'
  } catch {
    return false
  }
}
```

### 4.2 Update Environment Variables

**Add to**: `web-apps/article-summarizer/.env.local`

```bash
NEXT_PUBLIC_BACKEND_URL=https://your-app.up.railway.app
BACKEND_API_KEY=<same-api-key-as-railway>
```

### 4.3 Create Article Submission Page

**Create**: `web-apps/article-summarizer/src/app/submit/page.tsx`

```tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { processArticle } from '@/lib/backend-api'

export default function SubmitArticle() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const result = await processArticle(url)
      // Redirect to the newly created article
      router.push(`/article/${result.article_id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Submit Article</h1>

      <form onSubmit={handleSubmit} className="max-w-2xl">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com/article"
          className="w-full px-4 py-2 border rounded-lg"
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="mt-4 px-6 py-2 bg-[#077331] text-white rounded-lg"
        >
          {loading ? 'Processing...' : 'Process Article'}
        </button>

        {error && (
          <div className="mt-4 p-4 bg-red-50 text-red-800 rounded-lg">
            {error}
          </div>
        )}
      </form>
    </div>
  )
}
```

### 4.4 Add Submit Button to Header

**Update**: `web-apps/article-summarizer/src/components/ArticleList.tsx`

Add a "Submit Article" button next to the "AI Chat" button in the header.

---

## Phase 5: Testing & Validation

### 5.1 Local Testing (Before Railway)

**Step 1: Test FastAPI locally**
```bash
cd programs/article_summarizer_backend

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set environment variables
cp .env.example .env.local
# Edit .env.local with your keys

# Run server
uvicorn app.main:app --reload --port 8000
```

**Step 2: Test endpoints**
```bash
# Health check
curl http://localhost:8000/health

# Process article (with API key)
curl -X POST http://localhost:8000/api/process-article \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=some-video"}'
```

### 5.2 Railway Testing Checklist

**Basic Functionality**
- [ ] Health endpoint responds: `GET /health`
- [ ] API key authentication works (returns 401 without key)
- [ ] Process simple article (no auth): YouTube video
- [ ] Process text article (no auth): Wikipedia page

**Authentication & Anti-Bot**
- [ ] Process paywalled Substack article
- [ ] Process Medium article behind paywall
- [ ] Process Seeking Alpha article (Cloudflare test)
- [ ] Verify Playwright bypasses anti-bot measures

**Session Persistence**
- [ ] Stop and restart Railway service
- [ ] Verify storage_state.json still exists
- [ ] Process authenticated article again (should work)

**Database Integration**
- [ ] Article saves to Supabase correctly
- [ ] Embeddings generate successfully
- [ ] Frontend can retrieve and display article

**Performance**
- [ ] Measure processing time (expect 10-30 seconds)
- [ ] Check Railway metrics (CPU/memory usage)
- [ ] Verify no memory leaks over multiple requests

### 5.3 Common Issues & Fixes

**Issue**: "Playwright not found"
```bash
# In Railway shell
playwright install chromium
playwright install-deps
```

**Issue**: "Authentication failed"
```bash
# Check if storage_state.json exists
ls -la /app/storage/

# Re-run setup
python3 scripts/setup_auth.py --platform substack
```

**Issue**: "API key invalid"
```bash
# Verify environment variable is set correctly
echo $API_KEY

# Check Railway dashboard Variables tab
```

**Issue**: "Container out of memory"
- Railway might need larger plan for Playwright
- Optimize by setting `PLAYWRIGHT_HEADLESS=true`
- Consider adding memory limits in Dockerfile

---

## Phase 6: Monitoring & Maintenance

### 6.1 Railway Dashboard Monitoring

**Metrics to Watch:**
- **CPU Usage**: Should be <50% idle, spikes during processing
- **Memory Usage**: ~500MB idle, up to 1.5GB during Playwright
- **Build Time**: 5-10 minutes initial, 2-3 minutes subsequent
- **Response Time**: 10-30 seconds for article processing

**Logs:**
- View real-time logs in Railway dashboard
- Filter by log level (INFO, WARNING, ERROR)
- Search for specific article URLs or error messages

### 6.2 Session Refresh Strategy

**Automatic (Recommended):**
- Backend checks session validity on each request
- If session expired, logs warning
- Returns clear error message to frontend

**Manual (When Needed):**
```bash
# SSH into Railway container
railway run bash

# Re-authenticate for specific platform
python3 scripts/setup_auth.py --platform substack
```

**Scheduled (Optional):**
- Set up Railway cron job to check session health weekly
- Auto-alert if sessions about to expire
- Proactive re-authentication

### 6.3 Cost Optimization

**Expected Costs:**
- Railway Hobby: $5/month (includes $5 credit)
- Estimated usage: $15-20/month with Playwright
- Out of pocket: ~$10-15/month

**How to Reduce Costs:**
1. **Optimize Playwright usage**: Only use for authenticated/bot-protected sites
2. **Request-level caching**: Cache article metadata for 24 hours
3. **Resource limits**: Set memory/CPU limits in Dockerfile
4. **Sleep inactive services**: Railway auto-sleeps after inactivity

**Scaling Strategy:**
- Start with single Railway service
- If traffic increases, split into:
  - **Fast service**: Simple requests (YouTube, Wikipedia)
  - **Playwright service**: Authenticated/bot-protected only
- Use Railway's horizontal scaling when needed

---

## Security Best Practices

### 6.1 API Key Management

**DO:**
- ✅ Use long, random API keys (48+ characters)
- ✅ Store in Railway environment variables (encrypted)
- ✅ Rotate keys every 3-6 months
- ✅ Use different keys for dev/staging/production

**DON'T:**
- ❌ Commit API keys to Git
- ❌ Share API keys in Slack/email
- ❌ Use simple/guessable keys
- ❌ Reuse keys across services

### 6.2 Session Cookie Security

**Storage:**
- Cookies stored in `storage_state.json` on Railway volume
- Volume is private to your Railway service
- Not accessible from other services or users

**Access Control:**
- Only admin users should have Railway dashboard access
- Limit who can SSH into Railway containers
- Monitor access logs for suspicious activity

**Compliance:**
- ⚠️ Session cookies are tied to your personal account
- ⚠️ Ensure usage complies with platform ToS
- ⚠️ Document cookie usage for audit purposes
- ⚠️ Consider rate limiting to avoid account flags

### 6.3 Rate Limiting

**Implement in FastAPI:**
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/process-article")
@limiter.limit("10/minute")  # Max 10 articles per minute
async def process_article(...):
    pass
```

---

## Troubleshooting Guide

### Playwright Issues

**Browser Launch Fails:**
```bash
# Check Playwright installation
playwright install --dry-run chromium

# Reinstall if needed
playwright install chromium --with-deps
```

**Timeout Errors:**
```python
# Increase timeout in config
PLAYWRIGHT_TIMEOUT=60000  # 60 seconds
```

### Authentication Issues

**Session Expired:**
1. Check `storage_state.json` file exists
2. Check file modification time (should be recent)
3. Re-run `setup_auth.py` for affected platform

**Cookies Not Working:**
1. Verify cookies loaded from storage_state
2. Check cookie domain matches target URL
3. Ensure cookies haven't expired

### Database Issues

**Supabase Connection Failed:**
1. Verify SUPABASE_URL and SUPABASE_ANON_KEY
2. Check Supabase dashboard (service status)
3. Test connection from Railway shell:
   ```python
   python3 -c "from supabase import create_client; ..."
   ```

**Embeddings Not Generating:**
1. Verify OPENAI_API_KEY is set
2. Check OpenAI API quota/limits
3. Review logs for OpenAI API errors

---

## Rollback Plan

### If Railway Deployment Fails

**Option 1: Rollback to Previous Deploy**
1. Railway Dashboard → Deployments
2. Select previous working deployment
3. Click "Redeploy"

**Option 2: Continue Using Local Python**
```bash
# Keep running locally until Railway works
cd programs/article_summarizer
python3 scripts/article_summarizer.py "URL"
```

**Option 3: Debug in Railway Shell**
```bash
# SSH into Railway container
railway connect

# Run Python directly
python3 -m app.main
```

---

## Next Steps After Deployment

### Short Term (Week 1)
1. ✅ Monitor Railway logs daily
2. ✅ Test with 5-10 different article types
3. ✅ Verify session persistence over 7 days
4. ✅ Measure actual costs vs. estimates

### Medium Term (Month 1)
1. Add more authenticated platforms (Twitter, LinkedIn)
2. Implement article processing queue (for batch processing)
3. Add webhook notifications for completed articles
4. Set up monitoring alerts (Sentry, etc.)

### Long Term (Month 2+)
1. Migrate RSS feed checker to Railway
2. Implement scheduled article processing (cron jobs)
3. Add analytics dashboard (processing stats)
4. Consider multi-region deployment for speed

---

## Additional Resources

**Railway Documentation:**
- Getting Started: https://docs.railway.app/getting-started
- Environment Variables: https://docs.railway.app/deploy/variables
- Volumes: https://docs.railway.app/deploy/volumes
- Logs: https://docs.railway.app/deploy/logs

**Playwright Documentation:**
- Authentication: https://playwright.dev/python/docs/auth
- API Reference: https://playwright.dev/python/docs/api/class-playwright

**FastAPI Documentation:**
- Tutorial: https://fastapi.tiangolo.com/tutorial/
- Security: https://fastapi.tiangolo.com/tutorial/security/
- Deployment: https://fastapi.tiangolo.com/deployment/

**Supabase Documentation:**
- Python Client: https://supabase.com/docs/reference/python/introduction
- Row Level Security: https://supabase.com/docs/guides/auth/row-level-security

---

## Questions & Support

**Where to Get Help:**
1. **Railway Discord**: https://discord.gg/railway
2. **Playwright GitHub**: https://github.com/microsoft/playwright-python/issues
3. **FastAPI Discord**: https://discord.com/invite/fastapi
4. **This Repository**: Open GitHub issue with `[Railway]` tag

**Common Questions:**

**Q: Can I use Railway's free tier?**
A: Railway no longer has a free tier. Hobby plan starts at $5/month with $5 credit included. Your actual cost will be usage-based (~$15-20/month estimated).

**Q: How do I update the backend code?**
A: Push changes to GitHub main branch. Railway auto-deploys on git push. Or manually trigger deploy from Railway dashboard.

**Q: What happens if Railway goes down?**
A: Article processing will fail. Frontend should handle this gracefully with error messages. Have a rollback plan to run Python locally if needed.

**Q: Can I run multiple Railway services?**
A: Yes! You can split into separate services (e.g., main API + Playwright service). Each service has its own env vars and volumes.

---

**Document Version**: 1.0
**Last Updated**: October 20, 2025
**Author**: Claude Code
**Status**: Ready for Implementation
