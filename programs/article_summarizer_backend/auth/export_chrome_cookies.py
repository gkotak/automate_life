#!/usr/bin/env python3
"""
Export authenticated Chrome cookies and upload to Supabase

This script:
1. Extracts cookies from your Chrome browser (all sites you're logged into)
2. Converts them to Playwright storage_state.json format
3. Uploads to Supabase for Railway to use

This is much more convenient than manually logging into each site via Playwright.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables from .env.local
load_dotenv(Path(__file__).parent.parent / '.env.local')

# Import from same directory
try:
    from .cookie_utils import categorize_cookie, COOKIE_CATEGORY_ORDER
except ImportError:
    from cookie_utils import categorize_cookie, COOKIE_CATEGORY_ORDER

# Add parent to path for Supabase import
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pycookiecheat import chrome_cookies
    PYCOOKIECHEAT_AVAILABLE = True
except ImportError:
    PYCOOKIECHEAT_AVAILABLE = False
    print("❌ pycookiecheat not installed")
    print("   Install with: pip install pycookiecheat")
    sys.exit(1)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("❌ supabase-py not installed")
    print("   Install with: pip install supabase")
    sys.exit(1)


def get_chrome_cookies_for_domains(domains=None):
    """
    Extract cookies from Chrome for specified domains

    Args:
        domains: List of domains to extract cookies from. If None, uses common sites.

    Returns:
        dict: cookies by domain
    """
    if domains is None:
        # Common subscription/paywall sites
        domains = [
            'seekingalpha.com',
            'substack.com',
            'medium.com',
            'patreon.com',
            'tegus.co',  # Tegus
            'app.tegus.co',  # Tegus app
            'nytimes.com',
            'wsj.com',
            'ft.com',
            'bloomberg.com',
            'economist.com',
            'stratechery.com',
            'lennysnewsletter.com',
            'every.to',
        ]

    all_cookies = {}

    for domain in domains:
        try:
            # pycookiecheat needs a full URL
            url = f"https://{domain}"
            domain_cookies = chrome_cookies(url)

            if domain_cookies:
                all_cookies[domain] = domain_cookies
                print(f"   ✓ {domain}: {len(domain_cookies)} cookies")

        except Exception as e:
            # Skip domains with no cookies
            if "No cookies found" not in str(e):
                print(f"   ⚠️  {domain}: {e}")
            continue

    return all_cookies


def convert_to_playwright_format(chrome_cookies_by_domain):
    """
    Convert Chrome cookies to Playwright storage_state.json format

    Args:
        chrome_cookies_by_domain: Dict of {domain: {cookie_name: cookie_value}}

    Returns:
        dict: Playwright storage_state format
    """
    playwright_cookies = []

    for domain, cookies in chrome_cookies_by_domain.items():
        for name, value in cookies.items():
            # Build cookie object
            cookie = {
                "name": name,
                "value": value,
                "domain": f".{domain}",  # Prefix with . for subdomain matching
                "path": "/",
                "expires": (datetime.now() + timedelta(days=30)).timestamp(),
            }

            # Set security attributes based on cookie prefix
            if name.startswith('__Secure-') or name.startswith('__Host-'):
                cookie["secure"] = True
                cookie["sameSite"] = "None"  # Secure cookies often need SameSite=None
            else:
                # Best guess for other cookies - most modern sites use secure
                cookie["secure"] = domain not in ['localhost', '127.0.0.1']
                cookie["sameSite"] = "Lax"

            # We can't determine httpOnly from pycookiecheat, so omit it
            # Browsers will use the default (false) which is safer than guessing

            playwright_cookies.append(cookie)

    # Create Playwright storage_state structure
    storage_state = {
        "cookies": playwright_cookies,
        "origins": []
    }

    return storage_state


def save_storage_state(storage_state, output_file='auth/storage_state.json'):
    """Save storage state to JSON file"""
    output_path = Path(__file__).parent / Path(output_file).name

    with open(output_path, 'w') as f:
        json.dump(storage_state, f, indent=2)

    return output_path


def upload_to_supabase(storage_state, platform='all'):
    """Upload storage state to Supabase"""
    # Load environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        print("\n❌ ERROR: Missing Supabase credentials")
        print("   Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables")
        print("   Cannot proceed without Supabase - cookies will not be uploaded")
        sys.exit(1)

    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)

    print(f"\n📤 Uploading to Supabase...")

    # Upsert to database
    result = supabase.table('browser_sessions').upsert({
        'platform': platform,
        'storage_state': storage_state,
        'updated_at': datetime.utcnow().isoformat(),
        'expires_at': (datetime.utcnow() + timedelta(days=30)).isoformat(),
        'is_active': True
    }, on_conflict='platform').execute()

    print(f"✅ Uploaded to Supabase!")
    print(f"   Session ID: {result.data[0]['id']}")
    print(f"   Platform: {platform}")


def main():
    """Main function"""
    print("🍪 Exporting Chrome Cookies\n")
    print("=" * 60)

    # 1. Extract Chrome cookies
    print("\n1️⃣  Extracting cookies from Chrome...\n")
    chrome_cookies_by_domain = get_chrome_cookies_for_domains()

    if not chrome_cookies_by_domain:
        print("\n❌ No cookies found!")
        print("   Make sure you're logged into sites in Chrome")
        sys.exit(1)

    total_cookies = sum(len(cookies) for cookies in chrome_cookies_by_domain.values())
    print(f"\n   ✅ Found {total_cookies} cookies from {len(chrome_cookies_by_domain)} domains")

    # 2. Convert to Playwright format
    print("\n2️⃣  Converting to Playwright format...")
    storage_state = convert_to_playwright_format(chrome_cookies_by_domain)

    # 3. Analyze and categorize cookies
    print("\n3️⃣  Analyzing cookies...\n")
    cookies_by_category = {}

    for cookie in storage_state['cookies']:
        domain = cookie.get('domain', '').lstrip('.')
        name = cookie.get('name', 'unknown')
        http_only = cookie.get('httpOnly', False)
        secure = cookie.get('secure', False)

        # Categorize cookie
        category, certainty = categorize_cookie(name, domain, http_only, secure)

        # Group by category
        if category not in cookies_by_category:
            cookies_by_category[category] = []
        cookies_by_category[category].append({
            'name': name,
            'domain': domain,
            'certainty': certainty
        })

    # Show cookie breakdown
    for category in COOKIE_CATEGORY_ORDER:
        if category in cookies_by_category:
            cookie_list = cookies_by_category[category]
            print(f"\n   {category} ({len(cookie_list)} cookies):")
            for cookie_info in cookie_list[:5]:  # Show max 5 per category
                certainty_indicator = "⚠️" if cookie_info['certainty'] == 'low' else ""
                print(f"      {certainty_indicator}- {cookie_info['name']} ({cookie_info['domain']})")
            if len(cookie_list) > 5:
                print(f"      ... and {len(cookie_list) - 5} more")

    # 4. Save to file
    print("\n4️⃣  Saving to storage_state.json...")
    output_path = save_storage_state(storage_state)
    print(f"   ✅ Saved to: {output_path}")

    # 5. Upload to Supabase
    print("\n5️⃣  Uploading to Supabase...")
    upload_to_supabase(storage_state, platform='all')

    # Final summary
    print("\n" + "=" * 60)
    print("✅ Export Complete!\n")
    print("🎉 Your Chrome cookies are now available on Railway!")
    print("   The backend will automatically use them for authenticated requests.")
    print("\n💡 To refresh cookies in the future, just run this script again!")


if __name__ == '__main__':
    main()
