#!/usr/bin/env python3
"""
Process an article via the API endpoint (same behavior as web UI)

This script calls the /api/article/process-direct endpoint, providing
the same functionality as the web UI with all features:
- Privacy auto-detection
- Duplicate handling
- Demo video frame support
- Library management

Usage:
    python3 scripts/process_article_cli.py <url> [options]

Examples:
    python3 scripts/process_article_cli.py "https://youtube.com/watch?v=abc123"
    python3 scripts/process_article_cli.py "https://example.com/article" --demo-video
    python3 scripts/process_article_cli.py "https://example.com/article" --force

Options:
    --demo-video    Extract video frames for demo/screen share videos
    --force         Force reprocess even if article already exists
    --api-url       API server URL (default: http://localhost:8000)

Environment Variables:
    SUPABASE_URL            Supabase project URL
    SUPABASE_ANON_KEY       Supabase anon key (for auth)
    API_URL                 Alternative to --api-url flag

Authentication:
    You must be logged in. The script will prompt for email/password
    if no session is found, or you can set SUPABASE_AUTH_TOKEN.
"""

import argparse
import asyncio
import json
import os
import sys
import getpass

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)

try:
    from supabase import create_client
except ImportError:
    print("Error: supabase not installed. Run: pip install supabase")
    sys.exit(1)


def get_auth_token() -> str:
    """Get Supabase auth token, prompting for login if needed"""

    # Check for existing token in environment
    token = os.environ.get('SUPABASE_AUTH_TOKEN')
    if token:
        print("✅ Using auth token from SUPABASE_AUTH_TOKEN")
        return token

    # Get Supabase credentials
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_ANON_KEY')

    if not supabase_url or not supabase_key:
        print("Error: Missing Supabase credentials")
        print("  Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
        print("  Or set SUPABASE_AUTH_TOKEN directly")
        sys.exit(1)

    # Create Supabase client and prompt for login
    supabase = create_client(supabase_url, supabase_key)

    print("🔐 Authentication required")
    email = input("Email: ")
    password = getpass.getpass("Password: ")

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.session:
            print("✅ Logged in successfully")
            return response.session.access_token
        else:
            print("❌ Login failed: No session returned")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Login failed: {e}")
        sys.exit(1)


def format_duration(seconds: int) -> str:
    """Format seconds as MM:SS or HH:MM:SS"""
    if seconds < 3600:
        return f"{seconds // 60}:{seconds % 60:02d}"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:02d}"


async def process_article(url: str, token: str, api_url: str, demo_video: bool = False, force: bool = False):
    """Call the API endpoint and stream SSE events"""

    params = {
        'url': url,
        'token': token,
        'demo_video': str(demo_video).lower(),
        'force_reprocess': str(force).lower()
    }

    print(f"\n📄 Processing: {url}")
    print(f"   API: {api_url}")
    print(f"   Demo video: {demo_video}")
    print(f"   Force reprocess: {force}")
    print()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
            async with client.stream(
                'GET',
                f'{api_url}/api/article/process-direct',
                params=params
            ) as response:

                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"❌ API Error ({response.status_code}): {error_text.decode()}")
                    sys.exit(1)

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    # Parse SSE format
                    if line.startswith('event:'):
                        event_type = line[6:].strip()
                    elif line.startswith('data:'):
                        try:
                            data = json.loads(line[5:].strip())
                            handle_event(event_type if 'event_type' in dir() else 'message', data)
                        except json.JSONDecodeError:
                            pass

    except httpx.ConnectError:
        print(f"❌ Connection failed: Could not connect to {api_url}")
        print("   Make sure the API server is running")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def handle_event(event_type: str, data: dict):
    """Handle and display SSE events"""

    elapsed = data.get('elapsed', 0)
    elapsed_str = f"[{format_duration(elapsed)}]" if elapsed else ""

    if event_type == 'ping':
        print(f"🔗 {elapsed_str} Connected to API")

    elif event_type == 'started':
        print(f"🚀 {elapsed_str} Started processing")

    elif event_type == 'privacy_detected':
        is_private = data.get('is_private', False)
        privacy = "Private" if is_private else "Public"
        print(f"🔐 {elapsed_str} Privacy: {privacy}")

    elif event_type == 'duplicate_detected':
        title = data.get('title', 'Unknown')
        article_url = data.get('url', '')
        print(f"⚠️  {elapsed_str} Article already exists: {title}")
        print(f"   View at: http://localhost:3000{article_url}")
        print("   Use --force to reprocess")

    elif event_type == 'fetch_start':
        print(f"📥 {elapsed_str} Fetching article...")

    elif event_type == 'fetch_complete':
        title = data.get('title', 'Unknown')
        print(f"✅ {elapsed_str} Fetched: {title}")

    elif event_type == 'media_detected':
        media_type = data.get('media_type', 'unknown')
        print(f"🎬 {elapsed_str} Media type: {media_type}")

    elif event_type == 'content_extract_start':
        print(f"📄 {elapsed_str} Extracting content...")

    elif event_type == 'content_extracted':
        method = data.get('transcript_method', 'none')
        print(f"✅ {elapsed_str} Content extracted (method: {method})")

    elif event_type == 'transcript_progress':
        message = data.get('message', '')
        print(f"   {elapsed_str} {message}")

    elif event_type == 'ai_start':
        print(f"🤖 {elapsed_str} Generating AI summary...")

    elif event_type == 'ai_complete':
        print(f"✅ {elapsed_str} AI summary complete")

    elif event_type == 'save_start':
        print(f"💾 {elapsed_str} Saving to database...")

    elif event_type == 'save_complete':
        article_id = data.get('article_id', 'unknown')
        print(f"✅ {elapsed_str} Saved (ID: {article_id})")

    elif event_type == 'completed':
        article_id = data.get('article_id', 'unknown')
        article_url = data.get('url', f'/article/{article_id}')
        already_processed = data.get('already_processed', False)

        print()
        if already_processed:
            print(f"✅ Article added to your library")
        else:
            print(f"✅ Processing complete!")
        print(f"   Article ID: {article_id}")
        print(f"   View at: http://localhost:3000{article_url}")

    elif event_type == 'error':
        error = data.get('error', 'Unknown error')
        print(f"❌ {elapsed_str} Error: {error}")

    else:
        # Unknown event - print raw
        print(f"📌 {elapsed_str} [{event_type}] {data}")


def main():
    parser = argparse.ArgumentParser(
        description='Process an article via the API (same as web UI)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('url', help='URL of the article to process')
    parser.add_argument('--demo-video', action='store_true',
                        help='Extract video frames for demo/screen share videos')
    parser.add_argument('--force', action='store_true',
                        help='Force reprocess even if article already exists')
    parser.add_argument('--api-url', default=os.environ.get('API_URL', 'http://localhost:8000'),
                        help='API server URL (default: http://localhost:8000)')

    args = parser.parse_args()

    # Get auth token
    token = get_auth_token()

    # Run async processing
    asyncio.run(process_article(
        url=args.url,
        token=token,
        api_url=args.api_url,
        demo_video=args.demo_video,
        force=args.force
    ))


if __name__ == '__main__':
    main()
