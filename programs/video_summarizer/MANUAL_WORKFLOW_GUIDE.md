# Manual Video Summarizer Workflow

## Overview

The video summarizer has been converted to a **manual-only workflow**. No automation or scheduling is included - all operations require manual execution.

## 🔧 Quick Start

### 1. Manual Post Discovery
```bash
# Check for new posts manually
./manual_check.sh

# Or use the direct processor
python3 processors/post_checker.py
```

### 2. Review Discovered Posts
```bash
# Quick check what's new
./scripts/quick_process.sh check

# Get statistics
./scripts/quick_process.sh stats

# Filter by source
./scripts/quick_process.sh stratechery
./scripts/quick_process.sh lenny
```

### 3. Process Posts
```bash
# Process specific posts
python3 scripts/post_manager.py process post_id1 post_id2

# Bulk process multiple posts
./scripts/quick_process.sh bulk 5

# Process posts from specific source
python3 scripts/post_manager.py bulk --source=stratechery --action=process --limit=3
```

## 📊 Core Tools

### **1. Manual Post Checker (`./manual_check.sh`)**
- Manually checks newsletter/blog feeds for new posts
- No automation or scheduling
- Outputs summary with management commands

### **2. Post Manager (`scripts/post_manager.py`)**
- Powerful filtering and batch processing
- JSON-based data management
- Flexible criteria-based operations

### **3. Quick Process (`scripts/quick_process.sh`)**
- Simplified wrapper for common tasks
- Easy-to-remember commands
- Perfect for daily manual workflow

## 🎯 Common Workflows

### **Morning Routine (Manual)**
```bash
# 1. Check for new posts
./manual_check.sh

# 2. Review what's interesting
./scripts/quick_process.sh check

# 3. Process posts you want
./scripts/quick_process.sh process 3
```

### **Source-Specific Processing**
```bash
# Focus on specific newsletters
python3 scripts/post_manager.py list --source=stratechery --limit=5
python3 scripts/post_manager.py list --source=lennysnewsletter --limit=5

# Process posts from preferred sources
python3 scripts/post_manager.py bulk --source=stratechery --action=process --limit=3
```

### **Bulk Management**
```bash
# Skip posts you're not interested in
python3 scripts/post_manager.py bulk --source=creatoreconomy --action=skip --limit=10

# Process recent posts
python3 scripts/post_manager.py list --since=2025-10-01 --limit=5
python3 scripts/post_manager.py process post_id1 post_id2 post_id3
```

## 📝 Configuration

### **Newsletter Links (`newsletter_podcast_links.md`)**
Edit this file to add/remove newsletters and blogs to monitor:
```markdown
# Newsletter & Podcast Links

## Stratechery
- https://stratechery.passport.online/feed/podcast/xxx

## Lenny's Newsletter
- https://www.lennysnewsletter.com/

## Creator Economy
- https://creatoreconomy.so/
```

### **Environment Variables (`.env`)**
```bash
# Claude API (required for AI summaries)
ANTHROPIC_API_KEY=your_claude_api_key

# OpenAI API (required for transcription)
OPENAI_API_KEY=your_openai_api_key

# Optional: Newsletter authentication
NEWSLETTER_SESSION_COOKIES="cookie1=value1; cookie2=value2"
```

## 🔍 Filtering & Search

### **By Date**
```bash
# Posts since specific date
python3 scripts/post_manager.py list --since=2025-10-01

# Recent activity
python3 scripts/post_manager.py stats
```

### **By Source**
```bash
# Stratechery posts
python3 scripts/post_manager.py list --source=stratechery

# Lenny's Newsletter
python3 scripts/post_manager.py list --source=lennysnewsletter

# Creator Economy
python3 scripts/post_manager.py list --source=creatoreconomy
```

### **By Status**
```bash
# Newly discovered posts
python3 scripts/post_manager.py list --status=discovered

# Completed posts
python3 scripts/post_manager.py list --status=completed

# Failed processing attempts
python3 scripts/post_manager.py list --status=failed
```

### **Export for External Tools**
```bash
# Get URLs only
python3 scripts/post_manager.py list --source=stratechery --format=urls

# Export as JSON
python3 scripts/post_manager.py list --since=2025-10-01 --format=json > recent_posts.json
```

## 📈 Status Management

### **Post Lifecycle**
1. **discovered** - Found by manual checker
2. **processing** - Currently being processed
3. **completed** - Successfully summarized
4. **failed** - Processing failed (can retry)
5. **skipped** - Manually marked as not interesting

### **Status Updates**
```bash
# Mark posts as skipped
python3 scripts/post_manager.py update post_id1 post_id2 --status=skipped

# Retry failed posts
python3 scripts/post_manager.py update failed_post_id --status=discovered

# Bulk skip uninteresting posts
python3 scripts/post_manager.py bulk --source=creatoreconomy --action=skip --limit=20
```

## 🛠️ File Transcription

### **Audio/Video Files**
```bash
# Transcribe local files
./scripts/transcribe_file_v2.sh /path/to/audio.mp3

# With specific language
./scripts/transcribe_file_v2.sh /path/to/video.mp4 en

# Direct processor usage
python3 processors/file_transcriber.py /path/to/audio.wav spanish
```

## 📊 Monitoring & Statistics

### **View Statistics**
```bash
# Overall stats
python3 scripts/post_manager.py stats

# Quick overview
./scripts/quick_process.sh stats
```

### **Logs**
- Session logs: `logs/post_checker_YYYYMMDD_HHMMSS.log`
- Error logs: Check individual processor logs
- Processing logs: Video summarizer output logs

## 🔧 Troubleshooting

### **No Posts Found**
1. Check `newsletter_podcast_links.md` has valid URLs
2. Verify internet connection
3. Check if newsletters require authentication

### **Processing Fails**
1. Verify API keys in `.env` file
2. Check if URL is accessible
3. Review error logs for specific issues

### **Permission Issues**
```bash
# Make scripts executable
chmod +x manual_check.sh
chmod +x scripts/*.sh
```

## 📚 Quick Command Reference

```bash
# Essential manual workflow
./manual_check.sh                                    # Check for new posts
./scripts/quick_process.sh check                     # Review discovered
./scripts/quick_process.sh process 3                 # Process 3 posts

# Source filtering
./scripts/quick_process.sh stratechery               # View Stratechery
./scripts/quick_process.sh lenny                     # View Lenny's
./scripts/quick_process.sh claude                    # View Creator Economy

# Advanced filtering
python3 scripts/post_manager.py list --since=2025-10-01 --source=stratechery
python3 scripts/post_manager.py bulk --status=discovered --action=process --limit=5

# Status management
python3 scripts/post_manager.py update post_id --status=skipped
python3 scripts/post_manager.py stats
```

## 🚀 Best Practices

1. **Regular Manual Checks**: Run `./manual_check.sh` regularly to discover new content
2. **Filter First**: Use source filtering to focus on preferred newsletters
3. **Batch Processing**: Use bulk operations for efficiency
4. **Status Management**: Mark uninteresting posts as skipped to keep data clean
5. **Monitor Stats**: Use statistics to track your reading patterns

The manual workflow gives you complete control over when and what content gets processed, without any automation running in the background.