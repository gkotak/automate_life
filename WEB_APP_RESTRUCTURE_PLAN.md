# Web App Restructure Plan

## Proposed Change

Move from:
```
programs/article_summarizer/web-app/
```

To:
```
web-apps/article-summarizer/
web-apps/[future-app-2]/
web-apps/[future-app-3]/
```

## Current Structure Analysis

### Existing Layout
```
automate_life/
├── programs/
│   ├── article_summarizer/
│   │   ├── common/              # Python utilities
│   │   ├── processors/          # Python processors
│   │   ├── scripts/             # Python scripts
│   │   ├── logs/                # Processing logs
│   │   ├── migration/           # Database migration
│   │   ├── web-app/            ⭐ Next.js app (PORT 3000)
│   │   │   ├── src/
│   │   │   ├── package.json
│   │   │   ├── next.config.ts
│   │   │   └── .env.local
│   │   └── *.md                 # Documentation
│   └── check_new_posts/         # Python RSS checker
└── .env.local                   # Shared credentials
```

### Key Observations

1. **Web app is deeply nested** (4 levels deep)
2. **Mixed Python + JavaScript** in same folder
3. **Deployment currently via Vercel** (push-env-to-vercel.sh script exists)
4. **No .vercel/ directory** - likely deploying manually or via GitHub integration
5. **Uses @/ import alias** - configured in next.config.ts
6. **Supabase integration** - reads from NEXT_PUBLIC_SUPABASE_* env vars

---

## Proposed Structure

### Option A: Top-Level Web Apps (Recommended)

```
automate_life/
├── programs/                    # Python backend programs
│   ├── article_summarizer/     # Python-only
│   │   ├── common/
│   │   ├── processors/
│   │   ├── scripts/
│   │   └── logs/
│   └── check_new_posts/
│
├── web-apps/                    # All web frontends ⭐
│   ├── article-summarizer/     # Next.js app
│   │   ├── src/
│   │   ├── public/
│   │   ├── package.json
│   │   ├── next.config.ts
│   │   └── .env.local
│   └── [future-app]/           # Future web apps
│
└── .env.local                   # Shared credentials
```

**Benefits:**
- ✅ Clear separation: Python (programs/) vs JavaScript (web-apps/)
- ✅ Consistent naming: `web-apps/article-summarizer` (kebab-case)
- ✅ Easy to add more web apps in future
- ✅ Shorter paths: `web-apps/article-summarizer` vs `programs/article_summarizer/web-app`
- ✅ Better mental model: programs = backend, web-apps = frontend

**Trade-offs:**
- ⚠️ Python scripts and web app are separated (related code in different folders)
- ⚠️ Need to update import paths in documentation

---

### Option B: Keep Programs, Add Web Subfolder

```
automate_life/
├── programs/
│   ├── article_summarizer/     # Python backend
│   │   ├── common/
│   │   ├── processors/
│   │   ├── scripts/
│   │   └── logs/
│   └── check_new_posts/
│
├── web/                         # All web apps ⭐
│   ├── article-summarizer/
│   └── [future-app]/
│
└── .env.local
```

**Benefits:**
- ✅ Similar to Option A but shorter folder name (`web` vs `web-apps`)
- ✅ Clean separation

**Trade-offs:**
- ⚠️ Less descriptive (`web` could mean many things)

---

### Option C: Hybrid - Keep Related Together

```
automate_life/
├── projects/                    # Rename from "programs"
│   ├── article-summarizer/     # Kebab-case
│   │   ├── backend/            # Python (renamed from root)
│   │   │   ├── common/
│   │   │   ├── processors/
│   │   │   └── scripts/
│   │   └── web/                # Next.js
│   │       ├── src/
│   │       └── package.json
│   └── check-new-posts/
│       └── backend/
│
└── .env.local
```

**Benefits:**
- ✅ Related code stays together (same project folder)
- ✅ Consistent naming (all kebab-case)
- ✅ Clear backend/web separation within each project

**Trade-offs:**
- ⚠️ Bigger change (rename everything)
- ⚠️ Deeper nesting for web apps
- ⚠️ More migration work

---

## My Recommendation: Option A

**Go with top-level `web-apps/` folder**

### Why?

1. **Scalability**: Easy to add new web apps without touching programs/
2. **Clear boundaries**: Backend (Python) vs Frontend (Next.js)
3. **Deployment**: All Vercel apps in one place
4. **Future-proof**: Can add shared UI components in `web-apps/shared/`
5. **Minimal disruption**: Only moves one folder

---

## Migration Plan (Option A)

### Phase 1: Pre-Migration Checks ✅

**Before moving anything, verify:**

1. **Vercel deployment method**
   - [ ] Check if GitHub integration exists (vercel.com dashboard)
   - [ ] Identify deployment trigger (push to main? manual?)
   - [ ] Document current Vercel project settings

2. **Environment variables**
   - [ ] Document all env vars in web-app/.env.local
   - [ ] Check Vercel dashboard for production env vars
   - [ ] Verify Supabase connection strings

