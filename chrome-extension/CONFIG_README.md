# Configuration Guide

## Switching Between Local and Production

The extension uses [config.js](config.js) to manage environment settings.

### Local Development (Default)

Edit [config.js](config.js) and set:
```javascript
const ENVIRONMENT = 'local';
```

This will use:
- **Backend**: `http://localhost:8000`
- **Web App**: `http://localhost:3000`
- **Supabase**: Production Supabase (shared)

### Production

Edit [config.js](config.js) and set:
```javascript
const ENVIRONMENT = 'production';
```

This will use:
- **Backend**: `https://article-summarizer-backend-production.up.railway.app`
- **Web App**: `https://tryparticles.com`
- **Supabase**: Production Supabase

## After Changing Config

1. **Save** [config.js](config.js)
2. **Reload** the extension in `chrome://extensions/`
3. **Open DevTools** in the side panel (right-click → Inspect)
4. **Check console** - you should see:
   ```
   [CONFIG] Running in local mode
   [CONFIG] API_URL: http://localhost:8000
   [CONFIG] WEB_APP_URL: http://localhost:3000
   ```

## Testing Local Development

1. Make sure your local servers are running:
   ```bash
   # Terminal 1 - Backend
   cd programs/article_summarizer_backend
   uvicorn app.main:app --reload

   # Terminal 2 - Frontend
   cd web-apps/article-summarizer
   npm run dev
   ```

2. Open http://localhost:3000 and sign in

3. Open the extension - it should detect your local session

## Permissions

The manifest includes permissions for both local and production URLs:
- ✅ `http://localhost:3000/*` (local web app)
- ✅ `http://localhost:8000/*` (local backend)
- ✅ `https://tryparticles.com/*` (production web app)
- ✅ `https://*.railway.app/*` (production backend)

You don't need to modify manifest.json when switching environments.
