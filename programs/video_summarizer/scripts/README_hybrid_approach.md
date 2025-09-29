# Hybrid Article Summarizer

This is a **deterministic hybrid approach** that combines Python for reliable operations with Claude Code for AI-powered analysis.

## Architecture

### 🐍 Python Script (`video_article_summarizer.py`)
**Handles deterministic operations:**
- File system operations
- HTML template generation
- Git commit/push operations
- URL parsing and basic metadata extraction
- Index.html management

### 🤖 Claude Code API
**Handles AI-powered tasks:**
- Content analysis and summarization
- Key insight extraction
- Video timestamp identification
- Content quality assessment

## Advantages Over Pure Slash Commands

| Aspect | Slash Command | Hybrid Approach |
|--------|---------------|-----------------|
| **Consistency** | Variable output | Deterministic structure |
| **Performance** | Full AI interpretation | Only AI where needed |
| **Debugging** | Hard to troubleshoot | Standard Python debugging |
| **Version Control** | Logic in .md files | Proper code versioning |
| **Error Handling** | Basic | Comprehensive try/catch |
| **Customization** | English modifications | Code-level control |

## Usage

### Option 1: Direct Python
```bash
python3 scripts/video_article_summarizer.py "https://example.com/article"
```

### Option 2: Shell Wrapper (Recommended)
```bash
./scripts/summarize_article.sh "https://example.com/article"
```

### Option 3: As Replacement for Slash Command
Update your `.claude/commands/video_article_summarizer.md`:
```markdown
#video_article_summarizer

Run the hybrid Python script:
```bash
./scripts/summarize_article.sh $ARGUMENTS
```
```

## Installation

1. **Install Python dependencies:**
   ```bash
   pip3 install -r scripts/requirements.txt
   ```

2. **Ensure Claude Code CLI is available:**
   ```bash
   claude --version
   ```

3. **Make script executable:**
   ```bash
   chmod +x scripts/summarize_article.sh
   ```

## Workflow Details

```
URL Input
    ↓
[PYTHON] Extract basic metadata (title, domain, video indicators)
    ↓
[CLAUDE API] Analyze content & generate insights
    ↓
[PYTHON] Generate HTML using template
    ↓
[PYTHON] Update index.html (deterministic insertion)
    ↓
[PYTHON] Git commit & push
    ↓
Result: Consistent HTML file + updated index
```

## Benefits

✅ **Predictable Output**: Same input → same file structure
✅ **Faster Execution**: Only AI calls where needed
✅ **Better Error Handling**: Python exception handling
✅ **Easier Debugging**: Standard Python tools
✅ **Version Control**: Track code changes properly
✅ **Extensible**: Easy to add new features

## File Structure

```
scripts/
├── video_article_summarizer.py    # Main Python script
├── summarize_article.sh           # Shell wrapper
├── requirements.txt               # Python dependencies
└── README_hybrid_approach.md      # This documentation
```

## Comparison: Before vs After

### Before (Pure Slash Command)
```
/video_article_summarizer https://example.com
↓
Claude interprets entire workflow in natural language
↓
Variable execution path and output
```

### After (Hybrid Approach)
```
./scripts/summarize_article.sh https://example.com
↓
Python handles structure, Claude handles content analysis
↓
Consistent, debuggable, fast execution
```

This hybrid approach gives you the best of both worlds: AI power where you need it, and deterministic control everywhere else.