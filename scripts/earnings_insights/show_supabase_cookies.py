"""
Extract and display all cookies from Supabase browser_sessions table
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
env_path = project_root / '.env.local'
load_dotenv(env_path)

from supabase import create_client

def show_cookies():
    """Display all cookies from Supabase browser_sessions"""

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        print(f"   Checked: {env_path}")
        return

    supabase = create_client(supabase_url, supabase_key)

    # Get all active browser sessions
    result = supabase.table('browser_sessions')\
        .select('*')\
        .eq('is_active', True)\
        .order('updated_at', desc=True)\
        .execute()

    if not result.data:
        print("❌ No active browser sessions found in Supabase")
        return

    print("\n" + "=" * 100)
    print("BROWSER SESSIONS IN SUPABASE")
    print("=" * 100)

    for session in result.data:
        print(f"\n📦 Session ID: {session['id']}")
        print(f"   Platform: {session['platform']}")
        print(f"   Created: {session['created_at']}")
        print(f"   Updated: {session['updated_at']}")
        print(f"   Active: {session['is_active']}")

        storage_state = session.get('storage_state', {})
        cookies = storage_state.get('cookies', [])

        print(f"\n   🍪 Total Cookies: {len(cookies)}")

        if not cookies:
            print("      No cookies found")
            continue

        # Group cookies by domain
        by_domain = {}
        for cookie in cookies:
            domain = cookie.get('domain', 'unknown')
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append(cookie)

        print(f"\n   📊 Cookies by Domain:")
        for domain, domain_cookies in sorted(by_domain.items()):
            print(f"\n      🌐 {domain} ({len(domain_cookies)} cookies)")

            for cookie in domain_cookies:
                name = cookie.get('name', 'unknown')
                value = cookie.get('value', '')
                expires = cookie.get('expires', -1)
                path = cookie.get('path', '/')
                secure = cookie.get('secure', False)
                http_only = cookie.get('httpOnly', False)
                same_site = cookie.get('sameSite', 'None')

                # Format expiry
                import time
                if expires == -1:
                    expires_str = "session"
                    is_expired = False
                else:
                    expires_dt = datetime.fromtimestamp(expires)
                    expires_str = expires_dt.strftime('%Y-%m-%d %H:%M:%S')
                    is_expired = expires < time.time()

                # Status indicator
                status = "❌ EXPIRED" if is_expired else "✅"

                # Truncate value for display
                value_display = value[:40] + "..." if len(value) > 40 else value

                print(f"         {status} {name}")
                print(f"            Value: {value_display}")
                print(f"            Path: {path}")
                print(f"            Expires: {expires_str}")
                print(f"            Secure: {secure} | HttpOnly: {http_only} | SameSite: {same_site}")

        # Check for Seeking Alpha cookies
        sa_cookies = [c for c in cookies if 'seekingalpha' in c.get('domain', '').lower()]
        print(f"\n   🔍 Seeking Alpha Cookies: {len(sa_cookies)}")
        if sa_cookies:
            for cookie in sa_cookies:
                print(f"      ✅ {cookie['name']}: {cookie['domain']}")
        else:
            print(f"      ⚠️  No Seeking Alpha cookies found!")

        # Check for other origins
        origins = storage_state.get('origins', [])
        if origins:
            print(f"\n   🌐 Origins ({len(origins)}):")
            for origin in origins[:10]:
                print(f"      - {origin.get('origin', 'unknown')}")

        print("\n" + "-" * 100)

    print("\n" + "=" * 100)


if __name__ == "__main__":
    show_cookies()