3. **Dependencies**
   - [ ] List any Python scripts that reference web-app/
   - [ ] Check if any scripts write to web-app/public/
   - [ ] Verify no hardcoded paths to web-app

4. **Git history**
   - [ ] Consider if preserving git history for web-app is important
   - [ ] Plan for `git mv` vs manual copy

---

### Phase 2: Create New Structure 🔧

**Step 1: Create new web-apps directory**
```bash
mkdir -p web-apps
```

**Step 2: Move web app (preserving git history)**
```bash
# Option A: Git move (preserves history)
git mv programs/article_summarizer/web-app web-apps/article-summarizer

# Option B: Copy then delete (if git mv has issues)
cp -r programs/article_summarizer/web-app web-apps/article-summarizer
# Test first, then:
# git rm -r programs/article_summarizer/web-app
```

**Step 3: Update package.json name**
```json
{
  "name": "article-summarizer-web",  // Keep or change?
  ...
}
```

---

### Phase 3: Update Configuration Files 🔧

**Files that need updates:**

#### 1. `web-apps/article-summarizer/next.config.ts`
```typescript
// Should work as-is (uses __dirname for @/ alias)
// No changes needed! ✅
```

#### 2. `web-apps/article-summarizer/.env.local`
```bash
# Check if any paths reference ../../../
# Update if needed
```

#### 3. `web-apps/article-summarizer/README.md`
```markdown
# Update paths in documentation
- Old: programs/article_summarizer/web-app
- New: web-apps/article-summarizer
```

#### 4. Root documentation files
```bash
# Update references in:
- CLAUDE.md
- README.md (if exists)
- programs/article_summarizer/*.md files
```

---

### Phase 4: Update Vercel Deployment 🚀

**Critical: Vercel needs to know about new path**

#### Option 1: GitHub Integration (Most Common)

If using Vercel GitHub integration:

1. **Update Vercel Project Settings**
   - Go to vercel.com → Your Project → Settings
   - **Root Directory**: Change from `programs/article_summarizer/web-app` to `web-apps/article-summarizer`
   - **Build Command**: Keep as `next build` (default)
   - **Output Directory**: Keep as `.next` (default)
   - **Install Command**: Keep as `npm install` (default)

2. **Test deployment**
   - Push to git
   - Watch Vercel build logs
   - Verify deployment succeeds

#### Option 2: Vercel CLI Deployment

If deploying manually via CLI:

```bash
cd web-apps/article-summarizer
vercel --prod
```

Update any deployment scripts:
```bash
# Old
cd programs/article_summarizer/web-app && vercel --prod

# New
cd web-apps/article-summarizer && vercel --prod
```

#### Option 3: Vercel Configuration File

Create `vercel.json` in root (if needed):
```json
{
  "buildCommand": "cd web-apps/article-summarizer && npm run build",
  "outputDirectory": "web-apps/article-summarizer/.next"
}
```

---

### Phase 5: Update Scripts & Documentation 📝

**Update these files:**

#### 1. `web-apps/article-summarizer/push-env-to-vercel.sh`
```bash
# Should work as-is (uses .env.local in same directory)
# No changes needed! ✅
```

#### 2. Python scripts (if any reference web-app/)
```bash
# Search for references:
grep -r "web-app" programs/article_summarizer/ --include="*.py"

# Update any hardcoded paths
```

#### 3. Documentation files
```bash
# Update all .md files in programs/article_summarizer/
# Replace: programs/article_summarizer/web-app
# With: web-apps/article-summarizer
```

#### 4. Root CLAUDE.md
```markdown
# Update architecture section to reflect new structure
```

---

### Phase 6: Testing Checklist ✅

**Before considering migration complete:**

- [ ] **Local development works**
  ```bash
  cd web-apps/article-summarizer
  npm run dev
  # Test: http://localhost:3000
  ```

- [ ] **Build succeeds**
  ```bash
  cd web-apps/article-summarizer
  npm run build
  ```

- [ ] **Vercel deployment succeeds**
  - Push to git (if GitHub integration)
  - Check Vercel dashboard
  - Test production URL

- [ ] **Environment variables work**
  - Supabase connection works
  - All NEXT_PUBLIC_* vars accessible

- [ ] **Routing works**
  - Homepage: `/`
  - Article pages: `/article/{id}`
  - API routes: `/api/search`, `/api/related`

- [ ] **Static assets load**
  - Images from /public/
  - Favicon
  - Any other static files

- [ ] **Database queries work**
  - Article list loads
  - Article detail pages load
  - Search functionality works
  - Related articles work

---

## Rollback Plan 🔄

**If anything goes wrong:**

### Quick Rollback (Git)
```bash
# If using git mv:
git reset --hard HEAD~1

# If already committed and pushed:
git revert <commit-hash>

# Manual rollback:
git mv web-apps/article-summarizer programs/article_summarizer/web-app
```

