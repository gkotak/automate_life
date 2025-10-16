# Semantic Search Setup Instructions

## Step 1: Deploy the Search Function to Supabase

1. Open your Supabase project at https://supabase.com/dashboard
2. Navigate to **SQL Editor** in the left sidebar
3. Click **New Query**
4. Copy and paste the contents of `supabase/search_articles_function.sql`
5. Click **Run** to create the function

The SQL function creates a `search_articles()` function that performs vector similarity search using pgvector.

## Step 2: Configure OpenAI API Key

1. Get your OpenAI API key from https://platform.openai.com/api-keys
2. Open `web-app/.env.local`
3. Replace `your_openai_api_key_here` with your actual API key:
   ```
   OPENAI_API_KEY=sk-...your-actual-key...
   ```

## Step 3: Test the Search

1. Start the web app:
   ```bash
   cd web-app
   npm run dev
   ```

2. Open http://localhost:3000 in your browser

3. Try semantic search:
   - Click the "🧠 Semantic (AI)" button to enable semantic search
   - Enter a query like "articles about AI safety" or "what did the author say about climate change?"
   - Click Search

## How It Works

### Semantic Search Flow:
1. User enters a natural language query
2. Frontend sends query to `/api/search` endpoint
3. API generates embedding using OpenAI's `text-embedding-3-small` model
4. Supabase `search_articles()` function compares query embedding with article embeddings
5. Returns top matching articles sorted by similarity score

### Keyword Search (default):
- Traditional text matching using PostgreSQL's `ILIKE`
- Searches across title, summary, transcript, and article text
- Useful for exact phrase matching

## Troubleshooting

**Error: "OpenAI API key not configured"**
- Make sure you've added `OPENAI_API_KEY` to `web-app/.env.local`
- Restart the Next.js dev server after adding the key

**Error: "Search failed"**
- Check that the SQL function was deployed successfully in Supabase
- Verify the function exists: Run `SELECT * FROM pg_proc WHERE proname = 'search_articles';` in SQL Editor

**No results returned**
- Ensure articles have embeddings generated (check `embedding` column is not NULL)
- Lower the similarity threshold in the API if needed (default is 0.5)
- Try processing articles again with embedding generation enabled

## Database Schema Requirements

The search function expects:
- `articles` table with an `embedding` column (type: `vector(1536)`)
- pgvector extension enabled
- Vector index on the embedding column for performance

These should already be set up from Step 1 (embedding generation).
