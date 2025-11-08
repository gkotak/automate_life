"""
Podcast authentication handler for podcast tracking
Uses Playwright for web-based login with username/password
"""

import os
import logging
import asyncio
from typing import Optional, Dict, List

# Import generalized authentication helper
from .playwright_auth import PlaywrightAuthenticator, get_pocketcasts_config


class PodcastAuth:
    """Handle PocketCasts authentication using Playwright"""

    LOGIN_URL = "https://pocketcasts.com/user/login"
    HISTORY_URL = "https://pocketcasts.com/history"

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        # Load credentials from environment
        self.email = os.getenv('POCKETCASTS_EMAIL')
        self.password = os.getenv('POCKETCASTS_PASSWORD')

        # Initialize generalized authenticator
        self.authenticator = PlaywrightAuthenticator(logger=self.logger)

        # Playwright context and cookies
        self.cookies = None
        self.authenticated = False

    async def fetch_history_page(self) -> Optional[str]:
        """
        Authenticate with PocketCasts and fetch the history page HTML

        Returns:
            HTML content of history page if successful, None otherwise
        """
        # Check credentials
        if not self.email or not self.password:
            self.logger.error("PocketCasts credentials not found in environment")
            self.logger.error("Please set POCKETCASTS_EMAIL and POCKETCASTS_PASSWORD")
            return None

        self.logger.info("Authenticating with PocketCasts using Playwright...")

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                # Launch browser with args to avoid bot detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    # Hide webdriver flag
                    extra_http_headers={
                        'Accept-Language': 'en-US,en;q=0.9'
                    }
                )

                # Remove navigator.webdriver flag
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """)
                page = await context.new_page()

                # Navigate directly to login page
                self.logger.info(f"Navigating to {self.LOGIN_URL}")
                await page.goto(self.LOGIN_URL, wait_until='networkidle')

                # Use generalized authenticator for login
                self.logger.info("Using generalized authenticator for PocketCasts login...")
                pocketcasts_config = get_pocketcasts_config(email=self.email, password=self.password)
                login_success = await self.authenticator.login(page, pocketcasts_config)

                if not login_success:
                    self.logger.error("❌ PocketCasts login failed")
                    return None

                self.logger.info("✅ PocketCasts login completed successfully")

                # Instead of scraping HTML, intercept API calls to get episode data
                episodes_data = []
                all_responses = []

                async def handle_response(response):
                    """Capture ALL API responses for debugging"""
                    url = response.url
                    all_responses.append(url)

                    # Look for API calls that might contain episode data
                    # Check for ANY pocketcasts API endpoint
                    if 'pocketcasts.com' in url and ('/api/' in url or '/user/' in url or 'history' in url or 'episode' in url):
                        try:
                            # Try to get JSON response
                            json_data = await response.json()
                            self.logger.info(f"✅ Captured API response from: {url}")
                            self.logger.info(f"   Status: {response.status}")
                            self.logger.info(f"   Response keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
                            episodes_data.append({
                                'url': url,
                                'status': response.status,
                                'data': json_data
                            })
                        except Exception as e:
                            self.logger.debug(f"Could not parse response as JSON from {url}: {e}")

                # Register response handler BEFORE navigating
                page.on("response", handle_response)

                # Navigate to history page in the SAME authenticated session
                self.logger.info(f"Navigating to history page: {self.HISTORY_URL}")
                await page.goto(self.HISTORY_URL, wait_until='networkidle')

                # Wait longer for React app to load and make API calls
                self.logger.info("Waiting for React app to load and make API calls...")
                await page.wait_for_timeout(12000)

                # Check what page we're actually on
                current_url = page.url
                self.logger.info(f"Current page URL: {current_url}")

                # Get page title
                title = await page.title()
                self.logger.info(f"Page title: {title}")

                # Log all captured responses
                self.logger.info(f"📊 Total responses captured: {len(all_responses)}")
                self.logger.info(f"📊 API responses with potential episode data: {len(episodes_data)}")

                # Save all responses for debugging
                if all_responses:
                    unique_domains = set([url.split('/')[2] if len(url.split('/')) > 2 else url for url in all_responses])
                    self.logger.info(f"📊 Unique domains: {unique_domains}")

                # Save captured API responses for debugging
                if episodes_data:
                    self.logger.info(f"✅ Captured {len(episodes_data)} API responses with episode data")
                    import json
                    with open('/tmp/pocketcasts_api_responses.json', 'w', encoding='utf-8') as f:
                        json.dump(episodes_data, f, indent=2)
                    self.logger.info("📄 Saved API responses to /tmp/pocketcasts_api_responses.json")
                    await browser.close()
                    return json.dumps(episodes_data)

                # Otherwise return the HTML
                self.logger.warning("No API responses captured, falling back to HTML scraping")
                html_content = await page.content()

                # Save HTML for debugging
                with open('/tmp/pocketcasts_history_page.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                self.logger.info("📄 Saved history page HTML to /tmp/pocketcasts_history_page.html")

                await browser.close()
                return html_content

        except Exception as e:
            self.logger.error(f"Failed to authenticate with PocketCasts: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None

