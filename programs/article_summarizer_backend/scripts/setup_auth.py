#!/usr/bin/env python3
"""
Authentication Setup Script for Railway

This script helps you configure browser authentication for paywalled content.
Run this once on Railway to establish persistent browser sessions.

Usage:
    # In Railway shell
    python3 scripts/setup_auth.py --platform substack
    python3 scripts/setup_auth.py --platform medium
    python3 scripts/setup_auth.py --platform seekingalpha
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


PLATFORM_URLS = {
    'substack': 'https://substack.com/sign-in',
    'medium': 'https://medium.com/m/signin',
    'seekingalpha': 'https://seekingalpha.com/login',
    'patreon': 'https://www.patreon.com/login',
    'tegus': 'https://www.tegus.com/login',
}


def setup_platform_auth(platform: str, headless: bool = False):
    """
    Open browser, navigate to login page, wait for manual login,
    then save browser state to storage_state.json

    Args:
        platform: Platform to authenticate (substack, medium, etc.)
        headless: Whether to run browser in headless mode
    """

    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not installed!")
        print("   Install with: pip install playwright && playwright install chromium")
        sys.exit(1)

    if platform not in PLATFORM_URLS:
        print(f"❌ Unknown platform: {platform}")
        print(f"   Supported platforms: {', '.join(PLATFORM_URLS.keys())}")
        sys.exit(1)

    storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
    storage_state_file = Path(storage_dir) / 'storage_state.json'

    # Create storage directory if needed
    os.makedirs(storage_dir, exist_ok=True)

    print(f"🌐 Setting up authentication for {platform}")
    print(f"   Login URL: {PLATFORM_URLS[platform]}")
    print(f"   Storage: {storage_state_file}")
    print()
    print("Instructions:")
    print("1. Browser will open to login page")
    print("2. Complete login manually (enter username/password)")
    print("3. Once logged in, press Enter in this terminal")
    print("4. Browser session will be saved for future use")
    print()

    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )

        # Create context (load existing state if available)
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        if storage_state_file.exists():
            print(f"📂 Loading existing browser state...")
            context_options['storage_state'] = str(storage_state_file)

        context = browser.new_context(**context_options)
        page = context.new_page()

        # Navigate to login page
        print(f"🔗 Opening {PLATFORM_URLS[platform]}...")
        page.goto(PLATFORM_URLS[platform])

        # Wait for user to login
        input("\n⏸️  Complete login in the browser, then press Enter here to save session...")

        # Save browser state
        print(f"💾 Saving browser session...")
        context.storage_state(path=str(storage_state_file))

        print(f"✅ Authentication configured for {platform}!")
        print(f"   Session saved to: {storage_state_file}")

        browser.close()


def main():
    parser = argparse.ArgumentParser(description='Setup authentication for Railway backend')
    parser.add_argument('--platform', required=True, help='Platform to authenticate (substack, medium, seekingalpha, etc.)')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')

    args = parser.parse_args()

    try:
        setup_platform_auth(args.platform, args.headless)
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
