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
import numpy as np

# Use [FRAMEEXTRACTOR] prefix to match ArticleProcessor logging style
logger = logging.getLogger('[FRAMEEXTRACTOR]')
# Set logger to propagate to root logger (will inherit handlers and level from root)
logger.propagate = True
# Also set level from environment for standalone usage
import os as _os
_log_level = _os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, _log_level, logging.INFO))

try:
    import imagehash
    from PIL import Image
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    # This warning will appear during module import
    import sys
    print("⚠️ WARNING: imagehash library not available. Install with: pip install imagehash pillow", file=sys.stderr)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    import sys
    print("⚠️ WARNING: opencv-python library not available. Install with: pip install opencv-python", file=sys.stderr)


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
        self.face_cascade = None

        # Initialize detection cascades if OpenCV is available
        self.upperbody_cascade = None
        if CV2_AVAILABLE:
            try:
                # Face detection
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                if self.face_cascade.empty():
                    logger.warning("⚠️ Face detection cascade failed to load")
                    self.face_cascade = None
                else:
                    logger.info("✅ Face detection cascade loaded successfully")

                # Upper body detection (detects head + shoulders + torso)
                upperbody_path = cv2.data.haarcascades + 'haarcascade_upperbody.xml'
                self.upperbody_cascade = cv2.CascadeClassifier(upperbody_path)
                if self.upperbody_cascade.empty():
                    logger.warning("⚠️ Upper body detection cascade failed to load")
                    self.upperbody_cascade = None
                else:
                    logger.info("✅ Upper body detection cascade loaded successfully")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize detection cascades: {e}")
                self.face_cascade = None
                self.upperbody_cascade = None

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
        logger.debug(f"extract_frames called - CV2_AVAILABLE={CV2_AVAILABLE}, face_cascade={self.face_cascade is not None}")
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

            # Filter frames to only include screen share content
            screen_share_frames = []
            filtered_count = 0
            for idx, frame in enumerate(frames, 1):
                logger.info(f"📋 Analyzing frame {idx}/{len(frames)} at {frame['time_formatted']}")
                is_screen_share = self._is_screen_share_frame(frame["path"])
                if is_screen_share:
                    screen_share_frames.append(frame)
                else:
                    filtered_count += 1
                    logger.info(f"🚫 Filtered out frame {idx}/{len(frames)} at {frame['time_formatted']}")

            if filtered_count > 0:
                logger.info(f"📊 Filtered {filtered_count} frames showing faces/webcam feeds")

            # Compute perceptual hashes for metadata (not used for filtering)
            for frame in screen_share_frames:
                try:
                    img = Image.open(frame["path"])
                    phash = imagehash.phash(img)
                    frame["hash"] = str(phash)
                except Exception as e:
                    logger.warning(f"⚠️ Could not compute hash for frame {frame['path']}: {e}")
                    frame["hash"] = None

            logger.info(f"✅ Extracted {len(screen_share_frames)} screen share frames")
            return screen_share_frames

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

    def _is_screen_share_frame(self, frame_path: str) -> bool:
        """
        Determine if a frame contains screen share content vs just a person's face.

        Uses two detection methods:
        1. Face detection - if a large face is detected, it's likely a webcam feed
        2. Edge density analysis - screen shares have more sharp edges (UI, text, slides)

        Args:
            frame_path: Path to the frame image file

        Returns:
            True if frame appears to be screen share content, False if it's just a face
        """
        if not CV2_AVAILABLE or self.face_cascade is None:
            # If OpenCV not available, default to keeping the frame
            logger.debug(f"⚠️ OpenCV not available, keeping frame by default")
            return True

        try:
            # Read the image
            img = cv2.imread(frame_path)
            if img is None:
                logger.warning(f"⚠️ Could not read frame {frame_path}")
                return True  # Keep frame by default if we can't read it

            # Convert to grayscale for analysis
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 2. Edge density analysis (do this FIRST - it's more reliable)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.count_nonzero(edges) / edges.size

            # 1. Upper body detection - detects head, shoulders, torso (better for webcam detection)
            if self.upperbody_cascade is not None:
                upperbodies = self.upperbody_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3)

                if len(upperbodies) > 0:
                    # Calculate upper body area ratio
                    upperbody_area = sum(w * h for (x, y, w, h) in upperbodies)
                    frame_area = img.shape[0] * img.shape[1]
                    upperbody_ratio = upperbody_area / frame_area

                    # Upper body > 15% of frame = likely webcam/talking head
                    if upperbody_ratio > 0.15:
                        logger.info(f"   🚫 REJECT: Upper body {upperbody_ratio:.1%}, edges {edge_density:.1%} - webcam/talking head")
                        return False
                    else:
                        logger.info(f"   👤 Upper body {upperbody_ratio:.1%} detected but below threshold")

            # 2. Face detection as fallback
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=2)

            if len(faces) > 0:
                # Calculate face area ratio
                face_area = sum(w * h for (x, y, w, h) in faces)
                frame_area = img.shape[0] * img.shape[1]
                face_ratio = face_area / frame_area

                # Get largest face for position analysis
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest_face

                # Calculate face position (centered faces are more likely webcam)
                face_center_x = x + w / 2
                face_center_y = y + h / 2
                frame_center_x = img.shape[1] / 2
                frame_center_y = img.shape[0] / 2

                # Distance from center (normalized 0-1)
                center_dist_x = abs(face_center_x - frame_center_x) / frame_center_x
                center_dist_y = abs(face_center_y - frame_center_y) / frame_center_y

                # Talking head indicators (fallback when upper body not detected):
                # 1. Face area > 20% - definitely talking head
                # 2. Face detected (any size) AND low edges (<11%) - likely talking head
                # 3. Face > 5% AND centered AND low edges - likely talking head (redundant but kept for clarity)

                is_talking_head = False
                reason = ""

                if face_ratio > 0.20:
                    is_talking_head = True
                    reason = "large face >20%"
                elif edge_density < 0.11:
                    # Any face detected with low edges = talking head
                    # Screen shares have sharp edges (UI, text), talking heads don't
                    is_talking_head = True
                    reason = f"face detected with low edges (<11%)"
                elif face_ratio > 0.05 and center_dist_x < 0.3 and center_dist_y < 0.3:
                    is_talking_head = True
                    reason = "centered small face"

                if is_talking_head:
                    logger.info(f"   🚫 REJECT: Face {face_ratio:.1%}, edges {edge_density:.1%} - {reason}")
                    return False
                else:
                    logger.info(f"   👤 Face {face_ratio:.1%}, edges {edge_density:.1%}, center ({center_dist_x:.1%}, {center_dist_y:.1%})")

            # Analyze edge density for screen share characteristics
            if edge_density > 0.12:  # Lots of sharp edges = likely screen content
                logger.info(f"   ✅ KEEP: High edges {edge_density:.1%} - screen share")
                return True

            # If we have some edges but not many, it might still be screen content
            # (e.g., a slide with minimal text)
            if edge_density > 0.05:
                logger.info(f"   ✅ KEEP: Moderate edges {edge_density:.1%} - screen share")
                return True

            # Very low edge density (<5%) and no large face detected
            # Likely blank screen, sponsor intro, or transition slide - reject it
            logger.info(f"   🚫 REJECT: Low edges {edge_density:.1%} - likely blank/transition screen")
            return False

        except Exception as e:
            logger.warning(f"⚠️ Error analyzing frame {frame_path}: {e}")
            return True  # Keep frame by default on error

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
