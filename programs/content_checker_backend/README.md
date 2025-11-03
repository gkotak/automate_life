# Content Checker Backend

FastAPI backend for checking new podcasts and posts from various sources.

## Features

- Check PocketCasts for new podcast episodes
- Save discovered content to Supabase database
- API endpoints for frontend integration
- Railway deployment support

## Setup

### Local Development

1. Copy `.env.local.example` to `.env.local` and fill in your credentials:
   ```bash
   cp .env.local.example .env.local
   ```

2. Run the local development server:
   ```bash
   ./run_local.sh
   ```

   This will:
   - Create a virtual environment (if needed)
   - Install dependencies
   - Start the server on http://localhost:8001

3. Access the API:
   - API Documentation: http://localhost:8001/docs
   - Health Check: http://localhost:8001/health

### Railway Deployment

1. Push code to your repository

2. In Railway:
   - Connect your repository
   - Set root directory to `programs/content_checker_backend`
   - Set environment variables from `.env.production.example`

3. Railway will automatically:
   - Build using Dockerfile
   - Deploy to production
   - Provide a public URL

## API Endpoints

### GET /health
Health check endpoint

### GET /api/podcasts/discovered
Get discovered podcast episodes from database

Parameters:
- `limit` (optional): Maximum number of podcasts to return (default: 100)

Headers:
- `X-API-Key`: API key for authentication (optional for local dev)

### POST /api/podcasts/check
Check PocketCasts for new episodes

Headers:
- `X-API-Key`: API key for authentication (optional for local dev)

## Environment Variables

See `.env.local.example` for required environment variables.

## Frontend Integration

The frontend (Next.js app) connects to this backend:

Local:
```
NEXT_PUBLIC_CONTENT_CHECKER_API_URL=http://localhost:8001
NEXT_PUBLIC_CONTENT_CHECKER_API_KEY=your-api-key
```

Production:
```
NEXT_PUBLIC_CONTENT_CHECKER_API_URL=https://your-railway-app.railway.app
NEXT_PUBLIC_CONTENT_CHECKER_API_KEY=your-api-key
```

## Development

### Project Structure
```
content_checker_backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic
│   ├── models/              # Pydantic models
│   └── middleware/          # Authentication
├── core/                    # Shared utilities
│   ├── config.py            # Configuration
│   └── podcast_auth.py      # PocketCasts authentication
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker configuration
├── railway.json             # Railway deployment config
└── run_local.sh             # Local development script
```

### Adding New Features

1. Create models in `app/models/`
2. Create services in `app/services/`
3. Create routes in `app/routes/`
4. Register routes in `app/main.py`
