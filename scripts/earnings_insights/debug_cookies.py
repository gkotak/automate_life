"""
Debug script to inspect cookies in storage_state
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import shared modules
earnings_insights_dir = project_root / 'programs' / 'earnings_insights'
sys.path.insert(0, str(earnings_insights_dir))
from shared import AuthenticationManager

import requests

# Initialize AuthenticationManager
session = requests.Session()
auth_manager = AuthenticationManager(base_dir=project_root, session=session)

# Load storage state
storage_state = auth_manager._load_storage_state_from_supabase()

if not storage_state:
    print("❌ No storage_state found")
    sys.exit(1)

print(f"\n📊 Storage State Analysis")
print(f"=" * 60)

cookies = storage_state.get('cookies', [])
print(f"\nTotal cookies: {len(cookies)}")

# Group by domain
by_domain = {}
for cookie in cookies:
    domain = cookie.get('domain', 'unknown')
    if domain not in by_domain:
        by_domain[domain] = []
    by_domain[domain].append(cookie)

print(f"\n📍 Cookies by domain:")
for domain, domain_cookies in sorted(by_domain.items()):
    print(f"\n  {domain} ({len(domain_cookies)} cookies):")
    for cookie in domain_cookies:
        name = cookie.get('name', 'unknown')
        expires = cookie.get('expires', -1)

        # Check if expired
        import time
        is_expired = expires != -1 and expires < time.time()
        status = "❌ EXPIRED" if is_expired else "✅"

        # Format expiry
        if expires == -1:
            expires_str = "session"
        else:
            from datetime import datetime
            expires_str = datetime.fromtimestamp(expires).strftime('%Y-%m-%d %H:%M')

        print(f"    {status} {name}: expires={expires_str}")

# Check for SeekingAlpha specific cookies
print(f"\n🔍 Seeking Alpha cookies:")
sa_cookies = [c for c in cookies if 'seekingalpha' in c.get('domain', '').lower()]
if sa_cookies:
    print(f"  Found {len(sa_cookies)} SeekingAlpha cookies:")
    for cookie in sa_cookies:
        print(f"    - {cookie.get('name')}: {cookie.get('domain')}")
else:
    print(f"  ⚠️ No SeekingAlpha cookies found!")

# Check origins
origins = storage_state.get('origins', [])
print(f"\n🌐 Origins ({len(origins)}):")
for origin in origins[:10]:  # Show first 10
    print(f"  - {origin.get('origin', 'unknown')}")

print(f"\n" + "=" * 60)
