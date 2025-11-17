#!/usr/bin/env python3
"""
Quick test: Extract a few frames and test face detection
"""

import os
import sys
import logging
import asyncio
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set INFO logging level
os.environ['LOG_LEVEL'] = 'INFO'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from processors.frame_extractor import FrameExtractor

logger = logging.getLogger(__name__)


async def quick_test(video_path: str, num_frames: int = 5):
    """
    Extract just a few frames and test face detection on them

    Args:
        video_path: Path to video file
        num_frames: Number of frames to test (default: 5)
    """
    logger.info(f"🔍 Quick frame test on: {video_path}")
    logger.info(f"Will extract and test {num_frames} frames")

    # Initialize extractor with shorter interval for quick testing
    extractor = FrameExtractor(min_interval_seconds=30)

    try:
        # Extract frames
        frames = await extractor.extract_frames(video_path)

        logger.info(f"\n{'='*60}")
        logger.info(f"RESULTS")
        logger.info('='*60)
        logger.info(f"Total frames extracted: {len(frames)}")

        if frames:
            logger.info(f"\nFirst few frames:")
            for i, frame in enumerate(frames[:num_frames]):
                logger.info(f"  {i+1}. {frame['time_formatted']} - {frame['path']}")

    finally:
        # Cleanup
        extractor.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_frame_test.py <video_path> [num_frames]")
        print("\nExample:")
        print("  python quick_frame_test.py /path/to/video.mp4 5")
        sys.exit(1)

    video_path = sys.argv[1]
    num_frames = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        sys.exit(1)

    asyncio.run(quick_test(video_path, num_frames))
