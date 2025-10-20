#!/usr/bin/env python3
"""
Fix Pocket Casts article sources

Updates existing Pocket Casts articles in the database to use the correct
podcast name as the source instead of generic "Pocket Casts".
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
root_env = Path(__file__).parent.parent.parent.parent / '.env.local'
webapp_env = Path(__file__).parent.parent / 'web-app' / '.env.local'

if root_env.exists():
    load_dotenv(root_env)
elif webapp_env.exists():
    load_dotenv(webapp_env)

def normalize_source_name(source: str) -> str:
    """
    Normalize source name by removing common suffixes like Newsletter, Podcast, Journal, etc.
    """
    # List of suffixes to remove (case-insensitive)
    suffixes_to_remove = [
        'Newsletter',
        'Podcast',
        'Journal',
        'Magazine',
        'Blog',
        'Daily',
        'Weekly',
        'Show',
        'Network',
        'Media',
        'News'
    ]

    # Build regex pattern
    pattern = r"\s*[-:,]?\s*(?:'s\s+)?(" + '|'.join(suffixes_to_remove) + r")\s*$"

    # Remove matched suffixes (case-insensitive)
    normalized = re.sub(pattern, '', source, flags=re.IGNORECASE)

    # Clean up any trailing whitespace, colons, or dashes
    normalized = normalized.rstrip(' :-,')

    return normalized.strip()

def extract_podcast_name_from_url(url: str) -> str:
    """Extract podcast name from Pocket Casts URL"""
    # URL format: https://pocketcasts.com/podcast/the-podcast-name/episode/episode-id
    podcast_match = re.search(r'pocketcasts\.com/podcast/([^/]+)', url)
    if podcast_match:
        podcast_slug = podcast_match.group(1)
        # Convert slug to readable name (replace hyphens with spaces, title case)
        podcast_name = podcast_slug.replace('-', ' ').title()
        return normalize_source_name(podcast_name)

    return "Pocket Casts"

def main():
    """Update all Pocket Casts articles with correct source names"""

    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")
        sys.exit(1)

    supabase: Client = create_client(supabase_url, supabase_key)

    try:
        # Fetch all Pocket Casts articles
        print("🔍 Fetching Pocket Casts articles...")
        response = supabase.table('articles').select('id, url, source').like('url', '%pocketcasts.com%').execute()

        articles = response.data
        print(f"📊 Found {len(articles)} Pocket Casts articles")

        if not articles:
            print("✅ No Pocket Casts articles to update")
            return

        # Update each article
        updated_count = 0
        for article in articles:
            article_id = article['id']
            url = article['url']
            current_source = article.get('source', 'Pocket Casts')

            # Extract podcast name from URL
            new_source = extract_podcast_name_from_url(url)

            # Skip if source is already correct
            if current_source == new_source:
                print(f"⏭️  Article {article_id}: Already correct ({new_source})")
                continue

            # Update the article
            print(f"🔄 Article {article_id}: '{current_source}' → '{new_source}'")
            supabase.table('articles').update({'source': new_source}).eq('id', article_id).execute()
            updated_count += 1

        print(f"\n✅ Updated {updated_count} articles")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
