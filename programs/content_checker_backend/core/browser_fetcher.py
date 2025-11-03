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

# Try to import Playwright (both sync and async APIs)
try:
    from playwright.sync_api import sync_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright, Browser as AsyncBrowser, Page as AsyncPage
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

    async def fetch_with_playwright_async(self, url: str, cookies: Optional[Dict] = None) -> Tuple[bool, Optional[str], str]:
        """
        Async version of fetch_with_playwright for use with FastAPI/async contexts

        Args:
            url: The URL to fetch
            cookies: Optional dictionary of cookies to inject (from requests.Session)

        Returns:
            Tuple of (success, html_content, message)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, None, "Playwright not installed"

        self.logger.info(f"🌐 [BROWSER FETCH ASYNC] Launching browser for: {url}")
        self.logger.info(f"🌐 [BROWSER FETCH ASYNC] Headless: {self.headless}, Timeout: {self.timeout}ms")

        try:
            async with async_playwright() as p:
                # Launch browser
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-gpu',
                        '--disable-setuid-sandbox',
                        '--single-process',
                        '--no-zygote',
                    ]
                )

                # Create context with realistic settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                )

                # Inject cookies if provided
                if cookies:
                    await self._inject_cookies_async(context, cookies, url)

                # Create page and navigate
                page = await context.new_page()

                # Additional stealth: hide webdriver property
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                self.logger.info(f"🌐 [BROWSER FETCH ASYNC] Navigating to URL...")

                try:
                    # Navigate with timeout
                    response = await page.goto(url, timeout=self.timeout, wait_until='networkidle')

                    if response:
                        self.logger.info(f"🌐 [BROWSER FETCH ASYNC] Response status: {response.status}")

                    # Wait for content to load
                    success = await self._wait_for_content_async(page)

                    if not success:
                        self.logger.warning("⚠️ [BROWSER FETCH ASYNC] Content did not load within timeout")

                    # Take screenshot for debugging
                    screenshot_path = await self._take_screenshot_async(page, url)
                    self.logger.info(f"📸 [BROWSER FETCH ASYNC] Screenshot saved: {screenshot_path}")

                    # Extract HTML
                    html_content = await page.content()

                    # Try to detect logged-in user from page content
                    logged_in_user = await self._detect_logged_in_user_from_page_async(page)
                    if logged_in_user:
                        self.logger.info(f"✅ [BROWSER FETCH ASYNC] Successfully fetched {len(html_content)} chars - authenticated as: {logged_in_user}")
                    else:
                        self.logger.info(f"✅ [BROWSER FETCH ASYNC] Successfully fetched {len(html_content)} chars")

                    await browser.close()
                    return True, html_content, "Success"

                except PlaywrightTimeoutError as e:
                    self.logger.error(f"❌ [BROWSER FETCH ASYNC] Timeout: {e}")

                    if self.screenshot_on_error:
                        screenshot_path = await self._take_screenshot_async(page, url)
                        self.logger.info(f"📸 [BROWSER FETCH ASYNC] Screenshot saved: {screenshot_path}")

                    await browser.close()
                    return False, None, f"Timeout: {str(e)}"

        except Exception as e:
            self.logger.error(f"❌ [BROWSER FETCH ASYNC] Error: {e}")
            return False, None, f"Error: {str(e)}"

    def should_use_browser_fetch(self, url: str, response: Optional[requests.Response] = None) -> bool:
        """
        Determine if browser fetch should be used based on URL or response

        Args:
            url: The URL being fetched
            response: Optional response from requests library

        Returns:
            True if browser fetch should be used
        """
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        # Check environment variable for domains that always need browser fetch
        browser_fetch_domains = os.getenv('BROWSER_FETCH_DOMAINS', '').split(',')
        browser_fetch_domains = [d.strip() for d in browser_fetch_domains if d.strip()]

        # Check if domain is in always-use-browser list
        for browser_domain in browser_fetch_domains:
            if browser_domain in domain:
                self.logger.info(f"🌐 [BROWSER FETCH] Domain {domain} configured for browser fetch")
                return True

        # Check response for bot blocking indicators
        if response:
            content = response.text.lower()

            # Cloudflare challenge (not just CDN usage)
            # Only trigger if we see the actual challenge page
            if 'checking your browser' in content or 'just a moment' in content:
                self.logger.info("🌐 [BROWSER FETCH] Cloudflare challenge detected")
                return True

            # Bot blocking messages
            if 'access denied' in content or 'forbidden' in content:
                # Also check if status code is 403
                if response.status_code == 403:
                    self.logger.info("🌐 [BROWSER FETCH] Access denied/bot blocking detected (403)")
                    return True

            # Captcha - only if it's actually being shown (not in config)
            # Look for actual captcha elements, not just the word in JSON
            if 'recaptcha/api' in content or 'hcaptcha.com' in content or '<div class="g-recaptcha"' in content:
                self.logger.info("🌐 [BROWSER FETCH] Active CAPTCHA detected")
                return True

            # JavaScript required messages (Pocket Casts, SPAs, etc.)
            if 'you need to enable javascript' in content or 'javascript is required' in content or 'please enable javascript' in content:
                self.logger.info("🌐 [BROWSER FETCH] JavaScript required message detected")
                return True

            # React/SPA loading indicators - empty root div with minimal content
            if ('<div id="root"></div>' in content or '<div id="app"></div>' in content):
                # Check if there's minimal content (likely a SPA that needs JS)
                if len(content) < 5000:
                    self.logger.info("🌐 [BROWSER FETCH] Single Page App detected (minimal HTML)")
                    return True

        return False

    # Async helper methods for async Playwright API

    async def _inject_cookies_async(self, context, cookies: Dict, url: str):
        """
        Async version of _inject_cookies
        Only injects cookies relevant to the target URL domain
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        target_domain = parsed.hostname or parsed.netloc  # Use hostname to strip port

        # Extract base domain (e.g., "tegus.co" from "app.tegus.co")
        domain_parts = target_domain.split('.')
        base_domain = '.'.join(domain_parts[-2:]) if len(domain_parts) >= 2 else target_domain

        def is_cookie_relevant(cookie_domain: Optional[str]) -> bool:
            """Check if cookie domain matches target domain"""
            if not cookie_domain:
                return False

            # Strip leading dot
            cookie_domain = cookie_domain.lstrip('.')

            # Match if:
            # 1. Exact match (tegus.co == tegus.co)
            # 2. Cookie is for parent domain (tegus.co cookie works on app.tegus.co)
            # 3. Cookie is for subdomain (app.tegus.co cookie works on app.tegus.co)
            return (
                cookie_domain == target_domain or
                cookie_domain == base_domain or
                target_domain.endswith('.' + cookie_domain) or
                target_domain.endswith(cookie_domain)
            )

        # Handle both dict and requests.cookies.RequestsCookieJar
        if isinstance(cookies, dict):
            cookie_list = []
            for name, value in cookies.items():
                cookie_list.append({
                    'name': name,
                    'value': value,
                    'domain': target_domain,
                    'path': '/',
                    'secure': True,
                    'httpOnly': False,
                    'sameSite': 'Lax'
                })
        else:
            cookie_list = []
            for c in cookies:
                # Filter: only include cookies for this domain
                if not is_cookie_relevant(c.domain):
                    continue

                cookie_dict = {
                    'name': c.name,
                    'value': c.value,
                    'domain': c.domain,
                    'path': c.path or '/',
                    'secure': bool(c.secure),
                    'httpOnly': bool(getattr(c, 'has_nonstandard_attr', lambda x: False)('HttpOnly')),
                    'sameSite': 'Lax'
                }
                if c.expires:
                    cookie_dict['expires'] = c.expires
                cookie_list.append(cookie_dict)

        cookie_count = 0
        failed_count = 0
        for cookie_dict in cookie_list:
            try:
                await context.add_cookies([cookie_dict])
                cookie_count += 1
            except Exception as e:
                failed_count += 1
                self.logger.debug(f"Could not inject cookie {cookie_dict.get('name')}: {e}")

        if cookie_count > 0:
            self.logger.info(f"🍪 [BROWSER FETCH ASYNC] Injected {cookie_count} cookies for {target_domain} (filtered from {cookie_count + failed_count} total)")
        else:
            self.logger.warning(f"⚠️ [BROWSER FETCH ASYNC] No cookies injected for {target_domain}")

    async def _wait_for_content_async(self, page: 'AsyncPage') -> bool:
        """Async version of _wait_for_content"""
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
                await page.wait_for_selector(selector, timeout=5000, state='visible')
                self.logger.info(f"✅ [BROWSER FETCH ASYNC] Found content using selector: {selector}")

                # Scroll down to trigger lazy-loaded images
                await page.evaluate('() => { window.scrollTo(0, document.body.scrollHeight / 2); }')
                await page.wait_for_timeout(1000)
                await page.evaluate('() => { window.scrollTo(0, document.body.scrollHeight); }')
                await page.wait_for_timeout(2000)
                await page.evaluate('() => { window.scrollTo(0, 0); }')
                await page.wait_for_timeout(1000)

                self.logger.info("✅ [BROWSER FETCH ASYNC] Scrolled page to trigger lazy-loaded images")
                return True
            except PlaywrightTimeoutError:
                continue

        # If no specific content selector found, just wait a bit for JS to execute
        self.logger.info("⚠️ [BROWSER FETCH ASYNC] No specific content selector found, waiting for page to settle...")
        await page.wait_for_timeout(5000)
        return True

    async def _detect_logged_in_user_from_page_async(self, page: 'AsyncPage') -> Optional[str]:
        """Async version of _detect_logged_in_user_from_page"""
        try:
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
                    if await element.is_visible(timeout=1000):
                        text = await element.text_content()
                        if text and len(text) > 2 and len(text) < 50:
                            return text.strip()
                except Exception:
                    continue

            # Try to extract from page content using regex
            import re
            html_content = await page.content()

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

    async def _take_screenshot_async(self, page: 'AsyncPage', url: str) -> str:
        """Async version of _take_screenshot"""
        from urllib.parse import urlparse
        import time

        parsed = urlparse(url)
        domain = parsed.netloc.replace('.', '_')
        timestamp = int(time.time())

        screenshot_path = f"/tmp/playwright_error_{domain}_{timestamp}.png"
        await page.screenshot(path=screenshot_path, full_page=True)

        return screenshot_path
