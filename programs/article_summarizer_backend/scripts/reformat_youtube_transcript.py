#!/usr/bin/env python3
"""
Reformat YouTube transcript for an article by re-fetching and applying 30-second grouping

This script:
1. Fetches article from Supabase
2. Re-fetches the YouTube transcript using the video_id
3. Applies 30-second grouping for better readability
4. Updates transcript_text in database

Usage:
    python3 scripts/reformat_youtube_transcript.py <article_id>
    python3 scripts/reformat_youtube_transcript.py 338
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from supabase import create_client
from dotenv import load_dotenv
from processors.transcript_processor import TranscriptProcessor
from pathlib import Path
import requests

load_dotenv()


def get_supabase_client():
    """Get Supabase client"""
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def format_transcript_for_display(transcript_data: dict) -> str:
    """
    Format YouTube transcript with 30-second grouping for better readability
    """
    if not transcript_data or not transcript_data.get('success'):
        return ""

    transcript = transcript_data.get('transcript', [])
    is_youtube = transcript_data.get('type') in ['manual', 'auto_generated']

    formatted_sections = []

    if is_youtube:
        # YouTube transcripts: Group into minimum 30-second chunks
        current_group_start = None
        current_group_text = []

        for entry in transcript:
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            if not text:
                continue

            # Start new group if this is the first entry
            if current_group_start is None:
                current_group_start = start_time
                current_group_text = [text]
            # Check if we should start a new group (30 seconds elapsed)
            elif start_time - current_group_start >= 30:
                # Save the current group
                add_formatted_section(formatted_sections, current_group_start, ' '.join(current_group_text))
                # Start new group
                current_group_start = start_time
                current_group_text = [text]
            else:
                # Add to current group
                current_group_text.append(text)

        # Add the final group
        if current_group_start is not None and current_group_text:
            add_formatted_section(formatted_sections, current_group_start, ' '.join(current_group_text))
    else:
        # Non-YouTube: Use natural boundaries (no regrouping)
        for entry in transcript:
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            if not text:
                continue

            add_formatted_section(formatted_sections, start_time, text)

    return "\n\n".join(formatted_sections)


def add_formatted_section(sections: list, start_time: float, text: str) -> None:
    """Helper to format and add a timestamped section"""
    # Format timestamp as [MM:SS] or [H:MM:SS]
    hours = int(start_time // 3600)
    minutes = int((start_time % 3600) // 60)
    seconds = int(start_time % 60)

    if hours > 0:
        timestamp = f"[{hours}:{minutes:02d}:{seconds:02d}]"
    else:
        timestamp = f"[{minutes}:{seconds:02d}]"

    sections.append(f"{timestamp} {text}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/reformat_youtube_transcript.py <article_id> [--yes]")
        sys.exit(1)

    article_id = int(sys.argv[1])
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    print(f"📄 Reformatting YouTube transcript for article {article_id}...")

    # Get Supabase client
    supabase = get_supabase_client()

    # Fetch article
    print(f"🔍 Fetching article {article_id}...")
    response = supabase.table('articles').select('id, title, video_id, platform').eq('id', article_id).single().execute()

    if not response.data:
        print(f"❌ Article {article_id} not found")
        sys.exit(1)

    article = response.data
    print(f"✅ Found: {article['title']}")

    # Check if it's a YouTube video
    if not article.get('video_id') or article.get('platform') != 'youtube':
        print(f"⚠️ Article is not a YouTube video (platform: {article.get('platform')})")
        sys.exit(0)

    video_id = article['video_id']
    print(f"📺 Video ID: {video_id}")

    # Re-fetch YouTube transcript
    print(f"🔄 Re-fetching YouTube transcript...")
    base_dir = Path(__file__).parent.parent
    session = requests.Session()
    processor = TranscriptProcessor(base_dir, session)

    transcript_data = processor.get_youtube_transcript(video_id)

    if not transcript_data or not transcript_data.get('success'):
        print(f"❌ Failed to fetch transcript: {transcript_data.get('error', 'Unknown error')}")
        sys.exit(1)

    print(f"✅ Fetched transcript: {transcript_data.get('total_entries')} entries, type: {transcript_data.get('type')}")

    # Reformat with 30-second grouping
    print(f"📝 Reformatting with 30-second grouping...")
    new_transcript = format_transcript_for_display(transcript_data)

    # Show sample of new format
    new_preview = new_transcript[:500]
    print(f"\n✨ New format (first 500 chars):")
    print(f"{new_preview}...\n")

    # Confirm before updating
    if not auto_confirm:
        response = input(f"Update article {article_id} with reformatted transcript? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            sys.exit(0)
    else:
        print("✅ Auto-confirming update (--yes flag provided)")

    # Update database
    print(f"💾 Updating database...")
    supabase.table('articles').update({
        'transcript_text': new_transcript
    }).eq('id', article_id).execute()

    print(f"✅ Successfully reformatted transcript for article {article_id}")
    print(f"   View at: http://localhost:3000/article/{article_id}")


if __name__ == "__main__":
    main()
