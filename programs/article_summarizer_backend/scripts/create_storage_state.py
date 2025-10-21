#!/usr/bin/env python3
"""
Create Playwright storage_state.json from Chrome cookies

This script:
1. Extracts cookies from Chrome using pycookiecheat
2. Launches Playwright in headless mode
3. Injects cookies into Playwright context
4. Saves browser state to storage_state.json for Railway
"""

import json
import os
from pathlib import Path

try:
    from pycookiecheat import chrome_cookies
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   Install with: pip install pycookiecheat playwright")
    exit(1)


def create_storage_state():
    """Create storage_state.json from Chrome cookies"""

    storage_dir = Path(__file__).parent.parent / 'storage'
    storage_dir.mkdir(exist_ok=True)
    storage_state_file = storage_dir / 'storage_state.json'

    print("🔍 Extracting cookies from Chrome...")

    # Extract cookies for key platforms
    platforms = {
        'substack.com': 'https://substack.com',
        'medium.com': 'https://medium.com',
        'seekingalpha.com': 'https://seekingalpha.com',
    }

    all_cookies = []

    for domain, url in platforms.items():
        try:
            cookies = chrome_cookies(url)
            if cookies:
                print(f"✅ Found {len(cookies)} cookies for {domain}")
                # Convert to Playwright cookie format
                for name, value in cookies.items():
                    all_cookies.append({
                        'name': name,
                        'value': value,
                        'domain': domain if not domain.startswith('.') else domain,
                        'path': '/',
                        'secure': True,
                        'httpOnly': False,
                        'sameSite': 'Lax'
                    })
        except Exception as e:
            print(f"⚠️  Could not extract cookies for {domain}: {e}")

    if not all_cookies:
        print("❌ No cookies found. Make sure you're logged in to these sites in Chrome.")
        return None

    print(f"\n🌐 Launching Playwright to create browser state...")

    with sync_playwright() as p:
        # Launch headless browser
        browser = p.chromium.launch(headless=True)

        # Create context and inject cookies
        context = browser.new_context()
        context.add_cookies(all_cookies)

        # Visit each platform to establish session
        page = context.new_page()
        for domain, url in platforms.items():
            try:
                print(f"🔗 Visiting {domain}...")
                page.goto(url, timeout=10000, wait_until='domcontentloaded')
            except Exception as e:
                print(f"⚠️  Could not visit {domain}: {e}")

        # Save storage state
        print(f"\n💾 Saving browser state to {storage_state_file}...")
        context.storage_state(path=str(storage_state_file))

        browser.close()

    print(f"✅ Storage state saved successfully!")
    print(f"   File: {storage_state_file}")
    print(f"\nNext step: Upload this file to Railway storage")

    return str(storage_state_file)


if __name__ == '__main__':
    create_storage_state()
