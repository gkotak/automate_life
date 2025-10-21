#!/usr/bin/env python3
"""
Export Chrome cookies for Substack/Medium to use on Railway

This script extracts your authentication cookies from Chrome
and exports them in a format that can be used on Railway.
"""

import json
from pathlib import Path

try:
    from pycookiecheat import chrome_cookies
except ImportError:
    print("❌ pycookiecheat not installed")
    print("   Install with: pip install pycookiecheat")
    exit(1)

def export_cookies():
    """Export cookies for common platforms"""

    platforms = {
        'substack': 'https://substack.com',
        'medium': 'https://medium.com',
        'seekingalpha': 'https://seekingalpha.com',
    }

    all_cookies = {}

    for platform, url in platforms.items():
        try:
            print(f"\n🔍 Extracting {platform} cookies from Chrome...")
            cookies = chrome_cookies(url)

            if cookies:
                all_cookies[platform] = cookies
                print(f"✅ Found {len(cookies)} cookies for {platform}")
            else:
                print(f"⚠️  No cookies found for {platform}")

        except Exception as e:
            print(f"❌ Error extracting {platform} cookies: {e}")

    if all_cookies:
        # Save to JSON file
        output_file = Path(__file__).parent.parent / 'storage' / 'chrome_cookies.json'
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(all_cookies, f, indent=2)

        print(f"\n✅ Cookies exported to: {output_file}")
        print("\nNext steps:")
        print("1. Upload this file to Railway storage directory")
        print("2. Or set as environment variable: CHROME_COOKIES=$(cat storage/chrome_cookies.json)")

        return str(output_file)
    else:
        print("\n❌ No cookies found. Make sure you're logged in to these sites in Chrome.")
        return None

if __name__ == '__main__':
    export_cookies()
