#!/usr/bin/env python3
"""
Fix specific article that has incomplete content
"""

import os
import sys
from pathlib import Path

# Add the scripts directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    from supabase import create_client, Client
    from sentence_transformers import SentenceTransformer
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    sys.exit(1)

# Import the updated extractor
from migrate_to_supabase import ContentExtractor

# Supabase configuration
SUPABASE_URL = "https://gmwqeqlbfhxffxpsjokf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdtd3FlcWxiZmh4ZmZ4cHNqb2tmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTk0MDgxNDIsImV4cCI6MjA3NDk4NDE0Mn0.U_iJr_72FdbrkMj83eevJ_Hzi3fXQDoVrCsCnZj8fGc"

# File paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "article_summaries"

def fix_article():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    extractor = ContentExtractor()

    # The problematic file
    filename = "Why_AI_evals_are_the_hottest_new_skill_for_product_builders_Hamel_Husain_&_Shreya_Shankar_(creators_.html"
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return

    print(f"🔄 Re-processing: {filename}")

    # Read HTML content
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Extract content using the updated extractor
    article_data = extractor.extract_from_html(html_content, filename)

    print(f"✅ Extracted content:")
    print(f"   Title: {article_data['title'][:60]}...")
    print(f"   Summary HTML length: {len(article_data['summary_html'])}")
    print(f"   Summary Text length: {len(article_data['summary_text'])}")

    # Generate embedding
    combined_text = f"{article_data['title']} {article_data['summary_text'] or ''}"
    embedding = extractor.generate_embedding(combined_text)
    article_data['embedding'] = embedding

    # Update the article in Supabase (using URL as unique key)
    try:
        result = supabase.table('articles').update(article_data).eq('url', article_data['url']).execute()

        if result.data:
            print(f"✅ Successfully updated article in database")
            print(f"   Updated article ID: {result.data[0]['id']}")
        else:
            print(f"❌ No rows updated - article not found with URL: {article_data['url']}")

    except Exception as e:
        print(f"❌ Error updating article: {str(e)}")

if __name__ == "__main__":
    fix_article()