# Video Summarizer Web App Migration Plan

## Project Goal

Convert the existing video summarizer program into a standalone web app with the following requirements:
- **Nothing runs locally** - fully cloud-hosted solution
- **Interactive HTML output** - users can delete articles, search, manage content
- **Scalable architecture** - handles growing content and user base

## Recommended Architecture: Local Processing + Web Frontend

### **Frontend: Next.js + Vercel + Supabase**
### **Backend: Local Python Processing + Supabase**

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Local Python      │    │   Next.js on        │    │    Supabase         │
│   Processing        │    │   Vercel            │    │                     │
│   ┌───────────────┐ │    │   ┌───────────────┐ │    │   ┌───────────────┐ │
│   │ • Video Proc  │ │    │   │ • Search UI   │ │    │   │ • Database    │ │
│   │ • AI Analysis │ │──────→ │ • CRUD Ops    │ │──────→ │ • Vector Search│ │
│   │ • Manual Proc │ │    │   │ • Auth        │ │    │   │ • Real-time   │ │
│   │ • Data Upload │ │    │   │ • Real-time   │ │    │   │ • Auth        │ │
│   └───────────────┘ │    │   └───────────────┘ │    │   └───────────────┘ │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Why This Local Processing + Web Frontend Architecture?

### **Advantages Over Cloud Processing**
- **No processing time limits** - Run AI analysis as long as needed locally
- **Lower costs** - No backend hosting fees (only Supabase + Vercel free tiers)
- **Familiar workflow** - Keep existing manual workflow and Python environment
- **Zero rewrite** - Minimal changes to existing processing logic

### **Component Responsibilities**

#### **Local Python Processing (Your Machine)**
- ✅ **Existing video processing** - Keep current Python scripts
- ✅ **AI analysis** - No time constraints, full Claude integration
- ✅ **Manual processing** - On-demand workflow only
- ✅ **Data upload** - Push results to Supabase after processing
- ✅ **Embedding generation** - Create vectors for semantic search

#### **Next.js Frontend (Vercel)**
- ✅ **Interactive search** - Fuzzy + semantic search interface
- ✅ **Article management** - Delete, edit, filter articles
- ✅ **Authentication** - User management via Supabase Auth
- ✅ **Real-time updates** - Live data refresh from Supabase
- ✅ **Mobile responsive** - Modern web interface

#### **Supabase Database**
- ✅ **PostgreSQL** - Structured data storage
- ✅ **Vector embeddings** - Semantic search
- ✅ **Real-time subscriptions** - Live UI updates
- ✅ **Authentication** - Built-in user management
- ✅ **Full-text search** - Advanced search capabilities

## Database Schema Design

### **Articles Table**
```sql
CREATE TABLE articles (
  id SERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  summary_html TEXT,
  content_text TEXT, -- Plain text for search
  video_id TEXT,
  platform TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  tags TEXT[],

  -- Search capabilities
  search_vector tsvector, -- PostgreSQL full-text search
  embedding vector(1536)  -- OpenAI embeddings for semantic search
);

-- Search indexes
CREATE INDEX articles_search_idx ON articles USING gin(search_vector);
CREATE INDEX articles_embedding_idx ON articles USING ivfflat(embedding vector_cosine_ops);
```

### **RSS Feeds Table**
```sql
CREATE TABLE rss_feeds (
  id SERIAL PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  name TEXT,
  last_checked TIMESTAMP,
  active BOOLEAN DEFAULT true
);
```