### Vercel Rollback
1. Go to Vercel dashboard → Deployments
2. Find previous working deployment
3. Click "Promote to Production"
4. Update Root Directory back to old path (if changed)

---

## Timeline Estimate

**Total: 1-2 hours**

- Phase 1 (Pre-checks): 15 minutes
- Phase 2 (Move files): 5 minutes
- Phase 3 (Update configs): 15 minutes
- Phase 4 (Update Vercel): 10 minutes
- Phase 5 (Update docs): 15 minutes
- Phase 6 (Testing): 20-30 minutes
- Buffer for issues: 30 minutes

---

## Risks & Mitigations

### Risk 1: Vercel build fails after move
**Mitigation:**
- Don't delete old folder until Vercel build succeeds
- Test build locally first (`npm run build`)
- Have rollback plan ready

### Risk 2: Environment variables not found
**Mitigation:**
- Document all env vars before migration
- Push env vars to Vercel again if needed
- Keep .env.local in version control (gitignored but backup locally)

### Risk 3: Broken relative imports
**Mitigation:**
- Uses @/ alias (absolute imports) - should be fine
- Test locally before deploying
- Check for any ../../../ style imports

### Risk 4: Static assets 404
**Mitigation:**
- Verify /public/ folder moved correctly
- Check next.config.ts image domains
- Test all asset URLs after deployment

### Risk 5: Database connection fails
**Mitigation:**
- Env vars should be same
- Test Supabase connection locally first
- Verify NEXT_PUBLIC_SUPABASE_* vars in Vercel

---

## Future Enhancements

**After successful migration:**

### 1. Shared UI Components
```
web-apps/
├── shared/
│   ├── components/     # Shared React components
│   ├── styles/        # Shared CSS
│   └── utils/         # Shared utilities
├── article-summarizer/
└── [future-app]/
```

### 2. Monorepo Setup (Optional)
```bash
# Consider using workspace or monorepo tools:
- npm workspaces
- pnpm workspaces
- Turborepo
- Nx
```

### 3. Consistent Naming
```
web-apps/
├── article-summarizer/     ✅ Kebab-case
├── check-new-posts-ui/     ✅ Kebab-case
└── admin-dashboard/        ✅ Kebab-case
```

---

## Alternative: Minimal Change Option

**If full migration feels too risky right now:**

### Quick Win: Just Rename
```bash
# Minimal change:
git mv programs/article_summarizer/web-app programs/article_summarizer/web

# Update Vercel root directory:
programs/article_summarizer/web

# Done! ✅
```

**Then plan full migration to web-apps/ later when less risky**

---

## Decision Framework

### Choose Option A (web-apps/) if:
- ✅ You plan to add more web apps soon
- ✅ You want clean separation of concerns
- ✅ You're comfortable with Vercel config changes
- ✅ 1-2 hours migration time is acceptable

### Choose Minimal Change if:
- ✅ You want to test the idea first
- ✅ You're nervous about breaking Vercel
- ✅ You want to move faster (<15 minutes)
- ✅ You can do full migration later

### Stay with current structure if:
- ✅ It's working fine and not causing issues
- ✅ No plans for additional web apps soon
- ✅ Team is used to current structure
- ✅ Risk > reward for your use case

---

## My Final Recommendation

**Go with Option A (web-apps/) but do it in stages:**

### Stage 1: Safe Test (Today)
1. Create `web-apps/article-summarizer/` (copy, don't move)
2. Update Vercel to deploy from new path (test deployment)
3. Verify everything works in production
4. Keep old folder as backup

### Stage 2: Full Migration (After 24-48 hours)
1. Once confident new path works, delete old web-app/
2. Update all documentation
3. Commit changes

### Stage 3: Polish (Next week)
1. Add shared/ folder if needed
2. Consider monorepo tools
3. Set up for future web apps

---

## Questions to Answer Before Proceeding

1. **How is web app currently deployed to Vercel?**
   - [ ] GitHub integration (auto-deploy on push)?
   - [ ] Manual CLI deployment?
   - [ ] Other (Vercel for Git, etc.)?

2. **What's the Vercel project name?**
   - Used to identify correct project in dashboard

3. **Any hardcoded references to web-app path?**
   - In Python scripts?
   - In documentation?
   - In deployment scripts?

4. **Comfort level with Vercel changes?**
   - Have you changed Vercel settings before?
   - Do you have admin access to Vercel project?

5. **Timeline preference?**
   - Need it done today?
   - Can wait for safer testing period?
   - Prefer minimal change first?

---

## Conclusion

**Your instinct is right!** Separating web apps from Python programs makes sense for:
- Clarity
- Scalability
- Future growth

**But**: The migration needs careful planning around Vercel deployment.

**My advice**:
1. Answer the questions above
2. Start with safe test (copy, not move)
3. Verify Vercel deployment works
4. Complete full migration once confident

**Risk level**: Medium (Vercel config change is main risk)
**Effort**: 1-2 hours
**Reward**: Better organization, easier to scale

Let's discuss your answers to the questions, then I can help execute the migration safely!
