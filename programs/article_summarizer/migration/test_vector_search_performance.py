#!/usr/bin/env python3
"""
Test script to verify vector search performance after index optimization

This script:
1. Connects to Supabase
2. Generates a test embedding
3. Runs vector search queries
4. Displays performance metrics

Usage:
    python3 test_vector_search_performance.py
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

# Load environment variables
root_env = Path(__file__).parent.parent.parent.parent / '.env.local'
webapp_env = Path(__file__).parent.parent / 'web-app' / '.env.local'

if root_env.exists():
    load_dotenv(root_env)
elif webapp_env.exists():
    load_dotenv(webapp_env)

def test_vector_search():
    """Test vector search performance"""

    # Initialize clients
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    openai_api_key = os.getenv('OPENAI_API_KEY')

    if not all([supabase_url, supabase_key, openai_api_key]):
        print("❌ Missing required environment variables")
        print("   Required: SUPABASE_URL, SUPABASE_ANON_KEY, OPENAI_API_KEY")
        return

    supabase = create_client(supabase_url, supabase_key)
    openai_client = OpenAI(api_key=openai_api_key)

    print("🔍 Vector Search Performance Test")
    print("=" * 60)

    # Check current article count
    try:
        count_result = supabase.table('articles').select('id', count='exact').execute()
        total_articles = count_result.count
        print(f"📊 Total articles in database: {total_articles}")

        # Check articles with embeddings
        embedding_result = supabase.table('articles').select('id', count='exact').not_.is_('embedding', 'null').execute()
        articles_with_embeddings = embedding_result.count
        print(f"📊 Articles with embeddings: {articles_with_embeddings}")
        print()
    except Exception as e:
        print(f"⚠️ Could not fetch article count: {e}")
        print()

    # Test queries
    test_queries = [
        "AI and machine learning",
        "product management strategies",
        "software engineering best practices",
    ]

    for query in test_queries:
        print(f"Query: '{query}'")
        print("-" * 60)

        try:
            # Generate embedding
            start_time = time.time()
            response = openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=query,
                dimensions=384
            )
            embedding = response.data[0].embedding
            embedding_time = time.time() - start_time
            print(f"  ⏱️  Embedding generation: {embedding_time:.3f}s")

            # Perform vector search
            start_time = time.time()
            search_result = supabase.rpc('search_articles', {
                'query_embedding': embedding,
                'match_threshold': 0.3,
                'match_count': 10
            }).execute()
            search_time = time.time() - start_time

            results = search_result.data or []
            print(f"  ⏱️  Vector search time: {search_time:.3f}s")
            print(f"  📊 Results found: {len(results)}")

            if results:
                print(f"  🎯 Top result: {results[0]['title'][:50]}...")
                print(f"     Similarity: {results[0]['similarity']:.3f}")

            print()

        except Exception as e:
            print(f"  ❌ Error: {e}")
            print()

    print("=" * 60)
    print("✅ Performance test complete!")
    print()
    print("💡 Optimization tips:")
    print("   - Search time < 100ms: Excellent performance")
    print("   - Search time 100-500ms: Good performance")
    print("   - Search time > 500ms: Consider increasing 'lists' parameter")
    print()
    print("   To adjust accuracy/speed tradeoff, run in Supabase SQL editor:")
    print("   - Faster: SET ivfflat.probes = 1;")
    print("   - Balanced: SET ivfflat.probes = 5; (default)")
    print("   - Accurate: SET ivfflat.probes = 10;")

if __name__ == "__main__":
    test_vector_search()
