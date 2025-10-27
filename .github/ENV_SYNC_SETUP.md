# Environment Variable Sync Setup Guide

This guide explains how to set up automatic environment variable syncing from GitHub Secrets to Vercel and Railway.

## Overview

When you update secrets in GitHub, you can manually trigger GitHub Actions to sync them to:
- **Vercel** (Frontend deployment)
- **Railway** (Backend deployment)

## Step 1: Get Required Tokens

### Vercel Token

1. Go to https://vercel.com/account/tokens
2. Click "Create Token"
3. Name it "GitHub Actions Sync"
4. Select scopes: Full Account access (or at minimum: Read/Write for Projects)
5. Copy the token (starts with `vercel_...`)

### Vercel Project IDs

1. Go to your Vercel project settings
2. Click on "General" tab
3. Copy:
   - **Project ID** (e.g., `prj_xxxxx`)
   - **Team/Org ID** (in URL or settings)

### Railway Token

1. Go to https://railway.app/account/tokens
2. Click "New Token"
3. Name it "GitHub Actions Sync"
4. Copy the token

### Railway Project ID

1. Go to your Railway project
2. Click Settings
3. Copy the **Project ID**

## Step 2: Add Secrets to GitHub

Go to: https://github.com/gkotak/automate_life/settings/secrets/actions

Add these secrets by clicking "New repository secret":

### Vercel Deployment Tokens

```
VERCEL_TOKEN=vercel_abc123...
VERCEL_ORG_ID=team_abc123...
VERCEL_PROJECT_ID=prj_abc123...
```

### Railway Deployment Tokens

```
RAILWAY_TOKEN=your_railway_token_here
RAILWAY_PROJECT_ID=your_project_id_here
```

### Application Secrets (Synced to Deployments)

**Supabase (Vercel):**
```
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOi...
```

**Supabase (Railway):**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
SUPABASE_SECRET_KEY=your_secret_key
```

**AI Services:**
```
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
DEEPGRAM_API_KEY=your_deepgram_key
BRAINTRUST_API_KEY=sk-YNA40...
```

**PocketCasts (Optional):**
```
POCKETCASTS_EMAIL=your@email.com
POCKETCASTS_PASSWORD=your_password
```

## Step 3: Test the Workflows

### Test Vercel Sync

1. Go to: https://github.com/gkotak/automate_life/actions/workflows/sync-env-vercel.yml
2. Click "Run workflow" dropdown
3. Type `sync` in the confirm field
4. Click green "Run workflow" button
5. Wait for workflow to complete (watch live logs)
6. Verify in Vercel dashboard: Project → Settings → Environment Variables

### Test Railway Sync

1. Go to: https://github.com/gkotak/automate_life/actions/workflows/sync-env-railway.yml
2. Click "Run workflow" dropdown
3. Type `sync` in the confirm field
4. Click green "Run workflow" button
5. Wait for workflow to complete (watch live logs)
6. Verify in Railway dashboard: Project → Variables

## Step 4: Use the `/sync_env` Command

Once setup is complete, use the Claude slash command:

```bash
/sync_env              # Instructions for both platforms
/sync_env vercel       # Instructions for Vercel only
/sync_env railway      # Instructions for Railway only
/sync_env frontend     # Alias for vercel
/sync_env backend      # Alias for railway
```

## Troubleshooting

### Workflow fails with "401 Unauthorized"

- Check that tokens are valid and not expired
- Verify token has correct permissions
- For Vercel: Token needs project write access
- For Railway: Token needs project access

### Variables not showing in Vercel/Railway

- Check workflow logs for errors
- Verify secret names match exactly (case-sensitive)
- For Vercel: Check you're in the correct environment (production/preview)
- For Railway: Verify project ID is correct

### "Slugs already exist" error

- This is normal for updates - the workflow removes old value first
- If it persists, manually delete the variable in Vercel/Railway dashboard first

## Workflow Details

### What Gets Synced

**Vercel (Frontend):**
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`
- `OPENAI_API_KEY`
- `BRAINTRUST_API_KEY`

**Railway (Backend):**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_SECRET_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DEEPGRAM_API_KEY`
- `BRAINTRUST_API_KEY`
- `POCKETCASTS_EMAIL` (optional)
- `POCKETCASTS_PASSWORD` (optional)

### How to Add More Variables

1. Add the secret to GitHub Secrets
2. Edit the workflow file (`.github/workflows/sync-env-*.yml`)
3. Add new `vercel env add` or `railway variables set` command
4. Commit and push the workflow changes

## Security Notes

- ✅ Secrets are encrypted in GitHub
- ✅ Workflows require manual confirmation
- ✅ Only runs on manual trigger (not automatic)
- ✅ Tokens have limited scope (project-specific)
- ❌ Never commit `.env.local` to Git
- ❌ Never log secret values in workflows
