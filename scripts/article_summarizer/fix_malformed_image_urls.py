#!/usr/bin/env python3
"""
Fix malformed image URLs in the articles table.

This script fixes two issues:
1. Removes CDN transformation prefixes like "fl_progressive:steep/"
2. Decodes URL-encoded URLs (https%3A%2F%2F -> https://)

Example malformed URL:
  fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F...

Becomes:
  https://substack-post-media.s3.amazonaws.com/public/images/...
"""

import os
import sys
from urllib.parse import unquote
from supabase import create_client, Client

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)


def clean_image_url(url: str) -> str:
    """Clean up a malformed image URL"""
    if not url or not isinstance(url, str):
        return url

    original_url = url

    # Remove CDN transformation prefixes (e.g., "fl_progressive:steep/")
    if '/' in url and not url.startswith(('http://', 'https://', '//', '/')):
        parts = url.split('/', 1)
        if len(parts) == 2 and (':' in parts[0] or parts[1].startswith('http')):
            url = parts[1]

    # Decode URL-encoded URLs (e.g., https%3A%2F%2F -> https://)
    if '%' in url and not url.startswith(('http://', 'https://', '//')):
        url = unquote(url)

    # Verify we got a valid HTTP(S) URL
    if url != original_url and url.startswith(('http://', 'https://')):
        return url
    elif url == original_url:
        # No changes needed
        return url
    else:
        # Something went wrong, return original
        print(f"  ⚠️  Warning: Could not clean URL: {original_url}")
        return original_url


def main():
    # Load environment variables
    from dotenv import load_dotenv

    # Try to load from backend .env.local first, then fall back to root .env.local
    backend_env = os.path.join(project_root, 'programs/article_summarizer_backend/.env.local')
    root_env = os.path.join(project_root, '.env.local')

    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    elif os.path.exists(root_env):
        load_dotenv(root_env)

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env.local")
        sys.exit(1)

    print("🔧 Connecting to Supabase...")
    supabase: Client = create_client(supabase_url, supabase_key)

    # Fetch all articles with images
    print("📥 Fetching articles with images...")
    response = supabase.table('articles') \
        .select('id, title, images') \
        .not_.is_('images', 'null') \
        .execute()

    articles = response.data
    print(f"   Found {len(articles)} articles with images")

    fixed_count = 0
    skipped_count = 0

    for article in articles:
        article_id = article['id']
        title = article['title']
        images = article.get('images', [])

        if not images or not isinstance(images, list):
            skipped_count += 1
            continue

        # Check if any images need fixing
        needs_fixing = any(
            img and isinstance(img, str) and (
                (not img.startswith(('http://', 'https://', '//', '/'))) or
                ('%' in img and not img.startswith(('http://', 'https://', '//')))
            )
            for img in images
        )

        if not needs_fixing:
            skipped_count += 1
            continue

        # Clean all image URLs
        cleaned_images = [clean_image_url(img) for img in images]

        # Check if anything changed
        if cleaned_images == images:
            skipped_count += 1
            continue

        # Update the article
        print(f"\n📝 Fixing article {article_id}: {title[:60]}...")
        print(f"   Before: {len([img for img in images if not img.startswith('http')])} malformed URLs")
        print(f"   After:  {len([img for img in cleaned_images if not img.startswith('http')])} malformed URLs")

        supabase.table('articles') \
            .update({'images': cleaned_images}) \
            .eq('id', article_id) \
            .execute()

        fixed_count += 1

    print(f"\n✅ Migration complete!")
    print(f"   Fixed: {fixed_count} articles")
    print(f"   Skipped: {skipped_count} articles (no changes needed)")


if __name__ == '__main__':
    main()
