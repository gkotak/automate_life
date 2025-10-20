# Railway Backend Dependencies

## System Dependencies (Installed via Dockerfile)

All of these are automatically installed when Railway builds your Docker container:

### ✅ Playwright + Chromium
**Purpose**: Browser automation for authentication and anti-bot protection
**Installation**:
```dockerfile
RUN playwright install chromium
RUN playwright install-deps chromium
```
**What it includes**:
- Chromium browser binary
- All required system libraries (libnss3, libgtk-3-0, libx11-6, etc.)
- WebDriver for browser control

**Used for**:
- Bypassing Cloudflare and anti-bot measures
- Loading JavaScript-heavy sites
- Persistent browser sessions with cookies
- Authenticated content access

### ✅ ffmpeg
**Purpose**: Audio/video processing and transcription
**Installation**:
```dockerfile
RUN apt-get install -y ffmpeg
```

**Used for**:
- Extracting audio from video files
- Splitting large audio files into chunks (for Whisper API 25MB limit)
- Converting audio formats
- Processing audio for transcription

**Where it's used in code**:
- `article_summarizer.py:_transcribe_large_audio_file()` - Splits audio files >25MB
- `pydub.AudioSegment.from_file()` - Requires ffmpeg backend

### ✅ System Libraries for Chromium
**Purpose**: Support headless browser operation
**Includes**:
- libnss3, libnspr4 - Network Security Services
- libatk, libgtk-3-0 - GUI toolkit libraries
- libx11-6, libxcb1 - X11 display libraries
- libasound2 - Audio support
- fonts-liberation - Fonts for proper rendering

## Python Dependencies (Installed via requirements.txt)

### Web Framework
- **fastapi** - Modern Python web framework
- **uvicorn** - ASGI server for FastAPI
- **python-multipart** - Form data parsing

### Web Scraping & HTTP
- **requests** - HTTP library
- **beautifulsoup4** - HTML parsing
- **lxml** - XML/HTML parser backend

### Browser Automation
- **playwright** - Browser automation library

### Media Processing
- **youtube-transcript-api** - Extract YouTube transcripts
- **yt-dlp** - Download/extract video metadata
- **pydub** - Audio manipulation (requires ffmpeg)

### AI APIs
- **anthropic** - Claude AI API client
- **openai** - OpenAI API client (for Whisper, embeddings)

### Database
- **supabase** - Supabase Python client

### Utilities
- **python-dotenv** - Environment variable management

## Verification

After Railway deploys, verify all dependencies are installed:

```bash
# SSH into Railway container
railway connect

# Check Playwright
playwright --version

# Check Chromium
ls -la ~/.cache/ms-playwright/chromium*/

# Check ffmpeg
ffmpeg -version

# Check Python packages
pip list | grep -E "playwright|pydub|fastapi"
```

## Size Implications

**Docker Image Size**: ~1.5-2GB
- Base Python image: ~300MB
- Playwright + Chromium: ~800MB
- System libraries: ~200MB
- Python packages: ~200MB

**Railway Disk Usage**:
- Docker image: ~2GB
- Storage volume: 1GB (browser sessions)
- Total: ~3GB

**Build Time**:
- First build: 5-10 minutes (downloads everything)
- Subsequent builds: 2-3 minutes (Docker layer caching)

## Troubleshooting

### Playwright Not Working
```bash
# Reinstall Playwright browsers
playwright install chromium --with-deps
```

### ffmpeg Not Found
```bash
# Check if installed
which ffmpeg

# Reinstall if needed (in Dockerfile)
RUN apt-get update && apt-get install -y ffmpeg
```

### Audio Processing Fails
Check both:
1. ffmpeg is installed: `ffmpeg -version`
2. pydub is installed: `pip show pydub`

## Notes

- All dependencies are installed during Docker build - no manual installation needed
- Railway automatically rebuilds when Dockerfile or requirements.txt changes
- System dependencies are cached between builds for faster deployment
- Python dependencies use pip cache for faster installs

## Comparison: Local vs Railway

| Dependency | Local (macOS) | Railway (Docker) |
|------------|---------------|------------------|
| Playwright | `pip install playwright` | ✅ Dockerfile |
| Chromium | `playwright install chromium` | ✅ Dockerfile |
| ffmpeg | `brew install ffmpeg` | ✅ Dockerfile |
| pydub | `pip install pydub` | ✅ requirements.txt |
| Python packages | `pip install -r requirements.txt` | ✅ Dockerfile |

**Key difference**: On Railway, everything is automated in the Docker build process. No manual steps required!
