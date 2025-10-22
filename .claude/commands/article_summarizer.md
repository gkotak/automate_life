#article_summarizer

Process an article URL and save to Supabase database:

```bash
python3 programs/article_summarizer_backend/app/services/article_processor.py "$ARGUMENTS"
```

This script will automatically:
1. Extract metadata and detect content type (video/audio/text)
2. Handle authentication for paywalled content (Substack, Medium, etc.)
3. Extract YouTube transcripts or transcribe audio using Whisper API
4. Generate AI-powered summary with key insights and quotes using Claude
5. Save structured data to Supabase database (articles, transcripts, insights, quotes, key_moments)
6. Generate embeddings for semantic search

View the processed article at: http://localhost:3000/article/{id}

The script uses the article_summarizer_backend processing pipeline with database-first storage.
