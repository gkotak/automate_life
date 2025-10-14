#!/usr/bin/env python3
"""
Backfill Embeddings Script

Generates embeddings for existing articles in the database that don't have them.
Uses OpenAI's text-embedding-3-small model (384 dimensions).

Usage:
    python3 backfill_embeddings.py

Environment Variables Required:
    - SUPABASE_URL
    - SUPABASE_SERVICE_ROLE_KEY (needs update permissions)
    - OPENAI_API_KEY
"""

import os
import sys
import time
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from multiple possible locations
# Check root .env.local first, then web-app .env.local
root_env = Path(__file__).parent.parent.parent.parent / '.env.local'
webapp_env = Path(__file__).parent.parent / 'web-app' / '.env.local'

if root_env.exists():
    load_dotenv(root_env)
    print(f"📁 Loaded env from: {root_env}")
elif webapp_env.exists():
    load_dotenv(webapp_env)
    print(f"📁 Loaded env from: {webapp_env}")

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client
from openai import OpenAI


class EmbeddingBackfiller:
    def __init__(self):
        # Initialize Supabase
        supabase_url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        # Use service role key for update permissions
        supabase_key = (os.getenv('SUPABASE_SERVICE_ROLE_KEY') or
                       os.getenv('SUPABASE_ANON_KEY') or
                       os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY'))

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized")

        # Initialize OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set")

        self.openai_client = OpenAI(api_key=openai_api_key)
        print("✅ OpenAI client initialized")

    def fetch_articles_without_embeddings(self) -> List[dict]:
        """
        Fetch all articles that don't have embeddings

        Returns:
            List of article dictionaries
        """
        print("\n📊 Fetching articles without embeddings...")

        try:
            response = self.supabase.table('articles').select(
                'id, title, summary_text, key_insights, quotes, topics, embedding'
            ).is_('embedding', 'null').execute()

            articles = response.data if response.data else []
            print(f"   Found {len(articles)} articles without embeddings")
            return articles

        except Exception as e:
            print(f"❌ Error fetching articles: {e}")
            return []

    def build_embedding_text(self, article: dict) -> str:
        """
        Build comprehensive text for embedding generation

        Args:
            article: Article dictionary from database

        Returns:
            Combined text representing the article
        """
        parts = []

        # Add title (most important)
        if article.get('title'):
            parts.append(f"Title: {article['title']}")

        # Add summary
        if article.get('summary_text'):
            parts.append(f"Summary: {article['summary_text']}")

        # Add key insights
        key_insights = article.get('key_insights', [])
        if key_insights:
            insights_text = " ".join([
                insight.get('insight', '') if isinstance(insight, dict) else str(insight)
                for insight in key_insights
            ])
            parts.append(f"Key Insights: {insights_text}")

        # Add topics
        topics = article.get('topics', [])
        if topics:
            parts.append(f"Topics: {', '.join(topics)}")

        # Add quotes
        quotes = article.get('quotes', [])
        if quotes:
            quotes_text = " ".join([
                quote.get('quote', '') if isinstance(quote, dict) else str(quote)
                for quote in quotes
            ])
            parts.append(f"Notable Quotes: {quotes_text}")

        return "\n\n".join(parts)

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text using OpenAI API

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector (384 dimensions) or None if generation fails
        """
        try:
            # Truncate text to avoid token limits (8191 tokens max for text-embedding-3-small)
            # Approximately 4 characters per token, so limit to ~32000 characters
            if len(text) > 32000:
                text = text[:32000]
                print(f"      ⚠️  Truncated text to 32000 characters")

            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=384  # Use 384 dimensions for performance
            )

            return response.data[0].embedding

        except Exception as e:
            print(f"      ❌ Failed to generate embedding: {e}")
            return None

    def update_article_embedding(self, article_id: int, embedding: List[float]) -> bool:
        """
        Update article with generated embedding

        Args:
            article_id: ID of article to update
            embedding: Embedding vector to store

        Returns:
            True if update successful, False otherwise
        """
        try:
            self.supabase.table('articles').update({
                'embedding': embedding
            }).eq('id', article_id).execute()

            return True

        except Exception as e:
            print(f"      ❌ Failed to update article {article_id}: {e}")
            return False

    def process_articles(self, batch_size: int = 10, delay_between_batches: float = 1.0):
        """
        Process all articles without embeddings in batches

        Args:
            batch_size: Number of articles to process before taking a break
            delay_between_batches: Seconds to wait between batches (to avoid rate limits)
        """
        articles = self.fetch_articles_without_embeddings()

        if not articles:
            print("\n✅ All articles already have embeddings!")
            return

        total = len(articles)
        success_count = 0
        fail_count = 0

        print(f"\n🚀 Starting to process {total} articles...")
        print(f"   Batch size: {batch_size}")
        print(f"   Delay between batches: {delay_between_batches}s\n")

        for i, article in enumerate(articles, 1):
            article_id = article['id']
            title = article.get('title', 'Unknown')[:60]

            print(f"[{i}/{total}] Processing article {article_id}: {title}...")

            # Build text for embedding
            embedding_text = self.build_embedding_text(article)

            if not embedding_text.strip():
                print(f"      ⚠️  Skipping - no text content available")
                fail_count += 1
                continue

            # Generate embedding
            embedding = self.generate_embedding(embedding_text)

            if not embedding:
                print(f"      ❌ Skipping - embedding generation failed")
                fail_count += 1
                continue

            # Update database
            if self.update_article_embedding(article_id, embedding):
                print(f"      ✅ Embedding saved ({len(embedding)} dimensions)")
                success_count += 1
            else:
                fail_count += 1

            # Delay between batches to avoid rate limits
            if i % batch_size == 0 and i < total:
                print(f"\n   ⏸️  Batch complete. Waiting {delay_between_batches}s before next batch...\n")
                time.sleep(delay_between_batches)

        # Final summary
        print(f"\n{'='*60}")
        print(f"✅ Backfill complete!")
        print(f"   Total articles processed: {total}")
        print(f"   Successful: {success_count}")
        print(f"   Failed: {fail_count}")
        print(f"{'='*60}\n")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("Embedding Backfill Script")
    print("="*60 + "\n")

    try:
        backfiller = EmbeddingBackfiller()
        backfiller.process_articles(batch_size=10, delay_between_batches=1.0)

    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nRequired environment variables:")
        print("  - SUPABASE_URL")
        print("  - SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY)")
        print("  - OPENAI_API_KEY")
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Exiting...")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
