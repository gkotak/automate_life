# Local Development Guide

This guide shows you how to run the Article Summarizer in local development mode for faster iteration and better debugging.

## Why Local Development?

- ⚡ **Instant feedback** - No waiting for Railway deployments
- 🔍 **Full visibility** - See all backend logs in real-time
- 🐛 **Better debugging** - Use breakpoints, print statements, etc.
- 💰 **Cost efficient** - Save Railway bandwidth during development

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐
│   Next.js Frontend  │ ──────> │  FastAPI Backend    │
│  localhost:3000     │  HTTP   │  localhost:8000     │
│  (Vercel Preview)   │ ◄────── │  (Local Python)     │
└─────────────────────┘   SSE   └─────────────────────┘
         │                                  │
         │                                  │
         └──────────────┬───────────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │   Supabase   │
                 │  (Cloud DB)  │
                 └──────────────┘
```

## Quick Start

### 1. Start the Backend (Terminal 1)

```bash
cd programs/article_summarizer_backend
./run_local.sh
```

This will:
- Activate the virtual environment (or create one if needed)
- Install dependencies from `requirements.txt`
- Load environment variables from `.env.local`
- Start FastAPI server at http://localhost:8000

**Expected output:**
```
🚀 Starting Article Summarizer Backend (Local Development)
📦 Activating virtual environment...
✅ Environment configured

📡 Starting FastAPI server on http://localhost:8000
   API Docs: http://localhost:8000/docs
   Health: http://localhost:8000/health

INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Start the Frontend (Terminal 2)

```bash
cd web-apps/article-summarizer
npm run dev
```

**Expected output:**
```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - Network:      http://192.168.x.x:3000

 ✓ Ready in 2.1s
```

### 3. Open the Admin Page

Navigate to: **http://localhost:3000/admin**

The admin page will now connect to your **local backend** at `localhost:8000` instead of Railway.

## Environment Configuration

### Backend (.env.local)

Located at: `programs/article_summarizer_backend/.env.local`

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...

# Local Development API Key
API_KEY=test-api-key-for-local-development-only

# Playwright
PLAYWRIGHT_HEADLESS=false  # Shows browser for debugging
PLAYWRIGHT_TIMEOUT=30000
PLAYWRIGHT_SCREENSHOT_ON_ERROR=false

# Storage
STORAGE_DIR=./storage

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Frontend (.env.local)

Located at: `web-apps/article-summarizer/.env.local`

```bash
# Supabase (public)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...

# OpenAI (server-only)
OPENAI_API_KEY=sk-proj-...

# Backend API (LOCAL for development)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=test-api-key-for-local-development-only
```

## Testing SSE in Local Mode

When you submit an article in the admin UI, you'll see:

**Backend Terminal (Terminal 1):**
```
INFO:     Processing article request: https://example.com/article
INFO:     📡 [SSE] Created event emitter for job abc123
INFO:     📡 [SSE] Started streaming events for job abc123
INFO:     📡 [SSE] Sending initial ping for job abc123
INFO:     📡 [SSE] Emitted fetch_start for job abc123
INFO:     📡 [SSE] Streaming event 'fetch_start' for job abc123
INFO:     📡 [SSE] Emitted media_detected for job abc123
...
```

**Browser Console:**
```
Job started with ID: abc123
EventSource connection opened for job: abc123
PING received: {message: "SSE connection established"}
Event: fetch_start {elapsed: 0}
Event: fetch_complete {elapsed: 3}
Event: media_detected {media_type: "audio", elapsed: 5}
...
```

## Switching Between Local and Production

### Understanding Environment Files

**You DON'T need to manually switch!** The system uses different files for different environments:

