---
description: Sync environment variables to Vercel and Railway from local .env.production files via APIs
---

# Sync Environment Variables

Run local scripts to sync environment variables from `.env.production` files to deployment platforms using their REST/GraphQL APIs.

## Usage

```bash
/sync_env [target]
```

**Arguments:**
- No argument or `all` - Sync to all platforms (Vercel + both Railway services)
- `vercel` or `frontend` - Sync to Vercel only
- `article_summarizer` or `summarizer` - Sync article_summarizer_backend to Railway
- `content_checker` or `checker` - Sync content_checker_backend to Railway
- `railway` or `backend` - Sync both Railway backends (article_summarizer + content_checker)

## Examples

```bash
/sync_env                      # Sync all platforms
/sync_env all                  # Sync all platforms
/sync_env vercel               # Frontend only
/sync_env frontend             # Frontend only (alias)
/sync_env article_summarizer   # Article summarizer backend only
/sync_env content_checker      # Content checker backend only
/sync_env railway              # Both Railway backends
/sync_env backend              # Both Railway backends (alias)
```

## Instructions

1. **Parse the argument** from `$ARGUMENTS`:
   - Extract target: vercel, railway, frontend, backend, article_summarizer, content_checker, summarizer, checker, all, or empty
   - Normalize aliases:
     - frontend→vercel
     - backend→railway
     - summarizer→article_summarizer
     - checker→content_checker
     - empty→all

2. **Run the appropriate sync script(s)**:

   For **Vercel** (or frontend):
   ```bash
   bash scripts/sync_env_to_vercel.sh --yes
   ```
   - **API**: Vercel REST API (v10 batch endpoint)
   - **Reads from**: `web-apps/article-summarizer/.env.production`
   - **Syncs**: 6-8 variables (NEXT_PUBLIC_*, OPENAI_API_KEY, BRAINTRUST_API_KEY)
   - **Method**: Single batch POST with upsert (no multiple deployments)
   - **Note**: `--yes` flag skips confirmation prompt

   For **article_summarizer**:
   ```bash
   echo "y" | bash scripts/sync_env_to_railway.sh
   ```
   - **API**: Railway GraphQL (variableCollectionUpsert mutation)
   - **Reads from**: `programs/article_summarizer_backend/.env.production`
   - **Syncs**: ~21 variables (Supabase, AI APIs, Playwright config, auth credentials)
   - **Method**: Single batch mutation (avoids rate limits)
   - **Note**: Auto-confirms to avoid interactive prompt

   For **content_checker**:
   ```bash
   echo "y" | bash scripts/sync_env_to_content_checker.sh
   ```
   - **API**: Railway GraphQL (variableCollectionUpsert mutation)
   - **Reads from**: `programs/content_checker_backend/.env.production`
   - **Syncs**: ~9 variables (Supabase, PocketCasts, SerpAPI, CORS)
   - **Method**: Single batch mutation (avoids rate limits)
   - **Note**: Auto-confirms to avoid interactive prompt

   For **railway** (or backend):
   Run both Railway scripts sequentially (article_summarizer + content_checker).
   Auto-confirms both scripts.

   For **all**:
   Run all three scripts sequentially (vercel + article_summarizer + content_checker).
   Auto-confirms all Railway scripts.

3. **Before running**, check prerequisites:
   - `.env.production` files must exist in subdirectories
   - **Vercel**: VERCEL_TOKEN, VERCEL_PROJECT_ID, VERCEL_TEAM_ID
   - **Railway**: RAILWAY_TOKEN, RAILWAY_PROJECT_ID, RAILWAY_ENVIRONMENT_ID, RAILWAY_SERVICE_ID
   - If files don't exist, guide user to copy from `.env.production.example`

4. **Important Notes**:
   - **No CLI installation required** - uses direct API calls via curl
   - **Batch operations** - all variables synced in single request (fast!)
   - **Proper error handling** - shows detailed error messages from APIs
   - **JSON encoding** - uses Python for proper escaping (no shell injection risks)

## Setup (First Time Only)

### 1. Create Production Environment Files

**For Frontend (Vercel):**
```bash
cp web-apps/article-summarizer/.env.production.example \
   web-apps/article-summarizer/.env.production
```
Edit the file and fill in your production values.

**For Article Summarizer Backend (Railway):**
```bash
cp programs/article_summarizer_backend/.env.production.example \
   programs/article_summarizer_backend/.env.production
```
Edit the file and fill in your production values.

**For Content Checker Backend (Railway):**
```bash
cp programs/content_checker_backend/.env.production.example \
   programs/content_checker_backend/.env.production
```
Edit the file and fill in your production values.

### 2. Get Required Tokens

**Vercel Token:**
- Go to: https://vercel.com/account/tokens
- Create new token with full access
- Add to `web-apps/article-summarizer/.env.production`:
  ```
  VERCEL_TOKEN=your_token_here
  ```

**Railway Token:**
- Go to: https://railway.app/account/tokens
- Create new token
- Add to `programs/article_summarizer_backend/.env.production`:
  ```
  RAILWAY_TOKEN=your_token_here
  ```

### 3. Configure Service IDs (if needed)

The sync scripts auto-detect project/service IDs, but you can override:

**For Vercel** - Add to frontend `.env.production`:
```bash
VERCEL_PROJECT_ID=your_project_id  # Optional
VERCEL_ENV=production              # Optional, defaults to production
```

**For Railway** - Add to backend `.env.production`:
```bash
RAILWAY_SERVICE=article-summarizer-backend  # Optional
RAILWAY_ENVIRONMENT=production              # Optional
```

## Technical Details

### APIs Used
- **Vercel**: REST API v10 (`POST /v10/projects/{id}/env?upsert=true`)
- **Railway**: GraphQL API (`variableCollectionUpsert` mutation)

### Features
- ✅ **Batch operations** - Single API call per platform (fast, no rate limits)
- ✅ **No CLI required** - Direct API calls via curl (already installed)
- ✅ **Proper JSON encoding** - Python handles special characters safely
- ✅ **Detailed error messages** - Shows actual API errors with context
- ✅ **Confirmation prompts** - Prevents accidental syncs
- ✅ **Idempotent** - Safe to run multiple times (upserts existing variables)
- ✅ **Gitignored secrets** - `.env.production` never committed to Git

### Security
- Scripts run **locally** (not on GitHub servers)
- Tokens never exposed in logs or Git
- Production secrets separate from development (`.env.local` vs `.env.production`)
