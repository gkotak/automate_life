#!/usr/bin/env python3
"""
Test script for video frame extraction and upload to Supabase
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.frame_extractor import FrameExtractor
from core.storage_manager import StorageManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_frame_extraction(video_path: str, article_id: int = 999):
    """
    Test frame extraction and upload for a video file

    Args:
        video_path: Path to video file
        article_id: Article ID to use for storage (default: 999 for testing)
    """
    logger.info(f"🎬 Testing frame extraction for video: {video_path}")

    # Check if video exists
    if not os.path.exists(video_path):
        logger.error(f"❌ Video file not found: {video_path}")
        return

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    logger.info(f"📊 Video file size: {file_size_mb:.1f}MB")

    # Step 1: Extract frames
    logger.info("=" * 60)
    logger.info("STEP 1: Extracting frames from video")
    logger.info("=" * 60)

    extractor = FrameExtractor(min_interval_seconds=30)
    frames = await extractor.extract_frames(video_path)

    logger.info(f"✅ Extracted {len(frames)} frames")

    if not frames:
        logger.warning("⚠️ No frames extracted, stopping test")
        extractor.cleanup()
        return

    # Step 2: Upload frames to Supabase
    logger.info("=" * 60)
    logger.info("STEP 2: Uploading frames to Supabase storage")
    logger.info("=" * 60)

    storage_manager = StorageManager()
    uploaded_frames = []

    for i, frame in enumerate(frames):
        logger.info(f"📤 Uploading frame {i+1}/{len(frames)}: {frame['time_formatted']}")

        success, storage_path, public_url = storage_manager.upload_frame(
            frame["path"],
            article_id,
            frame["timestamp_seconds"]
        )

        if success:
            logger.info(f"   ✅ Uploaded: {public_url}")
            uploaded_frames.append({
                "url": public_url,
                "storage_path": storage_path,
                "timestamp_seconds": frame["timestamp_seconds"],
                "time_formatted": frame["time_formatted"],
                "perceptual_hash": frame.get("hash")
            })
        else:
            logger.error(f"   ❌ Failed to upload frame at {frame['time_formatted']}")

    # Clean up temporary frames
    extractor.cleanup()

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total frames extracted: {len(frames)}")
    logger.info(f"Successfully uploaded: {len(uploaded_frames)}")
    logger.info(f"Failed uploads: {len(frames) - len(uploaded_frames)}")

    if uploaded_frames:
        logger.info("\n📋 Uploaded frames:")
        for frame in uploaded_frames:
            logger.info(f"  - {frame['time_formatted']}: {frame['url']}")

    return uploaded_frames


if __name__ == "__main__":
    # Check if video path is provided
    if len(sys.argv) < 2:
        # Try to use the preserved video file
        preserved_video = "/var/folders/77/k9j4ylrs6lsdn9rj8bz44wh00000gn/T/demo_video_ad9nysxe/video_20872ffb506f41a4b16a878c95f02ff5.mp4"

        if os.path.exists(preserved_video):
            logger.info(f"✅ Using preserved video file: {preserved_video}")
            video_path = preserved_video
        else:
            print("Usage: python test_frame_extraction.py <path_to_video>")
            print(f"\nPreserved video not found at: {preserved_video}")
            sys.exit(1)
    else:
        video_path = sys.argv[1]

    # Run the test
    asyncio.run(test_frame_extraction(video_path))