```
┌──────────────────────────────────────────────────────────────┐
│  ENVIRONMENT FILE USAGE                                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  .env.local (LOCAL DEVELOPMENT)                              │
│  ├─ Used when: npm run dev                                   │
│  ├─ Location: Only on your computer                          │
│  ├─ API URL: http://localhost:8000                           │
│  └─ Never committed to Git / Never on Vercel                 │
│                                                              │
│  .env.production (VERCEL PRODUCTION)                         │
│  ├─ Used when: Vercel builds & deploys                       │
│  ├─ Location: Vercel dashboard environment variables         │
│  ├─ API URL: https://automatelife-production.up.railway.app  │
│  └─ Pushed via: ./push-env-to-vercel.sh                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### The Key Insight

**YES - Vercel production ALWAYS uses Railway (production backend)!**

Here's why:
1. `.env.local` is in `.gitignore` → **Never deployed to Vercel**
2. `.env.production` contains Railway URL → **Pushed to Vercel via script**
3. Vercel reads from its own environment variables → **Always points to Railway**

### Setting Up Vercel Production (One-Time Setup)

Run this from `web-apps/article-summarizer`:

```bash
# Make sure you're logged in to Vercel CLI
vercel login

# Push production environment variables to Vercel
./push-env-to-vercel.sh

# Verify in Vercel dashboard
open https://vercel.com/dashboard
```

This reads `.env.production` (with Railway URL) and pushes to Vercel.

### Summary Table

| Environment | Where | API URL | How to Use |
|------------|-------|---------|------------|
| **Local Dev** | Your computer | `localhost:8000` | `npm run dev` uses `.env.local` |
| **Vercel Production** | Cloud (vercel.app) | Railway URL | Vercel uses dashboard env vars |
| **Railway Backend** | Cloud (railway.app) | N/A | Auto-deploys from `main` branch |

### When You Make Changes

**Local Development:**
- Edit `.env.local` → Restart `npm run dev` → Changes apply immediately

**Vercel Production:**
- Edit `.env.production` → Run `./push-env-to-vercel.sh` → Redeploy on Vercel

**Note:** The frontend code automatically falls back to Railway URLs if environment variables are not set, so production will always work even if you forget to set env vars.

## Debugging Tips

### 1. Backend Logs

All logs appear in Terminal 1 where you ran `./run_local.sh`. Look for:
- `📡 [SSE]` - SSE streaming events
- `🔒` - Authentication/API key issues
- `❌` - Errors during processing
- `✅` - Successful operations

### 2. Frontend Console

Open browser DevTools (F12) → Console tab to see:
- SSE connection status
- Event reception timing
- Any JavaScript errors

### 3. API Documentation

Visit http://localhost:8000/docs for interactive API documentation where you can:
- Test endpoints manually
- See request/response schemas
- Try different parameters

### 4. Health Check

Visit http://localhost:8000/health to verify:
- Backend is running
- Database connection works
- Browser session is configured

### 5. Hot Reload

Both frontend and backend support hot reload:
- **Backend:** uvicorn auto-reloads when you edit Python files
- **Frontend:** Next.js auto-reloads when you edit TypeScript/React files

No need to restart servers during development!

## Common Issues

### Port Already in Use

If `localhost:8000` or `localhost:3000` is already in use:

```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### Dependencies Out of Date

```bash
# Backend
cd programs/article_summarizer_backend
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Frontend
cd web-apps/article-summarizer
npm install
```

### CORS Errors

Make sure `CORS_ORIGINS` in backend `.env.local` includes:
```
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### SSE Connection Fails

1. Check backend is running at `localhost:8000`
2. Check frontend `.env.local` has correct `NEXT_PUBLIC_API_URL`
3. Restart Next.js dev server to pick up env var changes

## Deployment to Production

When you're ready to deploy:

1. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: your changes"
   git push
   ```

2. **Railway auto-deploys** the backend from `main` branch

3. **Vercel auto-deploys** the frontend (but use Railway API URL in production)

4. **Update Vercel environment variables** to use Railway:
   ```bash
   cd web-apps/article-summarizer
   ./push-env-to-vercel.sh
   ```

   Then in Vercel dashboard, set:
   ```
   NEXT_PUBLIC_API_URL=https://automatelife-production.up.railway.app
   NEXT_PUBLIC_API_KEY=article-summarizer-production-key-2025
   ```

## Summary

**Development:** Local backend (localhost:8000) + Local frontend (localhost:3000)
**Production:** Railway backend + Vercel frontend

This gives you the best of both worlds: fast iteration during development and reliable cloud hosting in production.
