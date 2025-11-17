#!/usr/bin/env python3
"""
Test face detection on existing extracted frames WITHOUT reprocessing the video.
This allows quick verification that DEBUG logs work and face detection is functioning.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set DEBUG logging level BEFORE importing FrameExtractor
os.environ['LOG_LEVEL'] = 'DEBUG'

# Configure logging at DEBUG level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from processors.frame_extractor import FrameExtractor

logger = logging.getLogger(__name__)


def test_existing_frames(frame_directory: str):
    """
    Test face detection on frames that were already extracted

    Args:
        frame_directory: Directory containing extracted .jpg frames
    """
    logger.info(f"🔍 Testing face detection on frames in: {frame_directory}")

    # Initialize extractor
    extractor = FrameExtractor()

    # Get all jpg files in the directory
    frame_files = sorted(Path(frame_directory).glob("*.jpg"))

    if not frame_files:
        logger.error(f"❌ No .jpg files found in {frame_directory}")
        return

    logger.info(f"📊 Found {len(frame_files)} frame files")

    # Test each frame
    screen_share_count = 0
    face_count = 0

    for frame_file in frame_files:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing frame: {frame_file.name}")
        logger.info('='*60)

        is_screen_share = extractor._is_screen_share_frame(str(frame_file))

        if is_screen_share:
            screen_share_count += 1
            logger.info(f"✅ Result: KEEP (screen share)")
        else:
            face_count += 1
            logger.info(f"🚫 Result: REJECT (face/webcam)")

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info('='*60)
    logger.info(f"Total frames tested: {len(frame_files)}")
    logger.info(f"Screen share frames (keep): {screen_share_count}")
    logger.info(f"Face/webcam frames (reject): {face_count}")
    logger.info(f"Filter rate: {face_count / len(frame_files) * 100:.1f}% rejected")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_face_detection_on_frames.py <path_to_frame_directory>")
        print("\nExample:")
        print("  python test_face_detection_on_frames.py /tmp/video_frames_xyz123/")
        sys.exit(1)

    frame_dir = sys.argv[1]

    if not os.path.exists(frame_dir):
        print(f"❌ Directory not found: {frame_dir}")
        sys.exit(1)

    test_existing_frames(frame_dir)
