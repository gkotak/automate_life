#!/usr/bin/env python3
"""
Delete Q4 Inc cookies from Supabase database.
Q4 uses username/password authentication instead of cookies.
"""

import os
import json
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

def delete_q4_cookies():
    """Delete all Q4 Inc cookies from browser_sessions storage_state JSON"""

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        return

    supabase = create_client(supabase_url, supabase_key)

    # Q4 domains to filter out
    q4_domains = [
        'q4inc.com',
        'q4web.com'
    ]

    print("🔍 Loading browser session from Supabase...")

    # Get active browser session
    result = supabase.table('browser_sessions')\
        .select('*')\
        .eq('platform', 'all')\
        .eq('is_active', True)\
        .order('updated_at', desc=True)\
        .limit(1)\
        .execute()

    if not result.data:
        print("  ℹ️  No active browser session found")
        return

    session = result.data[0]
    storage_state = session.get('storage_state', {})
    cookies = storage_state.get('cookies', [])

    print(f"  Found {len(cookies)} total cookies")

    # Count and filter Q4 cookies
    q4_cookies = []
    filtered_cookies = []

    for cookie in cookies:
        domain = cookie.get('domain', '')
        is_q4 = any(q4_domain in domain for q4_domain in q4_domains)

        if is_q4:
            q4_cookies.append(cookie)
            print(f"  🗑️  Will remove: {cookie.get('name')} ({domain})")
        else:
            filtered_cookies.append(cookie)

    if not q4_cookies:
        print("  ✅ No Q4 cookies found - nothing to delete")
        return

    print(f"\n🗑️  Removing {len(q4_cookies)} Q4 cookies...")

    # Update storage_state with filtered cookies
    storage_state['cookies'] = filtered_cookies

    # Update the session in Supabase
    update_result = supabase.table('browser_sessions')\
        .update({'storage_state': storage_state})\
        .eq('id', session['id'])\
        .execute()

    print(f"✅ Successfully removed {len(q4_cookies)} Q4 cookies")
    print(f"   Remaining cookies: {len(filtered_cookies)}")
    print("   Q4 will now use username/password authentication only")

if __name__ == '__main__':
    delete_q4_cookies()
