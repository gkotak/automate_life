# Domain Update Summary

## ✅ All Updates Complete

The Chrome extension has been updated from **Automate Life** (automate-life.vercel.app) to **Particles** (tryparticles.com).

## 🔄 Files Updated

### Core Extension Files

1. **manifest.json**
   - Extension name: `Particles - Article Summarizer`
   - Host permissions updated:
     - ✅ `https://tryparticles.com/*`
     - ✅ `https://www.tryparticles.com/*` (added for www subdomain)
     - Removed: `https://automate-life.vercel.app/*`

2. **lib/auth.js**
   - `WEB_APP_URL` → `https://tryparticles.com`
   - Header comment updated to "Particles Extension"
   - Authentication now detects session from tryparticles.com

3. **sidepanel/sidepanel.js**
   - `WEB_APP_URL` → `https://tryparticles.com`
   - Header comment updated to "Particles Extension"

4. **sidepanel/sidepanel.html**
   - Title: `Particles - Summarizer`
   - Alt text for logo: `Particles`
   - Sign in button: "Sign In to Particles"
   - Auth card text: "Sign in to your Particles account"
   - Footer link: `https://tryparticles.com`

5. **sidepanel/sidepanel.css**
   - Header comment updated to "Particles Extension"

6. **background.js**
   - Header comment updated to "Particles Extension"
   - Console log message updated

7. **build.sh**
   - Script header: "Particles Chrome Extension"
   - Output filename: `particles-extension-v1.0.0.zip`

### Documentation Files

All markdown files updated with global search and replace:
- "Automate Life" → "Particles"
- "automate-life.vercel.app" → "tryparticles.com"
- "automate_life" → "particles"

Files updated:
- ✅ **README.md** - Full documentation
- ✅ **QUICK_START.md** - Installation guide
- ✅ **PROJECT_SUMMARY.md** - Technical overview
- ✅ **INSTALLATION_CHECKLIST.md** - Testing checklist

## 🔑 Critical Authentication Changes

### Before (Broken)
```javascript
const WEB_APP_URL = 'https://automate-life.vercel.app';

// Tried to find tabs matching automate-life.vercel.app
chrome.tabs.query({ url: `${WEB_APP_URL}/*` })
```

### After (Fixed)
```javascript
const WEB_APP_URL = 'https://tryparticles.com';

// Now correctly finds tabs matching tryparticles.com
chrome.tabs.query({ url: `${WEB_APP_URL}/*` })
```

### What This Fixes

1. **Token Detection** - Extension can now find your tryparticles.com tabs
2. **LocalStorage Access** - Can read Supabase auth token from the correct domain
3. **Login Redirect** - Opens tryparticles.com/login instead of old domain
4. **Host Permissions** - Chrome allows extension to access tryparticles.com

## 🧪 Testing Required

After reloading the extension, verify:

### 1. Authentication Flow
- [ ] Open https://tryparticles.com and sign in
- [ ] Click extension icon
- [ ] Extension should detect your session automatically
- [ ] Should NOT show "Sign In Required" if already logged in

### 2. Token Extraction
Open DevTools console in side panel and check:
```
Found web app tab: Particles - Article Summarizer
Successfully extracted token from web app
```

### 3. Processing
- [ ] Navigate to any article
- [ ] Click extension icon
- [ ] Click "Summarize This Page"
- [ ] Should connect successfully to backend
- [ ] Should complete processing without auth errors

## 🔧 How to Reload Extension

1. Go to `chrome://extensions/`
2. Find "Particles - Article Summarizer"
3. Click the **refresh icon** (circular arrow)
4. Close and reopen the side panel
5. Test authentication flow

## 📋 Manifest Permissions

The extension now has permission to access:
```json
"host_permissions": [
  "https://*.railway.app/*",
  "https://tryparticles.com/*",
  "https://www.tryparticles.com/*",
  "https://gmwqeqlbfhxffxpsjokf.supabase.co/*"
]
```

Note: Added `www.tryparticles.com` in case your domain uses www subdomain.

## 🐛 Common Issues & Solutions

### Issue: "Sign In Required" even when logged in

**Cause**: Chrome may be caching old permissions

**Solution**:
1. Go to `chrome://extensions/`
2. Remove the extension completely
3. Reload it with "Load unpacked"
4. Chrome will request new permissions for tryparticles.com

### Issue: Token not found in web app

**Cause**: Not logged into tryparticles.com in any tab

**Solution**:
1. Open https://tryparticles.com in a new tab
2. Sign in with your credentials
3. Keep that tab open
4. Open extension side panel again

### Issue: Host permission error

**Cause**: Old permissions cached

**Solution**:
1. Reload extension in `chrome://extensions/`
2. Or remove and re-add extension
3. Chrome will show new permission dialog for tryparticles.com

## ✨ What's Different Now

### Authentication Priority
1. Check extension storage for cached token (still works)
2. Check **tryparticles.com** tabs for token (fixed!)
3. Redirect to **tryparticles.com/login** (fixed!)

### Token Storage Key
Still looks for: `sb-<project-ref>-auth-token` in localStorage
(This is Supabase's standard, works on any domain)

### API Endpoints
Backend URL unchanged: `https://article-summarizer-backend-production.up.railway.app`
(Backend doesn't care about frontend domain)

## 🎯 Next Steps

1. **Test immediately**: Reload extension and verify authentication works
2. **Clear cache if needed**: Remove and re-add extension if issues persist
3. **Check console logs**: DevTools will show which domain it's checking
4. **Verify permissions**: Chrome should show tryparticles.com permission

---

**Status**: ✅ All files updated and ready for testing
**Version**: 1.0.0 (no version bump needed for domain change)
**Build command**: `./build.sh` (outputs `particles-extension-v1.0.0.zip`)
