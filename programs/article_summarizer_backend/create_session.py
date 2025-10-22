#!/usr/bin/env python3
"""
Simple script to create Playwright session file for Railway
Run this locally, then upload the session file to Railway
"""

from playwright.sync_api import sync_playwright
import os

def create_session():
    storage_dir = './storage'
    os.makedirs(storage_dir, exist_ok=True)

    with sync_playwright() as p:
        # Launch visible browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Go to Substack login
        page.goto('https://substack.com/sign-in')

        print('\n🔐 Please log in to Substack in the browser window...')
        print('⏸️  Press Enter here when you are logged in and see your feed...')
        input()

        # Save session
        session_file = f'{storage_dir}/storage_state.json'
        context.storage_state(path=session_file)

        print(f'\n✅ Session saved to {session_file}')
        print('\nNext steps:')
        print('1. Upload this file to Railway using: railway run cp storage/storage_state.json /app/storage/')
        print('2. Or use the Railway web interface to upload it')

        browser.close()

if __name__ == '__main__':
    create_session()
