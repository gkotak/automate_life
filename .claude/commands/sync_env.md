---
description: Sync environment variables to Vercel and Railway via GitHub Actions
---

# Sync Environment Variables

Trigger GitHub Actions to sync environment variables from GitHub Secrets to deployment platforms.

## Usage

```bash
/sync_env [target]
```

**Arguments:**
- No argument or `all` - Sync to both Vercel and Railway
- `vercel` or `frontend` - Sync to Vercel only
- `railway` or `backend` - Sync to Railway only

## Examples

```bash
/sync_env                  # Sync to both platforms
/sync_env all              # Sync to both platforms
/sync_env vercel           # Sync to Vercel only
/sync_env frontend         # Sync to Vercel only (alias)
/sync_env railway          # Sync to Railway only
/sync_env backend          # Sync to Railway only (alias)
```

## Instructions

You need to trigger the GitHub Actions workflows manually. Here's what to do:

1. **Parse the argument** from `$ARGUMENTS`:
   - Extract target: vercel, railway, frontend, backend, all, or empty
   - Normalize aliases: frontend→vercel, backend→railway

2. **Provide instructions** to the user based on the target:

   For **Vercel**:
   ```
   🔗 Go to: https://github.com/gkotak/automate_life/actions/workflows/sync-env-vercel.yml
   1. Click "Run workflow"
   2. Type "sync" in the confirm field
   3. Click "Run workflow" button

   This will sync these secrets to Vercel:
   - NEXT_PUBLIC_SUPABASE_URL
   - NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
   - OPENAI_API_KEY
   - BRAINTRUST_API_KEY
   ```

   For **Railway**:
   ```
   🔗 Go to: https://github.com/gkotak/automate_life/actions/workflows/sync-env-railway.yml
   1. Click "Run workflow"
   2. Type "sync" in the confirm field
   3. Click "Run workflow" button

   This will sync these secrets to Railway:
   - SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY
   - OPENAI_API_KEY
   - ANTHROPIC_API_KEY
   - DEEPGRAM_API_KEY
   - BRAINTRUST_API_KEY
   - POCKETCASTS_EMAIL/PASSWORD (if configured)
   ```

3. **Remind the user** about prerequisites:
   - GitHub Secrets must be set up first
   - VERCEL_TOKEN, RAILWAY_TOKEN, project IDs must be configured
   - See setup instructions below if first time

## Setup (First Time Only)

### GitHub Secrets Required

**For Vercel workflow:**
- `VERCEL_TOKEN` - Get from https://vercel.com/account/tokens
- `VERCEL_ORG_ID` - Found in Vercel project settings
- `VERCEL_PROJECT_ID` - Found in Vercel project settings
- All environment variables you want to sync (OPENAI_API_KEY, etc.)

**For Railway workflow:**
- `RAILWAY_TOKEN` - Get from Railway dashboard
- `RAILWAY_PROJECT_ID` - Found in Railway project settings
- All environment variables you want to sync

### How to Add GitHub Secrets

1. Go to: https://github.com/gkotak/automate_life/settings/secrets/actions
2. Click "New repository secret"
3. Add each secret name and value
4. Click "Add secret"

## Notes

- This triggers GitHub Actions (runs on GitHub's servers, not locally)
- Workflows sync ALL configured secrets each time
- Safe to run multiple times (idempotent)
- Requires manual confirmation ("sync") to prevent accidental runs
