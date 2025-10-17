#!/usr/bin/env python3
"""
Test script for podcast URL search functionality
"""

import sys
import os
from pathlib import Path

# Set debug logging
os.environ['DEBUG_LOGGING'] = '1'

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from processors.podcast_checker import PodcastChecker

def main():
    """Test URL search for a single episode"""
    checker = PodcastChecker()

    # Test cases - podcasts that likely have YouTube versions
    test_cases = [
        {
            "podcast": "Latent Space: The AI Engineer Podcast",
            "episode": "DevDay 2025: Apps SDK, Agent Kit, MCP, Codex and why Prompting still matters"
        },
        {
            "podcast": "Acquired",
            "episode": "Google: The AI Company"
        },
        {
            "podcast": "Lenny's Podcast: Product | Career | Growth",
            "episode": "Inside Google's AI turnaround: The rise of AI Mode, strategy behind Search, and how AI agents will transform products"
        }
    ]

    print("=" * 80)
    print("TESTING PODCAST URL SEARCH")
    print("=" * 80)
    print()

    for idx, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {idx}/{len(test_cases)}")
        print(f"{'=' * 80}")
        print(f"Podcast: {test['podcast']}")
        print(f"Episode: {test['episode'][:80]}...")
        print()

        url = checker._search_podcast_video_url(test['episode'], test['podcast'])

        if url:
            print(f"\n✅ SUCCESS: Found URL")
            print(f"   {url}")
        else:
            print(f"\n❌ FAILED: No URL found")

        print()

        # Test all to verify consistency
        # (commented out for faster testing)
        # if idx == 1:
        #     break

if __name__ == "__main__":
    main()
