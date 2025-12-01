# Particles User Guide

Particles is your personal content intelligence platform. It helps you save, summarize, and search through articles, videos, and podcasts—so you can spend less time consuming and more time understanding.

---

## Getting Started

### Creating an Account

1. Visit the app and click **Sign in**
2. Choose **Sign up** to create a new account
3. Enter your email and password
4. Check your email for a verification link

Once verified, you're ready to start saving content.

---

## Core Features

### 1. Saving Articles & Videos

The heart of Particles is turning long-form content into digestible summaries.

**To save content:**

1. Click the **New** button in the header
2. Select **New Article**
3. Paste any URL—YouTube videos, blog posts, newsletters, podcasts
4. Click **Process**

The system will:
- Extract the main content from the page
- Download and transcribe any video or audio
- Generate an AI-powered summary with key insights
- Create clickable timestamps for video/audio content
- Save everything to your personal library

**Supported content types:**
- YouTube videos (with full transcript)
- Podcast episodes (audio transcription)
- Blog posts and newsletters (Substack, Medium, etc.)
- News articles
- Any web page with substantial text content

**Pro tip:** For paywalled content you subscribe to, the system can often extract the full text if you're logged in to that service in your browser.

---

### 2. Browsing Your Library

Your home page shows all saved articles with powerful filtering options.

**Quick stats at the top:**
- Total articles saved
- Videos, Audio, and Text articles count

**Filtering options:**
- **My Articles Only** — Toggle to see just your saved content
- **Content Type** — Filter by video, audio, or article
- **Source** — Filter by publication (e.g., "Stratechery", "a]16z")
- **Themes** — Filter by custom themes you've created
- **Date Range** — Find content from specific time periods

**Viewing an article:**

Click any article to see its full summary. Article pages include:
- AI-generated summary with key insights
- Embedded video player (plays at 2x speed by default)
- Clickable timestamps that jump to specific moments
- Full transcript with search highlighting
- Related articles based on content similarity

---

### 3. Searching Your Knowledge Base

Particles offers two search modes to help you find exactly what you need.

**AI Search (Recommended)**
- Uses semantic understanding to find conceptually related content
- Great for questions like "What did experts say about AI agents?"
- Finds content even if your exact words aren't in the text

**Keyword Search**
- Traditional text matching for exact phrases
- Useful when you remember specific quotes or names

**Using search:**
1. Toggle between **AI Search** and **Keyword** modes
2. Type your query and press Enter or click Search
3. Results highlight matching terms
4. Click any result to see the full article with your search terms highlighted

---

### 4. Organizing with Folders

Folders help you group related content—like playlists for your saved articles.

**Creating a folder:**
1. Look at the left sidebar (visible on desktop)
2. Click the **+** button next to "Folders"
3. Enter a name and optional description
4. Click Create

**Adding articles to folders:**
1. On any article card, click the folder icon
2. Check the folders you want to add it to
3. Or click **Create new folder** to make one on the spot

**Browsing folders:**
- Click any folder in the sidebar to filter to just that content
- The URL updates (e.g., `/folder/AI%20Research`) so you can bookmark or share it
- Green badges on article cards show which folders they belong to

**Managing folders:**
- Click the three-dot menu on any folder to rename or delete it
- Collapse the sidebar by clicking the arrow to save screen space

---

### 5. Discovering New Content

Particles can monitor your favorite sources and alert you to new content.

#### Setting Up Content Sources

1. Go to **New > Check for Posts** or navigate to `/sources`
2. Add sources in three ways:
   - **URL** — Paste any website or RSS feed URL
   - **Podcast Search** — Search for podcasts by name
   - **YouTube Channel** — Search and add YouTube channels

The system will discover the RSS feed and show you recent posts. Once added, you can check for new content anytime.

#### Checking Your Podcast History

If you use PocketCasts, Particles can sync your listening history:

1. Go to **New > Podcast Listening History**
2. The system scans your recent podcast episodes
3. One-click to process any episode into a summary

This is perfect for capturing insights from podcasts you listened to on the go.

---

### 6. Chat with Your Content

Have a conversation with your entire content library using the **Chat** feature.

1. Click **Chat** in the header
2. Ask questions about any content you've saved
3. The AI will search your library and provide answers with sources

Example questions:
- "What are the key arguments for and against AI regulation?"
- "Summarize what I've saved about product-market fit"
- "Find content about startup fundraising"

Previous conversations are saved in the sidebar so you can continue later.

---

### 7. Themes (Admin Feature)

If you're an admin, you can create themes to categorize content across your organization.

1. Go to **Settings > Themes** (or `/settings/themes`)
2. Create themes like "Market Research", "Competitor Analysis", "Product Ideas"
3. Themes appear as filter options in the main library view

---

## Tips for Power Users

### Keyboard Shortcuts

- **Enter** in search — Execute search
- **Escape** — Close modals and dropdowns

### Video Playback

- Videos auto-play at 2x speed to save time
- Click any timestamp in the summary to jump to that moment
- The transcript syncs with video playback

### Sharing Content

- Each article has a shareable URL (e.g., `/article/123`)
- Folder URLs are bookmarkable (e.g., `/folder/Product%20Research`)
- Use the share button on articles to copy the link

### Managing Your Library

- **Delete articles** you no longer need using the trash icon
- **External link** icon opens the original source in a new tab
- Articles show content type (video/audio/article) with colored badges

---

## Frequently Asked Questions

**Q: How long does it take to process a video?**
A: Processing time depends on content length. A 10-minute video typically takes 1-2 minutes. You'll see real-time progress during processing.

**Q: Can I process paywalled content?**
A: Yes, for services you subscribe to. The system uses your authenticated session to access content from Substack, Medium, Patreon, and similar platforms.

**Q: What happens if I process the same URL twice?**
A: You'll see a warning that the article already exists, with a link to the existing version.

**Q: Is my content private?**
A: Yes. Your saved content is tied to your account and organization. Only you and your organization members can see it.

**Q: Can I export my summaries?**
A: Each article page can be printed or saved as PDF using your browser's print function.

---

## Getting Help

If you encounter issues or have feature requests:
- Check that your browser is up to date
- Try refreshing the page
- Contact support with details about what you were trying to do

---

## Summary of Navigation

| Page | URL | Purpose |
|------|-----|---------|
| Home | `/` | Browse all saved articles |
| Folder View | `/folder/{name}` | View articles in a specific folder |
| Article | `/article/{id}` | Read a specific article summary |
| Chat | `/chat` | Converse with your content library |
| New Article | `/new/article` | Process a new URL |
| Podcast History | `/new/podcast-history` | Check PocketCasts history |
| Check Posts | `/new/posts` | Scan sources for new posts |
| Content Sources | `/sources` | Manage RSS feeds and channels |
| Themes | `/settings/themes` | Manage content themes (admin) |

---

Happy reading!