### **Processing Queue Table**
```sql
CREATE TABLE processing_queue (
  id SERIAL PRIMARY KEY,
  url TEXT NOT NULL,
  status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
  error_message TEXT,
  progress_percentage INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

## Advanced Search Implementation

### **Hybrid Search Strategy**
1. **Fuzzy/Full-text Search** - PostgreSQL tsvector
2. **Semantic Search** - Vector embeddings with cosine similarity
3. **Hybrid Results** - Merge and rank both approaches

### **Search API Implementation**
```typescript
// API route: /api/search
export async function POST(request: Request) {
  const { query, searchType = 'hybrid', filters } = await request.json();

  let results = [];

  switch (searchType) {
    case 'fuzzy':
      results = await fuzzySearch(query, filters);
      break;
    case 'semantic':
      results = await semanticSearch(query, filters);
      break;
    case 'hybrid':
      results = await hybridSearch(query, filters);
      break;
  }

  return Response.json({ results });
}
```

### **Semantic Search with Vector Embeddings**
```sql
-- Supabase function for vector similarity
CREATE OR REPLACE FUNCTION match_articles(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id int,
  title text,
  url text,
  summary_html text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    articles.id,
    articles.title,
    articles.url,
    articles.summary_html,
    1 - (articles.embedding <=> query_embedding) as similarity
  FROM articles
  WHERE 1 - (articles.embedding <=> query_embedding) > match_threshold
  ORDER BY articles.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

## Tech Stack Details

### **Frontend Stack**
```typescript
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Shadcn/ui components
- React Query (data fetching)
- Zustand (state management)
- Supabase client (real-time, auth)
```

### **Local Processing Stack**
```python
- Existing Python scripts (video_article_summarizer.py)
- YouTube Transcript API (keep existing)
- Claude API integration (keep existing)
- Supabase Python client (for data upload)
- SentenceTransformers (for embeddings)
- Manual execution (no scheduling)
```

### **Infrastructure**
```
- Supabase (PostgreSQL + Vector + Auth + Real-time)
- Vercel (Frontend hosting)
- Local machine (Python processing)
```

## Key Features Implementation

### **1. Interactive Article Management**
```typescript
// Delete button component
const DeleteButton = ({ articleId }: { articleId: number }) => {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await fetch(`/api/articles/${articleId}`, { method: 'DELETE' });
      // Trigger UI refresh via React Query
      queryClient.invalidateQueries(['articles']);
    } catch (error) {
      console.error('Delete failed:', error);
    }
    setIsDeleting(false);
  };

  return (
    <button
      onClick={handleDelete}
      disabled={isDeleting}
      className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded"
    >
      {isDeleting ? 'Deleting...' : 'Delete'}
    </button>
  );
};
```

### **2. Real-time Processing Updates**
```typescript
// Frontend - Submit for processing with real-time updates
const processArticle = async (url: string) => {
  // Submit to FastAPI backend
  const response = await fetch('https://api.yourdomain.com/process', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url })
  });

  const { jobId } = await response.json();

  // Listen for real-time updates from Supabase
  const channel = supabase
    .channel('processing-updates')
    .on('postgres_changes',
      {
        event: 'UPDATE',
        schema: 'public',
        table: 'processing_queue',
        filter: `id=eq.${jobId}`
      },
      (payload) => {
        setProcessingStatus(payload.new.status);
        setProgress(payload.new.progress_percentage);
      }
    )
    .subscribe();

  return () => supabase.removeChannel(channel);
};
```

### **3. Local Processing with Supabase Upload**
```python
# Enhanced existing Python script
from supabase import create_client
from sentence_transformers import SentenceTransformer

# Initialize Supabase client
supabase = create_client(supabase_url, supabase_key)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def save_article_to_supabase(article_data):
    """Upload processed article to Supabase with embeddings"""
    try:
        # Generate embedding for semantic search
        content_text = f"{article_data['title']} {article_data['content_text']}"
        embedding = embedding_model.encode(content_text).tolist()

        # Upload to Supabase
        result = supabase.table('articles').upsert({
            'title': article_data['title'],
            'url': article_data['url'],
            'summary_html': article_data['summary_html'],
            'content_text': article_data['content_text'],
            'embedding': embedding,
            'video_id': article_data.get('video_id'),
            'platform': article_data.get('platform'),
            'tags': article_data.get('tags', []),
            'created_at': datetime.now().isoformat()
        }).execute()

        print(f"✅ Uploaded to Supabase: {article_data['title']}")
        return result

    except Exception as e:
        print(f"❌ Error uploading to Supabase: {str(e)}")
        return None

# Add to existing processing workflow
def process_article(url):
    # ... existing processing logic ...

    # After generating summary, upload to Supabase
    save_article_to_supabase({
        'title': title,
        'url': url,
        'summary_html': summary_html,
        'content_text': extract_text_from_html(summary_html),
        'video_id': video_id,
        'platform': platform,
        'tags': extract_tags_from_content(summary_html)
    })
```

## Migration Strategy

### **Phase 1: Database Setup & Data Migration (Week 1)**
1. **Setup Supabase project** with authentication
2. **Create database schema** with vector extension
3. **Migrate existing HTML files** to database records
4. **Setup vector embeddings** for existing content

### **Phase 2: Frontend Development (Week 2-3)**
1. **Next.js project setup** with TypeScript and Tailwind
2. **Authentication flow** with Supabase Auth
3. **Article listing interface** with search and filters
4. **Interactive features** (delete, edit, bulk operations)
5. **Real-time updates** for processing status

### **Phase 3: Local Processing Enhancement (Week 4-5)**
1. **Add Supabase integration** to existing Python scripts
2. **Implement embedding generation** with SentenceTransformers
3. **Update manual scripts** to upload results after processing
4. **Add error handling** for upload failures
5. **Test end-to-end workflow** from local processing to web display

### **Phase 4: Advanced Features (Week 6-7)**
1. **Semantic search implementation** with embeddings
2. **Admin dashboard** for RSS feed management
3. **Analytics and insights** dashboard
4. **Performance optimization** and caching

### **Phase 5: Deployment & Manual Processing (Week 8)**
1. **Production deployment** on Vercel (frontend only)
2. **Local processing enhancement** with Supabase upload
3. **Monitoring and alerting** setup
4. **Documentation and user guides**

## Cost Estimation

### **Development Phase**
- **Supabase**: Free tier (sufficient for development)
- **Vercel**: Free tier (sufficient for development)
- **Local processing**: No additional costs

### **Production (Estimated Monthly Costs)**
- **Supabase**: $0-25 (depending on usage, likely free tier)
- **Vercel**: $0 (free tier sufficient for frontend)
- **OpenAI API**: $5-20 (for embeddings only)
- **Claude API**: $20-100 (existing usage, no change)

**Total: $25-145/month** (significantly lower than cloud processing)

## Comparison: Why Local Processing vs Cloud?

### **Considered: Fully Cloud-Hosted Processing**
**Limitations:**
- ❌ **Higher costs** - Backend hosting + queue infrastructure
- ❌ **Time limits** - Serverless functions have execution timeouts
- ❌ **Code migration** - Would require adapting existing Python logic
- ❌ **Complexity** - Managing multiple cloud services

### **Local Processing Benefits**
- ✅ **No processing time limits** - Run as long as needed
- ✅ **Zero additional hosting costs** - Use existing local machine
- ✅ **Keep existing code** - Minimal changes to current workflow
- ✅ **Familiar environment** - Same development setup
- ✅ **Best of both worlds** - Local processing + modern web interface

## Implementation Priority

### **MVP Features (Phase 1-2)**
- [ ] User authentication
- [ ] Article listing with basic search
- [ ] Delete/edit articles
- [ ] Submit new URLs for processing

### **Advanced Features (Phase 3-4)**
- [ ] Semantic search with vector embeddings
- [ ] Real-time processing updates
- [ ] Manual RSS feed processing
- [ ] Admin dashboard

### **Future Enhancements**
- [ ] User collaboration features
- [ ] API for external integrations
- [ ] Mobile app
- [ ] Advanced analytics

## Next Steps

1. **Setup Supabase project** and configure database schema
2. **Create Next.js frontend** with basic CRUD operations
3. **Setup FastAPI backend** with existing Python processing logic
4. **Implement real-time updates** between frontend and backend
5. **Deploy and test** the complete system

This migration plan provides a robust, scalable solution that maintains the power of the existing Python processing while adding modern web app capabilities and removing local dependencies.