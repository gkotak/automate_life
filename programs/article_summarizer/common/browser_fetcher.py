"""
Browser Fetcher Module

Handles content fetching using Playwright for sites with anti-bot measures.
Uses headless browser automation to bypass Cloudflare and other bot detection.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

# Try to import Playwright
try:
    from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - browser fetching disabled. Install with: pip install playwright && playwright install chromium")


class BrowserFetcher:
    """Fetches content using Playwright for complex authentication scenarios"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
        self.timeout = int(os.getenv('PLAYWRIGHT_TIMEOUT', '30000'))
        self.screenshot_on_error = os.getenv('PLAYWRIGHT_SCREENSHOT_ON_ERROR', 'false').lower() == 'true'

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning("⚠️ [BROWSER FETCHER] Playwright not available")
        else:
            self.logger.info("✅ [BROWSER FETCHER] Playwright available")

    def is_available(self) -> bool:
        """Check if Playwright is available"""
        return PLAYWRIGHT_AVAILABLE

    def fetch_with_playwright(self, url: str, cookies: Optional[Dict] = None) -> Tuple[bool, Optional[str], str]:
        """
        Fetch content using Playwright browser automation

        Args:
            url: The URL to fetch
            cookies: Optional dictionary of cookies to inject (from requests.Session)

        Returns:
            Tuple of (success, html_content, message)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, None, "Playwright not installed"

        self.logger.info(f"🌐 [BROWSER FETCH] Launching browser for: {url}")
        self.logger.info(f"🌐 [BROWSER FETCH] Headless: {self.headless}, Timeout: {self.timeout}ms")

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )

                # Create context with realistic settings
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                )

                # Inject cookies if provided
                if cookies:
                    self._inject_cookies(context, cookies, url)

                # Create page and navigate
                page = context.new_page()

                # Additional stealth: hide webdriver property
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                self.logger.info(f"🌐 [BROWSER FETCH] Navigating to URL...")

                try:
                    # Navigate with timeout
                    response = page.goto(url, timeout=self.timeout, wait_until='networkidle')

                    if response:
                        self.logger.info(f"🌐 [BROWSER FETCH] Response status: {response.status}")

                    # Wait for content to load
                    success = self._wait_for_content(page)

                    if not success:
                        self.logger.warning("⚠️ [BROWSER FETCH] Content did not load within timeout")

                    # Take screenshot for debugging (always, not just on error)
                    screenshot_path = self._take_screenshot(page, url)
                    self.logger.info(f"📸 [BROWSER FETCH] Screenshot saved: {screenshot_path}")

                    # Extract HTML
                    html_content = page.content()

                    # Try to detect logged-in user from page content
                    logged_in_user = self._detect_logged_in_user_from_page(page)
                    if logged_in_user:
                        self.logger.info(f"✅ [BROWSER FETCH] Successfully fetched {len(html_content)} chars - authenticated as: {logged_in_user}")
                    else:
                        self.logger.info(f"✅ [BROWSER FETCH] Successfully fetched {len(html_content)} chars")

                    browser.close()
                    return True, html_content, "Success"

                except PlaywrightTimeoutError as e:
                    self.logger.error(f"❌ [BROWSER FETCH] Timeout: {e}")

                    if self.screenshot_on_error:
                        screenshot_path = self._take_screenshot(page, url)
                        self.logger.info(f"📸 [BROWSER FETCH] Screenshot saved: {screenshot_path}")

                    browser.close()
                    return False, None, f"Timeout: {str(e)}"

        except Exception as e:
            self.logger.error(f"❌ [BROWSER FETCH] Error: {e}")
            return False, None, f"Error: {str(e)}"

    def _inject_cookies(self, context, cookies: Dict, url: str):
        """
        Inject cookies from requests.Session into Playwright context

        Args:
            context: Playwright browser context
            cookies: Dictionary or CookieJar from requests.Session
            url: URL for domain context
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        # Handle both dict and requests.cookies.RequestsCookieJar
        if hasattr(cookies, 'items'):
            cookie_items = cookies.items()
        else:
            cookie_items = [(c.name, c.value) for c in cookies]

        cookie_count = 0
        for name, value in cookie_items:
            try:
                # Create cookie for Playwright
                cookie_dict = {
                    'name': name,
                    'value': value,
                    'domain': domain if not domain.startswith('.') else domain,
                    'path': '/',
                }
                context.add_cookies([cookie_dict])
                cookie_count += 1
            except Exception as e:
                self.logger.warning(f"⚠️ [BROWSER FETCH] Could not inject cookie {name}: {e}")

        if cookie_count > 0:
            self.logger.info(f"🍪 [BROWSER FETCH] Injected {cookie_count} cookies into browser context")
        else:
            self.logger.warning("⚠️ [BROWSER FETCH] No cookies injected")

    def _wait_for_content(self, page: 'Page') -> bool:
        """
        Wait for article content to load

        Args:
            page: Playwright page object

        Returns:
            True if content loaded, False otherwise
        """
        # Try multiple selectors for article content
        content_selectors = [
            'article',
            '[role="main"]',
            '.article-content',
            '.post-content',
            '.entry-content',
            'main',
        ]

        for selector in content_selectors:
            try:
                page.wait_for_selector(selector, timeout=5000, state='visible')
                self.logger.info(f"✅ [BROWSER FETCH] Found content using selector: {selector}")

                # Scroll down to trigger lazy-loaded images
                page.evaluate('''
                    () => {
                        window.scrollTo(0, document.body.scrollHeight / 2);
                    }
                ''')
                page.wait_for_timeout(1000)

                page.evaluate('''
                    () => {
                        window.scrollTo(0, document.body.scrollHeight);
                    }
                ''')
                page.wait_for_timeout(2000)

                # Scroll back to top
                page.evaluate('() => { window.scrollTo(0, 0); }')
                page.wait_for_timeout(1000)

                self.logger.info("✅ [BROWSER FETCH] Scrolled page to trigger lazy-loaded images")
                return True
            except PlaywrightTimeoutError:
                continue

        # If no specific content selector found, just wait a bit for JS to execute
        self.logger.info("⚠️ [BROWSER FETCH] No specific content selector found, waiting for page to settle...")
        page.wait_for_timeout(5000)  # Wait 5 seconds for JS and images
        return True

    def _detect_logged_in_user_from_page(self, page: 'Page') -> Optional[str]:
        """
        Detect logged-in user from page content

        Args:
            page: Playwright page object

        Returns:
            Username if detected, None otherwise
        """
        try:
            # Try to find username in common selectors
            selectors = [
                '[data-testid="account-menu"]',
                '[class*="account"]',
                '[class*="profile"]',
                '[class*="user-menu"]',
                'button[aria-label*="account"]',
                'button[aria-label*="profile"]',
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=1000):
                        text = element.text_content()
                        if text and len(text) > 2 and len(text) < 50:
                            return text.strip()
                except Exception:
                    continue

            # Try to extract from page content using regex
            import re
            html_content = page.content()

            username_patterns = [
                r'"username":\s*"([^"]+)"',
                r'"email":\s*"([^"@]+@[^"]+)"',
                r'"user":\s*"([^"]+)"',
                r'data-user[^>]*=\s*"([^"]+)"',
            ]

            for pattern in username_patterns:
                match = re.search(pattern, html_content)
                if match:
                    return match.group(1)

        except Exception as e:
            self.logger.debug(f"Could not detect logged-in user: {e}")

        return None

    def _take_screenshot(self, page: 'Page', url: str) -> str:
        """
        Take screenshot for debugging

        Args:
            page: Playwright page object
            url: URL being fetched

        Returns:
            Path to screenshot file
        """
        from urllib.parse import urlparse
        import time

        parsed = urlparse(url)
        domain = parsed.netloc.replace('.', '_')
        timestamp = int(time.time())

        screenshot_path = f"/tmp/playwright_error_{domain}_{timestamp}.png"
        page.screenshot(path=screenshot_path, full_page=True)

        return screenshot_path

    def should_use_browser_fetch(self, url: str, response: Optional[requests.Response] = None) -> bool:
        """
        Determine if browser fetch should be used based on URL or response

        Args:
            url: The URL being fetched
            response: Optional response from requests library

        Returns:
            True if browser fetch should be used
        """
        # Check environment variable for domains that always need browser fetch
        browser_fetch_domains = os.getenv('BROWSER_FETCH_DOMAINS', '').split(',')
        browser_fetch_domains = [d.strip() for d in browser_fetch_domains if d.strip()]

        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        # Check if domain is in always-use-browser list
        for browser_domain in browser_fetch_domains:
            if browser_domain in domain:
                self.logger.info(f"🌐 [BROWSER FETCH] Domain {domain} configured for browser fetch")
                return True

        # Check response for bot blocking indicators
        if response:
            content = response.text.lower()

            # Cloudflare challenge
            if 'checking your browser' in content or 'cloudflare' in content:
                self.logger.info("🌐 [BROWSER FETCH] Cloudflare challenge detected")
                return True

            # Bot blocking messages
            if 'access denied' in content or 'forbidden' in content or '403' in content:
                self.logger.info("🌐 [BROWSER FETCH] Access denied/bot blocking detected")
                return True

            # Captcha
            if 'captcha' in content or 'recaptcha' in content:
                self.logger.info("🌐 [BROWSER FETCH] CAPTCHA detected")
                return True

            # JavaScript required messages (Pocket Casts, SPAs, etc.)
            if 'you need to enable javascript' in content or 'javascript is required' in content or 'please enable javascript' in content:
                self.logger.info("🌐 [BROWSER FETCH] JavaScript required message detected")
                return True

            # React/SPA loading indicators
            if '<div id="root"></div>' in content or '<div id="app"></div>' in content:
                # Check if there's minimal content (likely a SPA that needs JS)
                if len(content) < 5000:
                    self.logger.info("🌐 [BROWSER FETCH] Single Page App detected (minimal HTML)")
                    return True

        return False
