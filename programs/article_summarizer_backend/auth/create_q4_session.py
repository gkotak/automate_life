#!/usr/bin/env python3
"""
Create Q4 Inc session with complete authentication state
This captures cookies + localStorage + sessionStorage
"""

from playwright.sync_api import sync_playwright
import os
import json
from pathlib import Path

def create_q4_session():
    auth_dir = Path(__file__).parent

    with sync_playwright() as p:
        # Launch visible browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Go to Q4 Inc event page (will redirect to login if not authenticated)
        q4_url = 'https://events.q4inc.com/attendee/525896792'
        print(f'\n🌐 Opening Q4 Inc URL: {q4_url}')
        page.goto(q4_url)

        print('\n🔐 Please log in to Q4 Inc in the browser window...')
        print('⏸️  Press Enter here when you are logged in and can see the event content...')
        print('    (NOT just the registration/login page)')
        input()

        # Save complete session state (cookies + localStorage + sessionStorage)
        # Save to standard storage_state.json so we can use existing upload script
        session_file = auth_dir / 'storage_state.json'
        context.storage_state(path=str(session_file))

        # Also print out what we captured for debugging
        with open(session_file, 'r') as f:
            state = json.load(f)

        print(f'\n✅ Q4 Inc session saved to {session_file}')
        print(f'\n📊 Captured data:')
        print(f'   Cookies: {len(state.get("cookies", []))}')
        print(f'   Origins: {len(state.get("origins", []))}')

        # Show Q4-specific cookies
        q4_cookies = [c for c in state.get('cookies', [])
                     if 'q4' in c.get('domain', '').lower()]
        print(f'\n   Q4 Inc cookies: {len(q4_cookies)}')
        for cookie in q4_cookies:
            print(f'      - {cookie["name"]}: {cookie["domain"]}')

        # Show localStorage for Q4 domains
        for origin in state.get('origins', []):
            if 'q4' in origin.get('origin', '').lower():
                local_storage = origin.get('localStorage', [])
                if local_storage:
                    print(f'\n   LocalStorage for {origin["origin"]}:')
                    for item in local_storage:
                        # Don't print values (could be sensitive)
                        print(f'      - {item["name"]}')

        print('\n📤 Next steps:')
        print('1. Run: python auth/upload_session_to_supabase.py --platform q4inc')
        print('2. Session will be uploaded to Supabase for Railway to use')

        browser.close()

if __name__ == '__main__':
    create_q4_session()
