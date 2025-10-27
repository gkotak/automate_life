"""
Podcast authentication handler for podcast tracking
Uses Playwright for web-based login with username/password
"""

import os
import logging
from typing import Optional, Dict, List


class PodcastAuth:
    """Handle PocketCasts authentication using Playwright"""

    LOGIN_URL = "https://pocketcasts.com/"
    HISTORY_URL = "https://pocketcasts.com/history"

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        # Load credentials from environment
        self.email = os.getenv('POCKETCASTS_EMAIL')
        self.password = os.getenv('POCKETCASTS_PASSWORD')

        # Playwright context and cookies
        self.cookies = None
        self.authenticated = False

    def authenticate_and_get_cookies(self) -> Optional[List[Dict]]:
        """
        Authenticate with PocketCasts using Playwright and return cookies

        Returns:
            List of cookies if authentication successful, None otherwise
        """
        # Check credentials
        if not self.email or not self.password:
            self.logger.error("PocketCasts credentials not found in environment")
            self.logger.error("Please set POCKETCASTS_EMAIL and POCKETCASTS_PASSWORD")
            return None

        self.logger.info("Authenticating with PocketCasts using Playwright...")

        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()

                # Navigate to PocketCasts
                self.logger.info(f"Navigating to {self.LOGIN_URL}")
                page.goto(self.LOGIN_URL, wait_until='networkidle')

                # Wait for and click the sign-in button
                try:
                    # Look for sign in button/link
                    sign_in_button = page.locator('text=/sign in/i').first
                    if sign_in_button.is_visible(timeout=5000):
                        self.logger.info("Clicking sign in button...")
                        sign_in_button.click()
                        page.wait_for_load_state('networkidle')
                except Exception as e:
                    self.logger.debug(f"Sign in button not found or already on login page: {e}")

                # Fill in email
                self.logger.info("Filling in login credentials...")
                email_input = page.locator('input[type="email"], input[name="email"], input[placeholder*="email" i]').first
                email_input.fill(self.email)

                # Fill in password
                password_input = page.locator('input[type="password"], input[name="password"]').first
                password_input.fill(self.password)

                # Click login/submit button
                login_button = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Log in")').first
                login_button.click()

                # Wait for navigation after login
                self.logger.info("Waiting for login to complete...")
                page.wait_for_load_state('networkidle', timeout=15000)

                # Check if we're logged in by trying to access history
                page.goto(self.HISTORY_URL, wait_until='networkidle')

                # If URL contains 'login', authentication failed
                if 'login' in page.url.lower() or 'signin' in page.url.lower():
                    self.logger.error("Authentication failed - still on login page")
                    browser.close()
                    return None

                # Get cookies
                self.cookies = context.cookies()
                self.authenticated = True

                self.logger.info(f"✅ Successfully authenticated - got {len(self.cookies)} cookies")

                browser.close()
                return self.cookies

        except Exception as e:
            self.logger.error(f"Failed to authenticate with PocketCasts: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None

    def get_cookies(self):
        """
        Get authentication cookies in RequestsCookieJar format for browser_fetcher

        Returns:
            RequestsCookieJar with cookies or None if not authenticated
        """
        if not self.cookies:
            playwright_cookies = self.authenticate_and_get_cookies()
            if not playwright_cookies:
                return None

            # Convert Playwright cookies to RequestsCookieJar format
            from http.cookiejar import Cookie
            from requests.cookies import RequestsCookieJar

            jar = RequestsCookieJar()
            for pc in playwright_cookies:
                # Convert Playwright cookie dict to http.cookiejar.Cookie
                cookie = Cookie(
                    version=0,
                    name=pc['name'],
                    value=pc['value'],
                    port=None,
                    port_specified=False,
                    domain=pc.get('domain', '.pocketcasts.com'),
                    domain_specified=True,
                    domain_initial_dot=pc.get('domain', '.pocketcasts.com').startswith('.'),
                    path=pc.get('path', '/'),
                    path_specified=True,
                    secure=pc.get('secure', False),
                    expires=pc.get('expires'),
                    discard=False,
                    comment=None,
                    comment_url=None,
                    rest={},
                    rfc2109=False
                )
                jar.set_cookie(cookie)

            self.cookies = jar

        return self.cookies

    def is_authenticated(self) -> bool:
        """Check if we have authentication cookies"""
        return self.authenticated and self.cookies is not None
