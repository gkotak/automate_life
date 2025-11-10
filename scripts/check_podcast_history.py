#!/usr/bin/env python3
"""
CLI wrapper for checking PocketCasts listening history
Calls the content_checker_backend API
"""

import asyncio
import os
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / 'programs' / 'content_checker_backend' / '.env.local'
if env_path.exists():
    load_dotenv(env_path)

# API configuration
CONTENT_CHECKER_API_URL = os.getenv('CONTENT_CHECKER_API_URL', 'http://localhost:8001')
API_KEY = os.getenv('CONTENT_CHECKER_API_KEY', '')


async def check_podcast_history():
    """Call the content_checker_backend API to check PocketCasts listening history"""

    print("🎙️  Checking PocketCasts listening history for new episodes...")
    print(f"📡 API: {CONTENT_CHECKER_API_URL}")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Call the check endpoint
            response = await client.post(
                f"{CONTENT_CHECKER_API_URL}/api/podcast-history/check",
                headers={"X-API-Key": API_KEY}
            )

            if response.status_code == 200:
                data = response.json()

                print(f"\n✅ {data['message']}")
                print(f"📊 New episodes: {data['new_podcasts_found']}")
                print(f"📊 Episodes checked: {data['total_episodes_checked']}")

                if data.get('newly_discovered_ids'):
                    print(f"\n🆕 Newly discovered episodes ({len(data['newly_discovered_ids'])}):")
                    for episode_id in data['newly_discovered_ids'][:10]:  # Show first 10
                        print(f"   - {episode_id}")
                    if len(data['newly_discovered_ids']) > 10:
                        print(f"   ... and {len(data['newly_discovered_ids']) - 10} more")

                return 0

            elif response.status_code == 401:
                print("❌ Authentication failed. Check your API key.")
                return 1

            else:
                print(f"❌ API error: {response.status_code}")
                print(f"   {response.text}")
                return 1

    except httpx.ConnectError:
        print(f"❌ Could not connect to {CONTENT_CHECKER_API_URL}")
        print("   Make sure content_checker_backend is running:")
        print("   cd programs/content_checker_backend && venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001")
        return 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point"""
    exit_code = asyncio.run(check_podcast_history())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
