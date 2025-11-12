"""
Video Frame Extractor for Demo Videos

Extracts frames from demo/screen-share videos using ffmpeg scene detection
and perceptual hashing to identify unique, significant moments.
"""

import os
import logging
import subprocess
import tempfile
import shutil
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import hashlib
import asyncio

# Use [FRAMEEXTRACTOR] prefix to match ArticleProcessor logging style
logger = logging.getLogger('[FRAMEEXTRACTOR]')

try:
    import imagehash
    from PIL import Image
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    # This warning will appear during module import
    import sys
    print("⚠️ WARNING: imagehash library not available. Install with: pip install imagehash pillow", file=sys.stderr)


class FrameExtractor:
    """Extract significant frames from demo videos"""

    def __init__(self, min_interval_seconds: int = 10, similarity_threshold: int = 15):
        """
        Initialize FrameExtractor

        Args:
            min_interval_seconds: Minimum time between frames (default: 10s for demo videos)
            similarity_threshold: Perceptual hash difference threshold for uniqueness (default: 15)
                                Higher = allow more similar frames (0-64 range, not currently used)
        """
        self.min_interval_seconds = min_interval_seconds
        self.similarity_threshold = similarity_threshold
        self.temp_dir = None

    async def extract_frames(self, video_path: str) -> List[Dict[str, any]]:
        """
        Extract frames from video using scene detection with minimum interval enforcement.

        Uses ffmpeg's scene detection to identify visual changes, with a built-in filter
        to ensure frames are at least min_interval_seconds apart. Falls back to fixed
        interval extraction if scene detection finds no changes.

        Args:
            video_path: Path to video file

        Returns:
            List of frame dictionaries with:
                - path: File path to extracted frame
                - timestamp_seconds: Timestamp in video
                - time_formatted: Formatted timestamp (MM:SS or HH:MM:SS)
                - hash: Perceptual hash of the frame (for metadata only)
        """
        logger.info(f"🎬 Starting frame extraction from video: {video_path}")

        if not IMAGEHASH_AVAILABLE:
            logger.error("❌ imagehash library is required for frame extraction")
            return []

        # Create temporary directory for frames
        self.temp_dir = tempfile.mkdtemp(prefix="video_frames_")
        logger.info(f"📁 Created temp directory: {self.temp_dir}")

        try:
            # Use ffmpeg scene detection to find significant changes
            # The ffmpeg filter enforces minimum interval during extraction
            frames = await self._detect_scene_changes(video_path)
            logger.info(f"🎯 Detected {len(frames)} scene changes")

            if not frames:
                logger.warning("⚠️ No scene changes detected, falling back to interval extraction")
                frames = await self._extract_by_interval(video_path)

            # Compute perceptual hashes for metadata (not used for filtering)
            for frame in frames:
                try:
                    img = Image.open(frame["path"])
                    phash = imagehash.phash(img)
                    frame["hash"] = str(phash)
                except Exception as e:
                    logger.warning(f"⚠️ Could not compute hash for frame {frame['path']}: {e}")
                    frame["hash"] = None

            logger.info(f"✅ Extracted {len(frames)} unique frames")
            return frames

        except Exception as e:
            logger.error(f"❌ Frame extraction failed: {e}", exc_info=True)
            return []

    async def _detect_scene_changes(self, video_path: str) -> List[Dict[str, any]]:
        """
        Use ffmpeg scene detection to find significant frame changes

        Returns:
            List of frames with timestamps
        """
        logger.info("🔍 Running ffmpeg scene detection...")

        try:
            # Use ffmpeg select filter for scene detection only
            # scene=0.2 means detect scenes with 20% change (lower = more sensitive)
            # Minimum interval filtering is done in Python post-processing for reliability
            # showinfo writes frame info to stderr for timestamp extraction
            filter_complex = "select='gt(scene,0.2)',showinfo"

            output_pattern = os.path.join(self.temp_dir, "scene_%04d.jpg")

            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", filter_complex,
                "-vsync", "vfr",  # Variable frame rate to match scene changes
                "-q:v", "2",  # High quality JPEG
                output_pattern
            ]

            # Run ffmpeg in subprocess (async-friendly)
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()
            stderr_text = stderr.decode('utf-8', errors='ignore')

            if process.returncode != 0:
                logger.warning(f"⚠️ ffmpeg scene detection had warnings: {stderr_text[:500]}")

            # Get frame files
            frame_files = sorted(Path(self.temp_dir).glob("scene_*.jpg"))

            # Parse timestamps from stderr (showinfo output)
            timestamps = self._parse_showinfo_timestamps(stderr_text)

            logger.info(f"📊 Found {len(frame_files)} frames and {len(timestamps)} timestamps")

            # Build frame list
            frames = []
            for idx, frame_file in enumerate(frame_files):
                # Use metadata timestamp if available, otherwise estimate
                if idx < len(timestamps):
                    timestamp_seconds = timestamps[idx]
                else:
                    logger.warning(f"⚠️ No timestamp for frame {idx}, using estimate")
                    timestamp_seconds = idx * self.min_interval_seconds

                frames.append({
                    "path": str(frame_file),
                    "timestamp_seconds": timestamp_seconds,
                    "time_formatted": self._format_timestamp(timestamp_seconds),
                    "hash": None  # Will be computed later
                })

            # Post-process filter: Enforce minimum interval
            # The ffmpeg filter sometimes lets through frames that are too close
            filtered_frames = []
            last_timestamp = -self.min_interval_seconds  # Allow first frame

            for frame in frames:
                if frame["timestamp_seconds"] - last_timestamp >= self.min_interval_seconds:
                    filtered_frames.append(frame)
                    last_timestamp = frame["timestamp_seconds"]
                else:
                    logger.debug(f"🔍 Filtered out frame at {frame['time_formatted']} (too close to previous)")

            if len(filtered_frames) < len(frames):
                logger.info(f"🔍 Filtered {len(frames) - len(filtered_frames)} frames that were too close together")

            return filtered_frames

        except Exception as e:
            logger.error(f"❌ Scene detection failed: {e}", exc_info=True)
            return []

    async def _extract_by_interval(self, video_path: str) -> List[Dict[str, any]]:
        """
        Fallback: Extract frames at fixed intervals

        Returns:
            List of frames with timestamps
        """
        logger.info(f"⏱️ Extracting frames every {self.min_interval_seconds} seconds...")

        try:
            # Get video duration first
            duration = await self._get_video_duration(video_path)

            if not duration:
                logger.error("❌ Could not determine video duration")
                return []

            frames = []
            output_pattern = os.path.join(self.temp_dir, "frame_%04d.jpg")

            # Extract one frame every N seconds
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"fps=1/{self.min_interval_seconds}",
                "-q:v", "2",  # High quality JPEG
                output_pattern
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()

            # Collect extracted frames
            frame_files = sorted(Path(self.temp_dir).glob("frame_*.jpg"))

            for idx, frame_file in enumerate(frame_files):
                timestamp_seconds = idx * self.min_interval_seconds

                frames.append({
                    "path": str(frame_file),
                    "timestamp_seconds": timestamp_seconds,
                    "time_formatted": self._format_timestamp(timestamp_seconds),
                    "hash": None
                })

            return frames

        except Exception as e:
            logger.error(f"❌ Interval extraction failed: {e}", exc_info=True)
            return []


    async def _get_video_duration(self, video_path: str) -> Optional[float]:
        """Get video duration in seconds using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, _ = await process.communicate()
            duration_str = stdout.decode('utf-8').strip()

            return float(duration_str)

        except Exception as e:
            logger.error(f"❌ Could not get video duration: {e}")
            return None

    def _parse_showinfo_timestamps(self, stderr_text: str) -> List[float]:
        """Parse timestamps from ffmpeg showinfo filter output"""
        import re

        timestamps = []
        # Look for pts_time:X.XXX in showinfo output
        pattern = r'pts_time:([\d.]+)'

        for match in re.finditer(pattern, stderr_text):
            try:
                timestamps.append(float(match.group(1)))
            except ValueError:
                continue

        return timestamps

    def _parse_showinfo_timestamps(self, stderr_text: str) -> List[float]:
        """Parse timestamps from ffmpeg showinfo filter output in stderr"""
        import re

        timestamps = []
        # showinfo outputs lines like: [Parsed_showinfo_1 @ 0x...] n:0 pts:18304 pts_time:1.144 ...
        # Note: pts_time is followed by a space and value, not a colon
        pattern = r'\[Parsed_showinfo.*?\]\s+n:\s*\d+.*?pts_time:([\d.]+)'

        for match in re.finditer(pattern, stderr_text):
            try:
                timestamps.append(float(match.group(1)))
            except ValueError:
                continue

        logger.info(f"📋 Parsed {len(timestamps)} timestamps from showinfo")
        return timestamps

    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp as MM:SS or HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def cleanup(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"🧹 Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Could not clean up temp directory: {e}")
