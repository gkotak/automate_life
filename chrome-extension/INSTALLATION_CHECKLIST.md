# Installation Checklist

Use this checklist to verify your Chrome extension is ready for distribution.

## ✅ Pre-Installation Setup

### Required Files

- [ ] `manifest.json` exists
- [ ] `background.js` exists
- [ ] `sidepanel/sidepanel.html` exists
- [ ] `sidepanel/sidepanel.css` exists
- [ ] `sidepanel/sidepanel.js` exists
- [ ] `lib/auth.js` exists

### Icon Files (⚠️ YOU MUST ADD THESE)

- [ ] `icons/icon-16.png` exists (16x16 pixels)
- [ ] `icons/icon-48.png` exists (48x48 pixels)
- [ ] `icons/icon-128.png` exists (128x128 pixels)

**How to create icons:**
```bash
# If you have ImageMagick installed:
cd icons
convert your-logo.png -resize 16x16 icon-16.png
convert your-logo.png -resize 48x48 icon-48.png
convert your-logo.png -resize 128x128 icon-128.png

# Or use online tools like:
# - cloudconvert.com
# - resizeimage.net
# - GIMP/Photoshop
```

## ✅ Local Testing

### Load Extension

1. [ ] Open Chrome and go to `chrome://extensions/`
2. [ ] Enable "Developer mode" toggle (top-right)
3. [ ] Click "Load unpacked" button
4. [ ] Select the `chrome-extension` folder
5. [ ] Extension appears in list without errors
6. [ ] Pin extension to toolbar (puzzle icon → pin)

### Test Authentication

1. [ ] Click extension icon → side panel opens
2. [ ] If not logged in, see "Sign In Required" message
3. [ ] Click "Sign In to Particles" → new tab opens
4. [ ] Log in at https://tryparticles.com
5. [ ] Return to extension → main content now shows

### Test Article Processing

1. [ ] Navigate to any article (e.g., https://stratechery.com)
2. [ ] Click extension icon → side panel opens
3. [ ] Verify page title and URL are displayed
4. [ ] Click "Summarize This Page" button
5. [ ] Processing section appears with steps
6. [ ] Watch real-time progress updates
7. [ ] All steps complete successfully
8. [ ] "Success!" message appears with "View Article" button
9. [ ] Click "View Article" → opens article in new tab

### Test Duplicate Detection

1. [ ] Process the same article again
2. [ ] Duplicate warning appears
3. [ ] Message shows when article was processed
4. [ ] "View Existing" button works
5. [ ] "Reprocess Anyway" button works

### Test Options

1. [ ] Toggle "Extract demo video frames" checkbox
2. [ ] Process a screen share video
3. [ ] Verify option is sent to backend

1. [ ] Toggle "Save as private article" checkbox
2. [ ] Process any article
3. [ ] Verify article is saved privately

### Test Error Handling

1. [ ] Process an invalid URL (e.g., chrome://extensions)
2. [ ] Error message appears
3. [ ] Extension doesn't crash

## ✅ Code Quality Checks

### JavaScript

- [ ] No syntax errors in DevTools console
- [ ] All event listeners working
- [ ] SSE connection establishes successfully
- [ ] All SSE events handled correctly
- [ ] Authentication flow works
- [ ] Token caching works

### CSS

- [ ] All styles render correctly
- [ ] Colors match web app design
- [ ] Responsive layout (resize side panel)
- [ ] Icons and buttons look good
- [ ] Animations work smoothly

### Permissions

- [ ] Only required permissions in manifest.json
- [ ] No unnecessary host permissions
- [ ] No security warnings in Chrome

## ✅ Distribution Preparation

### Documentation

- [ ] README.md is complete and accurate
- [ ] QUICK_START.md has clear instructions
- [ ] PROJECT_SUMMARY.md documents architecture
- [ ] All screenshots/images included (if any)

### Build Process

1. [ ] Run `./build.sh` from chrome-extension folder
2. [ ] ZIP file created successfully
3. [ ] ZIP file name includes version number
4. [ ] Verify ZIP contents:
   - [ ] All source files included
   - [ ] No build artifacts
   - [ ] Documentation included

### Version Information

- [ ] Version number set in `manifest.json`
- [ ] Version number matches build output
- [ ] Changelog updated (if exists)

## ✅ Final Checklist

### Before Sharing

- [ ] Extension works on fresh Chrome installation
- [ ] All icons display correctly
- [ ] No console errors or warnings
- [ ] Authentication flow is smooth
- [ ] Processing works reliably
- [ ] Documentation is clear

### Distribution

- [ ] ZIP file uploaded to GitHub Releases (or other platform)
- [ ] Download link is accessible
- [ ] Installation instructions are clear
- [ ] Support channel is available (GitHub Issues)

### Optional (Chrome Web Store)

- [ ] Created Chrome Web Store developer account ($5)
- [ ] Prepared store assets:
  - [ ] Screenshots (1280x800 or 640x400)
  - [ ] Promotional tile (440x280)
  - [ ] Detailed description
  - [ ] Privacy policy
- [ ] Submitted for review
- [ ] Review approved
- [ ] Public URL available

## 🐛 Common Issues

### Extension won't load
- Check for syntax errors in manifest.json
- Verify all required files exist
- Check Chrome DevTools console for errors

### Icons not showing
- Verify icon files exist in correct paths
- Check file names match manifest.json
- Ensure icons are PNG format with correct dimensions

### Authentication fails
- Verify user is logged into web app
- Check token extraction logic in auth.js
- Verify web app URL is correct

### SSE connection fails
- Check backend URL in sidepanel.js
- Verify backend is running (Railway)
- Check network tab in DevTools

### Processing never completes
- Check console for errors
- Verify backend is responding
- Check SSE event handlers

## 📊 Testing Matrix

| Test Case | Status | Notes |
|-----------|--------|-------|
| Fresh install | ⬜ | |
| Authentication | ⬜ | |
| Process article | ⬜ | |
| Duplicate detection | ⬜ | |
| Force reprocess | ⬜ | |
| Demo video option | ⬜ | |
| Private article option | ⬜ | |
| Error handling | ⬜ | |
| Token caching | ⬜ | |
| View article link | ⬜ | |

## ✅ Ready for Distribution!

Once all items are checked:

1. Create GitHub Release with ZIP file
2. Share download link with users
3. Monitor for issues and feedback
4. Update documentation as needed

---

**Need help?** Check README.md or open an issue on GitHub.
