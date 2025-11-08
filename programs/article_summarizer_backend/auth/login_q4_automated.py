#!/usr/bin/env python3
"""
Automated Q4 Inc login using Playwright
Logs in with username/password and saves session
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def login_q4():
    """Automated Q4 login"""

    auth_dir = Path(__file__).parent
    q4_url = 'https://events.q4inc.com/attendee/525896792'

    async with async_playwright() as p:
        # Launch visible browser
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-setuid-sandbox',
            ]
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )

        page = await context.new_page()

        print(f'\n🌐 Navigating to Q4 Inc URL: {q4_url}')
        await page.goto(q4_url, wait_until='networkidle')

        # Wait for registration page to load
        print('⏳ Waiting for registration page...')
        await page.wait_for_selector('button', timeout=10000)
        await page.wait_for_timeout(2000)  # Extra wait for React to render

        # Look for "Register with a Q4 Account" button
        print('🔘 Clicking "Register with a Q4 Account" button...')

        # Try to find and click the registration button
        try:
            # Wait for the button with the specific text
            register_button = page.locator('button:has-text("Register with a Q4 Account")')
            await register_button.click()
            print('✅ Clicked registration button')
        except Exception as e:
            print(f'⚠️  Could not find registration button: {e}')
            print('🔍 Available buttons:')
            buttons = await page.locator('button').all()
            for i, btn in enumerate(buttons):
                text = await btn.inner_text()
                print(f'  {i+1}. {text}')

        # Wait for redirect to login page
        print('⏳ Waiting for login page...')
        await page.wait_for_timeout(5000)  # Give more time for React to render

        print(f'📄 Current URL: {page.url}')

        # Wait for page to be fully loaded (wait for network to be idle again)
        await page.wait_for_load_state('networkidle')
        await page.wait_for_timeout(2000)  # Extra buffer

        # Look for email/username input field
        print('🔍 Looking for login fields...')

        # Take screenshot for debugging
        screenshot_path = auth_dir / 'q4_login_page.png'
        await page.screenshot(path=str(screenshot_path))
        print(f'📸 Screenshot saved: {screenshot_path}')

        # Try common login field selectors
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[name="username"]',
            'input[placeholder*="email" i]',
            'input[placeholder*="username" i]',
            'input[id*="email" i]',
            'input[id*="username" i]',
        ]

        email_input = None
        for selector in email_selectors:
            try:
                email_input = page.locator(selector).first
                if await email_input.count() > 0:
                    print(f'✅ Found email input: {selector}')
                    break
            except:
                continue

        if not email_input or await email_input.count() == 0:
            print('❌ Could not find email input field')
            print('📄 Page HTML:')
            content = await page.content()
            # Print first 2000 chars
            print(content[:2000])
            await browser.close()
            return

        # Fill in email
        print('📝 Entering email...')
        await email_input.fill('gkotak@gmail.com')

        # Click "Next" button to proceed to password step
        print('🔘 Looking for "Next" button...')
        next_button = page.locator('button:has-text("Next")')
        if await next_button.count() > 0:
            print('✅ Found "Next" button, clicking...')
            await next_button.click()

            # Wait for password field to appear
            print('⏳ Waiting for password field...')
            await page.wait_for_timeout(2000)
        else:
            print('⚠️  Could not find "Next" button')

        # Look for password field
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="password" i]',
        ]

        password_input = None
        for selector in password_selectors:
            try:
                password_input = page.locator(selector).first
                if await password_input.count() > 0:
                    print(f'✅ Found password input: {selector}')
                    break
            except:
                continue

        if not password_input or await password_input.count() == 0:
            print('❌ Could not find password input field')
            print('📸 Taking screenshot...')
            await page.screenshot(path=str(auth_dir / 'q4_no_password_field.png'))
            await browser.close()
            return

        # Fill in password
        print('📝 Entering password...')
        await password_input.fill('Abcd1234!')

        # Look for submit button
        print('🔍 Looking for submit button...')
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Sign in")',
            'button:has-text("Log in")',
            'button:has-text("Login")',
            'input[type="submit"]',
        ]

        submit_button = None
        for selector in submit_selectors:
            try:
                submit_button = page.locator(selector).first
                if await submit_button.count() > 0:
                    print(f'✅ Found submit button: {selector}')
                    break
            except:
                continue

        if not submit_button or await submit_button.count() == 0:
            print('❌ Could not find submit button')
            await browser.close()
            return

        # Click submit
        print('🔘 Clicking submit button...')
        await submit_button.click()

        # Wait for navigation after login
        print('⏳ Waiting for login to complete...')
        await page.wait_for_timeout(5000)

        print(f'📄 Current URL after login: {page.url}')

        # Check if we're on the event page
        if 'login' in page.url.lower() or 'signin' in page.url.lower():
            print('❌ Still on login page - authentication may have failed')
            # Take another screenshot
            await page.screenshot(path=str(auth_dir / 'q4_after_login.png'))
            print('📸 Screenshot saved: q4_after_login.png')
        else:
            print('✅ Appears to be logged in!')

            # Wait a bit more to ensure everything is loaded
            await page.wait_for_timeout(3000)

            # Save complete session state
            session_file = auth_dir / 'storage_state.json'
            await context.storage_state(path=str(session_file))

            # Load and analyze what we captured
            with open(session_file, 'r') as f:
                state = json.load(f)

            print(f'\n✅ Q4 Inc session saved to {session_file}')
            print(f'\n📊 Captured data:')
            print(f'   Total cookies: {len(state.get("cookies", []))}')
            print(f'   Origins: {len(state.get("origins", []))}')

            # Show Q4-specific cookies
            q4_cookies = [c for c in state.get('cookies', [])
                         if 'q4' in c.get('domain', '').lower()]
            print(f'\n   Q4 Inc cookies: {len(q4_cookies)}')

            # Show identity.q4inc.com cookies specifically
            identity_cookies = [c for c in q4_cookies if 'identity.q4inc.com' in c.get('domain', '')]
            if identity_cookies:
                print(f'\n   identity.q4inc.com cookies:')
                for cookie in identity_cookies:
                    print(f'      - {cookie["name"]}')

            # Show localStorage for Q4 domains
            for origin in state.get('origins', []):
                if 'q4' in origin.get('origin', '').lower():
                    local_storage = origin.get('localStorage', [])
                    if local_storage:
                        print(f'\n   LocalStorage for {origin["origin"]}:')
                        for item in local_storage:
                            print(f'      - {item["name"]}')

            print('\n📤 Next step:')
            print('   Run: python auth/upload_session_to_supabase.py --platform all')

        print('\n⏸️  Browser will stay open for 10 seconds so you can verify...')
        await page.wait_for_timeout(10000)

        await browser.close()


if __name__ == '__main__':
    asyncio.run(login_q4())
