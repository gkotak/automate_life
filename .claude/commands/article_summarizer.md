#article_summarizer

Execute the Python script directly to process the article URL:

```bash
python3 programs/article_summarizer/scripts/article_summarizer.py "$ARGUMENTS"
```

This script will automatically:
1. Extract metadata and video information from the article URL
2. Generate a structured summary (max 1000 words) with bullet points
3. Extract YouTube transcripts if available and create interactive video timestamps
4. Create an HTML page in programs/video_summarizer/output/article_summaries/ with a sanitized filename
5. Update programs/video_summarizer/output/article_summaries/index.html with the new article in reverse chronological order
6. Commit and push the changes to GitHub

The Python script handles all the processing internally using both deterministic operations and AI-powered analysis via Claude Code CLI. 