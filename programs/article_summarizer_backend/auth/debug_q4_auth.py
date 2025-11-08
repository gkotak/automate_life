#!/usr/bin/env python3
"""
Debug Q4 Inc authentication - test what happens when we load cookies
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def test_q4_auth():
    """Test Q4 authentication with current storage_state.json"""

    # Load storage state
    storage_file = Path(__file__).parent / 'storage_state.json'

    with open(storage_file, 'r') as f:
        storage_state = json.load(f)

    # Filter to Q4 cookies for debugging
    q4_cookies = [c for c in storage_state.get('cookies', [])
                  if 'q4' in c.get('domain', '').lower()]

    print(f"\n📊 Storage State Analysis:")
    print(f"   Total cookies: {len(storage_state.get('cookies', []))}")
    print(f"   Q4 cookies: {len(q4_cookies)}")
    print(f"   Origins (localStorage): {len(storage_state.get('origins', []))}")

    # Check for Q4 localStorage
    q4_origins = [o for o in storage_state.get('origins', [])
                  if 'q4' in o.get('origin', '').lower()]

    print(f"\n🔍 Q4 Inc specific data:")
    print(f"   Q4 origins with localStorage: {len(q4_origins)}")

    for origin in q4_origins:
        local_storage = origin.get('localStorage', [])
        print(f"\n   Origin: {origin['origin']}")
        print(f"   localStorage items: {len(local_storage)}")
        for item in local_storage:
            # Show key names only (values might be sensitive)
            print(f"      - {item['name']}")

    if not q4_origins or not any(o.get('localStorage', []) for o in q4_origins):
        print(f"\n⚠️  WARNING: No localStorage found for Q4 domains!")
        print(f"   This suggests the storage_state.json doesn't have Q4 authentication data")

    # Now test with Playwright
    print(f"\n🌐 Testing Q4 URL with Playwright + storage_state...")

    url = 'https://events.q4inc.com/attendee/525896792'

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Show browser
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-setuid-sandbox',
            ]
        )

        # Create context with storage_state
        context = await browser.new_context(storage_state=storage_state)
        page = await context.new_page()

        print(f"🌐 Navigating to: {url}")
        response = await page.goto(url, wait_until='networkidle')

        print(f"📄 Response status: {response.status}")
        print(f"📄 Final URL: {page.url}")

        # Check if we got redirected to login
        if 'login' in page.url.lower() or 'signin' in page.url.lower():
            print(f"\n❌ REDIRECTED TO LOGIN PAGE")
            print(f"   Current URL: {page.url}")
        else:
            print(f"\n✅ No redirect - appears to be authenticated")

        # Check page title
        title = await page.title()
        print(f"📄 Page title: {title}")

        # Check for authentication indicators
        content = await page.content()

        if 'sign in' in content.lower() or 'log in' in content.lower():
            print(f"\n⚠️  Page contains login prompts")

        # Try to extract current cookies after navigation
        cookies_after = await context.cookies()
        q4_cookies_after = [c for c in cookies_after if 'q4' in c.get('domain', '').lower()]

        print(f"\n🍪 Cookies after navigation:")
        print(f"   Total: {len(cookies_after)}")
        print(f"   Q4 cookies: {len(q4_cookies_after)}")

        # Look for any new cookies that might be auth-related
        new_cookies = [c for c in q4_cookies_after
                      if c['name'] not in [oc['name'] for oc in q4_cookies]]

        if new_cookies:
            print(f"\n🆕 New cookies set by Q4:")
            for cookie in new_cookies:
                print(f"      {cookie['name']}: {cookie['domain']}")

        # Check localStorage after navigation
        local_storage_after = await page.evaluate("""
            () => {
                const storage = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    storage[key] = localStorage.getItem(key).substring(0, 50);  // First 50 chars
                }
                return storage;
            }
        """)

        print(f"\n💾 LocalStorage after navigation:")
        if local_storage_after:
            for key, value in local_storage_after.items():
                print(f"      {key}: {value}...")
        else:
            print(f"      (empty)")

        print(f"\n⏸️  Browser will stay open. Press Enter to close...")
        input()

        await browser.close()


if __name__ == '__main__':
    asyncio.run(test_q4_auth())
