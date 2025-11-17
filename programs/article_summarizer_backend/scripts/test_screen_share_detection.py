#!/usr/bin/env python3
"""
Test script for screen share detection logic
Creates test images to verify face detection and edge detection work correctly
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.frame_extractor import FrameExtractor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    from PIL import Image
    CV2_AVAILABLE = True
except ImportError as e:
    logger.error(f"❌ Required libraries not available: {e}")
    logger.error("Install with: pip install opencv-python numpy pillow")
    sys.exit(1)


def create_test_face_image() -> str:
    """Create a test image with a smooth face-like appearance (low edge density)"""
    # Create blank image with gradient (smooth, like a face)
    img = np.ones((480, 640, 3), dtype=np.uint8) * 220

    # Create smooth gradient (like a face with lighting)
    for y in range(480):
        for x in range(640):
            # Smooth gradient from center
            dist = np.sqrt((x - 320)**2 + (y - 240)**2)
            intensity = max(0, 220 - int(dist / 3))
            img[y, x] = [intensity, intensity - 10, intensity - 20]

    # Add very subtle features (won't create many edges)
    center = (320, 240)
    radius = 150

    # Subtle oval shape (very smooth)
    cv2.ellipse(img, center, (radius, int(radius * 1.2)), 0, 0, 360, (210, 190, 170), -1)

    # Very subtle features (eyes, mouth) with Gaussian blur
    cv2.circle(img, (270, 210), 15, (190, 180, 170), -1)
    cv2.circle(img, (370, 210), 15, (190, 180, 170), -1)
    cv2.ellipse(img, (320, 280), (40, 20), 0, 0, 180, (200, 180, 170), -1)

    # Apply Gaussian blur to make it very smooth (low edge density)
    img = cv2.GaussianBlur(img, (21, 21), 0)

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    cv2.imwrite(temp_file.name, img)
    logger.info(f"✅ Created test face-like image (smooth, low edges): {temp_file.name}")
    return temp_file.name


def create_test_screen_share_image() -> str:
    """Create a test image that looks like a screen share (UI with text/edges)"""
    # Create blank image (white background)
    img = np.ones((480, 640, 3), dtype=np.uint8) * 255

    # Draw lots of UI elements with sharp edges to increase edge density
    # Window frame
    cv2.rectangle(img, (50, 50), (590, 430), (100, 100, 100), 2)

    # Title bar
    cv2.rectangle(img, (50, 50), (590, 80), (60, 60, 60), -1)
    cv2.putText(img, "Application Window", (60, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    # Buttons with borders
    cv2.rectangle(img, (100, 100), (200, 130), (0, 120, 255), -1)
    cv2.rectangle(img, (100, 100), (200, 130), (0, 0, 0), 2)
    cv2.rectangle(img, (220, 100), (320, 130), (0, 180, 0), -1)
    cv2.rectangle(img, (220, 100), (320, 130), (0, 0, 0), 2)

    # Text-like lines (simulate text)
    for i in range(5):
        y = 150 + i * 25
        cv2.rectangle(img, (100, y), (550, y + 12), (50, 50, 50), -1)
        cv2.rectangle(img, (100, y), (550, y + 12), (0, 0, 0), 1)

    # Grid of UI elements (like a table or data grid)
    for row in range(3):
        for col in range(4):
            x = 100 + col * 120
            y = 280 + row * 45
            cv2.rectangle(img, (x, y), (x + 100, y + 35), (220, 220, 220), -1)
            cv2.rectangle(img, (x, y), (x + 100, y + 35), (100, 100, 100), 2)
            # Add small text-like marks inside
            cv2.line(img, (x + 5, y + 10), (x + 90, y + 10), (80, 80, 80), 1)
            cv2.line(img, (x + 5, y + 20), (x + 70, y + 20), (80, 80, 80), 1)

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    cv2.imwrite(temp_file.name, img)
    logger.info(f"✅ Created test screen share image: {temp_file.name}")
    return temp_file.name


def create_test_blank_image() -> str:
    """Create a mostly blank image"""
    # Create solid color image
    img = np.ones((480, 640, 3), dtype=np.uint8) * 230

    # Add slight variation
    cv2.rectangle(img, (200, 200), (440, 280), (235, 235, 235), -1)

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    cv2.imwrite(temp_file.name, img)
    logger.info(f"✅ Created test blank image: {temp_file.name}")
    return temp_file.name


def run_tests():
    """Run screen share detection tests"""
    logger.info("=" * 60)
    logger.info("Testing Screen Share Detection Logic")
    logger.info("=" * 60)

    # Initialize extractor
    extractor = FrameExtractor()

    # Test 1: Smooth face-like image (low edges, should return False or be borderline)
    logger.info("\n📋 Test 1: Smooth/Face-like Image (Low Edge Density)")
    face_image = create_test_face_image()
    is_screen_share = extractor._is_screen_share_frame(face_image)
    logger.info(f"Result: Detected as {'screen share' if is_screen_share else 'face/webcam'}")
    logger.info(f"Note: Without real face detection, this may default to 'keep' based on edge density")
    os.unlink(face_image)

    # Test 2: Screen share image (should return True)
    logger.info("\n📋 Test 2: Screen Share/UI Image")
    screen_image = create_test_screen_share_image()
    is_screen_share = extractor._is_screen_share_frame(screen_image)
    logger.info(f"Result: {'✅ PASS' if is_screen_share else '❌ FAIL'} - Detected as {'screen share' if is_screen_share else 'face/webcam'}")
    os.unlink(screen_image)

    # Test 3: Blank image (should default to True - keep frame)
    logger.info("\n📋 Test 3: Blank/Low Content Image")
    blank_image = create_test_blank_image()
    is_screen_share = extractor._is_screen_share_frame(blank_image)
    logger.info(f"Result: {'✅ PASS' if is_screen_share else '❌ FAIL'} - Detected as {'screen share' if is_screen_share else 'face/webcam'}")
    os.unlink(blank_image)

    logger.info("\n" + "=" * 60)
    logger.info("✅ All tests completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_tests()
