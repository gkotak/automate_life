# Article Summarizer Backend

FastAPI backend service for article summarization, deployed on Railway.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your API keys

# Run server
uvicorn app.main:app --reload --port 8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Process article (requires API key)
curl -X POST http://localhost:8000/api/process-article \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=example"}'
```

## Railway Deployment

See `.claude/Docs/RAILWAY_MIGRATION_GUIDE.md` for complete deployment instructions.

### Quick Deploy Steps

1. Create Railway project from GitHub repo
2. Set root directory: `programs/article_summarizer_backend`
3. Add environment variables (see `.env.example`)
4. Add persistent volume mounted at `/app/storage`
5. Deploy!

## Authentication Setup

After deploying to Railway, you need to configure browser authentication:

### Option 1: Upload Cookies (Quickest)

```bash
# Extract cookies locally
python3 scripts/extract_cookies.py

# Upload to Railway
curl -X POST https://your-app.railway.app/api/auth/upload-cookies \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @cookies.json
```

### Option 2: Interactive Login (Recommended)

```bash
# Connect to Railway shell
railway connect

# Run authentication setup
python3 scripts/setup_auth.py --platform substack
```

## Architecture

```
FastAPI Backend
├── Article Processing (Claude AI)
├── Video/Audio Transcription (YouTube, Whisper)
├── Browser Automation (Playwright)
│   └── Anti-bot protection (Cloudflare, JS sites)
│   └── Authentication (paywalled content)
└── Database Integration (Supabase)
```

## Key Features

- ✅ **Zero Local Dependencies**: Runs entirely on Railway
- ✅ **Browser-in-Docker**: Playwright for auth + anti-bot
- ✅ **Persistent Sessions**: Browser state saved to Railway volume
- ✅ **API Authentication**: Secure endpoints with API keys
- ✅ **Production Ready**: Error handling, logging, health checks

## Endpoints

### Public
- `GET /` - Service info
- `GET /health` - Health check

### Protected (Requires API Key)
- `POST /api/process-article` - Process article URL
- `POST /api/auth/upload-cookies` - Upload authentication cookies
- `GET /api/auth/status` - Check auth configuration
- `DELETE /api/auth/clear-session` - Clear stored sessions

## Environment Variables

See `.env.example` for all configuration options.

Required:
- `ANTHROPIC_API_KEY` - Claude API key
- `OPENAI_API_KEY` - OpenAI API key (for embeddings)
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase anon key
- `API_KEY` - Backend API authentication key

## Cost Estimate

Railway usage: ~$15-20/month with Playwright

## Documentation

- Full Migration Guide: `.claude/Docs/RAILWAY_MIGRATION_GUIDE.md`
- Backend Auth Strategy: `.claude/Docs/BACKEND_AUTH_PLAN.md`

## Support

For issues or questions, see the main repository README or open a GitHub issue.
