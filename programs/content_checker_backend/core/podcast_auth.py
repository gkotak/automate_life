"""
Podcast authentication handler for podcast tracking
Uses Playwright for web-based login with username/password
"""

import os
import logging
import asyncio
from typing import Optional, Dict, List


class PodcastAuth:
    """Handle PocketCasts authentication using Playwright"""

    LOGIN_URL = "https://pocketcasts.com/user/login"
    HISTORY_URL = "https://pocketcasts.com/history"

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        # Load credentials from environment
        self.email = os.getenv('POCKETCASTS_EMAIL')
        self.password = os.getenv('POCKETCASTS_PASSWORD')

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

                # Wait for login form to be visible
                self.logger.info("Waiting for login form...")
                await page.wait_for_selector('input[type="email"]', timeout=10000)

                # Fill in email
                self.logger.info("Filling in email address...")
                email_input = page.locator('input[type="email"]').first
                await email_input.fill(self.email)

                # Fill in password
                self.logger.info("Filling in password...")
                password_input = page.locator('input[type="password"]').first
                await password_input.fill(self.password)

                # Set up response handler to detect login success/failure
                login_response_received = asyncio.Event()
                login_success = False

                async def check_login_response(response):
                    nonlocal login_success
                    url = response.url
                    # Look for specific login/token API endpoints
                    if ('api.pocketcasts.com' in url and
                        ('login' in url or 'token' in url or 'user/' in url)):
                        self.logger.info(f"🔐 Login API call detected: {url}")
                        self.logger.info(f"   Status: {response.status}")
                        try:
                            if response.status == 200:
                                json_data = await response.json()
                                # Check if we got an access token (successful login)
                                if isinstance(json_data, dict) and 'accessToken' in json_data:
                                    self.logger.info(f"   ✅ Login successful - received access token")
                                    login_success = True
                                else:
                                    self.logger.info(f"   Response keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
                            else:
                                self.logger.warning(f"   Login request failed with status {response.status}")
                        except:
                            pass
                        login_response_received.set()

                page.on("response", check_login_response)

                # Click the login button
                self.logger.info("Clicking login button...")
                login_button = page.locator('button:has-text("Log in"), button[type="submit"]').first

                # Wait for either navigation or login API response
                try:
                    await login_button.click()

                    # Wait for login response (with timeout)
                    self.logger.info("Waiting for login API response...")
                    try:
                        await asyncio.wait_for(login_response_received.wait(), timeout=10.0)
                    except asyncio.TimeoutError:
                        self.logger.warning("⚠️  No login API response detected within 10 seconds")

                    # Also wait for page to settle
                    await page.wait_for_load_state('networkidle', timeout=15000)

                    if not login_success:
                        self.logger.error("❌ Login appears to have failed - no successful login API response")
                        # Check current URL
                        current_url = page.url
                        self.logger.error(f"   Current URL: {current_url}")
                        if 'login' in current_url:
                            self.logger.error("   Still on login page - credentials may be incorrect")
                            return None
                except Exception as e:
                    self.logger.error(f"Error during login: {e}")
                    return None

                self.logger.info("✅ Login completed successfully")

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

