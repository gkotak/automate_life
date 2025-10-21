#!/usr/bin/env python3
"""
Upload browser session to Supabase

This script uploads the storage_state.json to Supabase database
instead of storing it as a file on Railway.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ supabase-py not installed")
    print("   Install with: pip install supabase")
    sys.exit(1)


def upload_session(platform: str = 'all'):
    """Upload browser session to Supabase"""

    # Load environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SECRET_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        print("   Set SUPABASE_URL and SUPABASE_SECRET_KEY environment variables")
        sys.exit(1)

    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)

    # Load storage_state.json
    storage_file = Path(__file__).parent.parent / 'storage' / 'storage_state.json'

    if not storage_file.exists():
        print(f"❌ Storage state file not found: {storage_file}")
        print("   Run: python scripts/create_storage_state.py first")
        sys.exit(1)

    with open(storage_file, 'r') as f:
        storage_state = json.load(f)

    print(f"📂 Loaded storage state from {storage_file}")
    print(f"   Cookies: {len(storage_state.get('cookies', []))}")
    print(f"   Origins: {len(storage_state.get('origins', []))}")

    # If platform is 'all', upload combined session
    if platform == 'all':
        print(f"\n📤 Uploading combined session to Supabase...")

        # Upsert to database
        result = supabase.table('browser_sessions').upsert({
            'platform': 'all',
            'storage_state': storage_state,
            'updated_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
            'is_active': True
        }, on_conflict='platform').execute()

        print(f"✅ Session uploaded for platform: all")
        print(f"   Session ID: {result.data[0]['id']}")
        print(f"   Updated at: {result.data[0]['updated_at']}")

    else:
        # Upload platform-specific session (extract cookies for that platform)
        platform_cookies = [c for c in storage_state.get('cookies', [])
                           if platform in c.get('domain', '')]

        if not platform_cookies:
            print(f"⚠️  No cookies found for platform: {platform}")
            return

        platform_state = {
            'cookies': platform_cookies,
            'origins': [o for o in storage_state.get('origins', [])
                       if platform in o.get('origin', '')]
        }

        print(f"\n📤 Uploading session for {platform} to Supabase...")
        print(f"   Cookies: {len(platform_cookies)}")

        result = supabase.table('browser_sessions').upsert({
            'platform': platform,
            'storage_state': platform_state,
            'updated_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
            'is_active': True
        }, on_conflict='platform').execute()

        print(f"✅ Session uploaded for platform: {platform}")
        print(f"   Session ID: {result.data[0]['id']}")

    print("\n🎉 Done! Railway backend can now access browser sessions from Supabase")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Upload browser session to Supabase')
    parser.add_argument('--platform', default='all',
                       help='Platform to upload (all, substack, medium, seekingalpha)')
    args = parser.parse_args()

    upload_session(args.platform)
