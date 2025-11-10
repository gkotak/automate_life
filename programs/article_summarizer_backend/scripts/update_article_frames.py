#!/usr/bin/env python3
"""
Update article with video frames from storage
"""

import os
import sys
import re
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client
from dotenv import load_dotenv

load_dotenv('.env.local')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Configuration
source_article_id = 999  # Where the test frames are stored
article_id = 264  # Target article to update

# Get frames dynamically from storage
from core.storage_manager import StorageManager
storage_manager = StorageManager()

print(f"🔍 Scanning storage for frames in article_{source_article_id}...")

# List all files in the source article folder
try:
    files = storage_manager.supabase.storage.from_("video-frames").list(f"article_{source_article_id}")

    # Extract frame timestamps from filenames (frame_123.jpg -> 123)
    test_frames = []
    frame_pattern = re.compile(r'frame_(\d+)\.jpg')

    for file in files:
        match = frame_pattern.match(file['name'])
        if match:
            timestamp_seconds = int(match.group(1))

            # Format timestamp as MM:SS or HH:MM:SS
            hours = timestamp_seconds // 3600
            minutes = (timestamp_seconds % 3600) // 60
            secs = timestamp_seconds % 60

            if hours > 0:
                time_formatted = f"{hours:02d}:{minutes:02d}:{secs:02d}"
            else:
                time_formatted = f"{minutes:02d}:{secs:02d}"

            test_frames.append({
                "timestamp_seconds": timestamp_seconds,
                "time_formatted": time_formatted
            })

    # Sort by timestamp
    test_frames.sort(key=lambda x: x['timestamp_seconds'])

    print(f"📊 Found {len(test_frames)} frames in storage")
    for frame in test_frames:
        print(f"  - {frame['time_formatted']} ({frame['timestamp_seconds']}s)")

except Exception as e:
    print(f"❌ Failed to list frames: {e}")
    sys.exit(1)

# Build video_frames array for article 264
video_frames = []
for frame in test_frames:
    video_frames.append({
        "url": f"https://gmwqeqlbfhxffxpsjokf.supabase.co/storage/v1/object/public/video-frames/article_{article_id}/frame_{int(frame['timestamp_seconds'])}.jpg",
        "storage_path": f"article_{article_id}/frame_{int(frame['timestamp_seconds'])}.jpg",
        "timestamp_seconds": frame["timestamp_seconds"],
        "time_formatted": frame["time_formatted"]
    })

print(f"\n📤 Updating article {article_id} with {len(video_frames)} frames...")

# Copy frames from source to destination in storage
print(f"\n📋 Copying frames from article_{source_article_id} to article_{article_id}...")

for frame in test_frames:
    source_path = f"article_{source_article_id}/frame_{int(frame['timestamp_seconds'])}.jpg"
    dest_path = f"article_{article_id}/frame_{int(frame['timestamp_seconds'])}.jpg"

    try:
        # Download from source
        source_data = storage_manager.supabase.storage.from_("video-frames").download(source_path)

        # Upload to destination
        storage_manager.supabase.storage.from_("video-frames").upload(
            path=dest_path,
            file=source_data,
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        print(f"  ✅ Copied frame at {frame['time_formatted']}")
    except Exception as e:
        print(f"  ❌ Failed to copy frame at {frame['time_formatted']}: {e}")

# Update article in database
result = supabase.table('articles').update({
    'video_frames': video_frames
}).eq('id', article_id).execute()

print(f"\n✅ Updated article {article_id} with {len(video_frames)} frames!")
print(f"\nView at: http://localhost:3000/article/{article_id}")
