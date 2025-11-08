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
    from playwright.async_api import async_playwright, Browser as AsyncBrowser, Page as AsyncPage, TimeoutError as AsyncPlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - browser fetching disabled. Install with: pip install playwright && playwright install chromium")

# Import generalized authentication helper
from .playwright_auth import PlaywrightAuthenticator, get_q4_config


class BrowserFetcher:
    """Fetches content using Playwright for complex authentication scenarios"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
        self.timeout = int(os.getenv('PLAYWRIGHT_TIMEOUT', '30000'))
        self.screenshot_on_error = os.getenv('PLAYWRIGHT_SCREENSHOT_ON_ERROR', 'false').lower() == 'true'

        # Initialize generalized authenticator
        self.authenticator = PlaywrightAuthenticator(logger=self.logger)

        if not PLAYWRIGHT_AVAILABLE:
            self.logger.warning("⚠️ [BROWSER FETCHER] Playwright not available")
        else:
            self.logger.info("✅ [BROWSER FETCHER] Playwright available")

    def is_available(self) -> bool:
        """Check if Playwright is available"""
        return PLAYWRIGHT_AVAILABLE

    async def fetch_with_playwright_async(self, url: str, cookies: Optional[Dict] = None, storage_state: Optional[Dict] = None) -> Tuple[bool, Optional[str], str]:
        """
        Async version of fetch_with_playwright for use with FastAPI/async contexts

        Args:
            url: The URL to fetch
            cookies: Optional dictionary of cookies to inject (from requests.Session)
            storage_state: Optional Playwright storage_state dict (includes cookies, localStorage, etc.)

        Returns:
            Tuple of (success, html_content, message)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, None, "Playwright not installed"

        self.logger.info(f"🌐 [BROWSER FETCH ASYNC] Launching browser for: {url}")
        self.logger.info(f"🌐 [BROWSER FETCH ASYNC] Headless: {self.headless}, Timeout: {self.timeout}ms")
        if storage_state:
            self.logger.info(f"🌐 [BROWSER FETCH ASYNC] Using storage_state with {len(storage_state.get('cookies', []))} cookies")

        try:
            async with async_playwright() as p:
                # Detect Q4 Inc URLs which need special handling (crash with --single-process)
                is_q4_url = 'q4inc.com' in url or 'q4web.com' in url

                # Base args that work for most sites
                browser_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]

                # Only add --single-process and --no-zygote for non-Q4 URLs
                # Q4 Inc uses heavy JavaScript/WebAssembly that crashes with these flags
                if not is_q4_url:
                    browser_args.extend([
                        '--single-process',
                        '--no-zygote',
                        '--disable-gpu',
                    ])
                else:
                    # Q4-specific args: enable media features for video player
                    self.logger.info(f"🎯 [Q4 DETECTION] Q4 Inc URL detected, using media-enabled browser args")
                    browser_args.extend([
                        '--enable-features=WebRTC,WebAudio,MediaStreamTrack',
                        '--use-fake-ui-for-media-stream',  # Auto-grant media permissions
                        '--use-fake-device-for-media-stream',  # Provide fake media devices
                        '--autoplay-policy=no-user-gesture-required',  # Allow autoplay
                        '--disable-features=IsolateOrigins,site-per-process',  # Better compatibility
                    ])

                # Launch browser
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=browser_args
                )

                # Create context with realistic settings + storage_state if provided
                context_options = {
                    'viewport': {'width': 1920, 'height': 1080},
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'locale': 'en-US',
                    'timezone_id': 'America/New_York',
                }

                # Use storage_state if provided (includes cookies + localStorage + sessionStorage)
                if storage_state:
                    context_options['storage_state'] = storage_state

                context = await browser.new_context(**context_options)

                # Only inject cookies manually if storage_state not provided
                if not storage_state and cookies:
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

                    # Check for bot detection challenges and wait for manual completion
                    await self._handle_bot_challenges_async(page, url)

                    # Check if Q4 Inc URL and perform automated login if needed
                    if 'q4inc.com' in url:
                        q4_email = os.getenv('Q4_EMAIL')
                        q4_password = os.getenv('Q4_PASSWORD')

                        if q4_email and q4_password:
                            # Wait for page to render and check if login is needed
                            await page.wait_for_timeout(2000)

                            # Check if we're on a registration/login page
                            register_button = page.locator('button:has-text("Register with a Q4 Account")')
                            has_register_button = await register_button.count() > 0

                            if has_register_button:
                                self.logger.info("🔐 [Q4 AUTH] Detected Q4 registration page, performing automated login...")

                                # Use generalized authenticator
                                q4_config = get_q4_config(email=q4_email, password=q4_password)
                                login_success = await self.authenticator.login(page, q4_config)

                                if login_success:
                                    self.logger.info("✅ [Q4 AUTH] Automated login successful")
                                    # Wait for React app to load and video element to appear
                                    self.logger.info("⏳ [Q4 AUTH] Waiting for React app and video element to load...")
                                    try:
                                        await page.wait_for_selector('video', timeout=15000, state='attached')
                                        self.logger.info("✅ [Q4 AUTH] Video element loaded successfully")
                                        # Give video a bit more time to be fully ready
                                        await page.wait_for_timeout(2000)
                                    except AsyncPlaywrightTimeoutError:
                                        self.logger.warning("⚠️ [Q4 AUTH] Video element not found after login, continuing anyway...")
                                        await page.wait_for_timeout(3000)
                                else:
                                    self.logger.error("❌ [Q4 AUTH] Automated login failed")
                            else:
                                self.logger.info("✅ [Q4 AUTH] Already authenticated (no registration page)")
                        else:
                            self.logger.warning("⚠️ [Q4 AUTH] Q4_EMAIL or Q4_PASSWORD not set in environment")

                    # Wait for content to load
                    success = await self._wait_for_content_async(page)

                    if not success:
                        self.logger.warning("⚠️ [BROWSER FETCH ASYNC] Content did not load within timeout")

                    # Wait for potential dynamic video embeds (e.g., Loom iframes)
                    try:
                        self.logger.info(f"⏳ [BROWSER FETCH ASYNC] Waiting for dynamic content (iframes)...")
                        await page.wait_for_selector('iframe', timeout=5000)
                        self.logger.info(f"✅ [BROWSER FETCH ASYNC] Iframe(s) detected")
                        # Wait a bit more for iframe content to fully load
                        await page.wait_for_timeout(2000)

                        # Extract iframe and surrounding context using JavaScript
                        video_info = await page.evaluate("""
                            () => {
                                const iframes = document.querySelectorAll('iframe');
                                const videoData = [];
                                iframes.forEach(iframe => {
                                    const src = iframe.src || iframe.getAttribute('data-src') || '';
                                    const parent = iframe.parentElement;
                                    const parentHtml = parent ? parent.outerHTML.substring(0, 500) : '';
                                    videoData.push({
                                        src: src,
                                        parentHtml: parentHtml
                                    });
                                });
                                return videoData;
                            }
                        """)

                        if video_info:
                            self.logger.info(f"📹 [VIDEO EMBEDS] Found {len(video_info)} iframes")
                            for i, vid in enumerate(video_info[:3]):
                                src_preview = vid['src'][:100] if vid['src'] else 'no-src'
                                self.logger.info(f"   Iframe {i+1}: {src_preview}...")
                                # Check if parent HTML contains loom.com references
                                if 'loom.com' in vid.get('parentHtml', '').lower():
                                    self.logger.info(f"   🎯 Found loom.com reference in parent HTML")

                    except Exception as e:
                        self.logger.info(f"ℹ️ [BROWSER FETCH ASYNC] No iframes detected or timeout: {e}")

                    # Take screenshot for debugging
                    screenshot_path = await self._take_screenshot_async(page, url)
                    self.logger.info(f"📸 [BROWSER FETCH ASYNC] Screenshot saved: {screenshot_path}")

                    # Extract HTML - use evaluate to get the full DOM including all attributes
                    # document.documentElement.outerHTML captures everything including data attributes
                    html_content = await page.evaluate("() => document.documentElement.outerHTML")
                    self.logger.info(f"✅ [HTML EXTRACTION] Extracted {len(html_content)} chars using document.outerHTML")

                    # If we have original HTML with video URLs, prefer that for video detection
                    # (Some sites like GitBook use iframe.ly which replaces URLs after JS runs)
                    if hasattr(page, '_original_html') and page._original_html:
                        self.logger.info(f"✅ [USING ORIGINAL HTML] Using original response HTML (contains video URLs before JS modification)")
                        html_content = page._original_html
                    elif hasattr(page, '_api_responses_with_video') and page._api_responses_with_video:
                        # If video URLs were found in API responses, inject them into the HTML
                        self.logger.info(f"✅ [USING API DATA] Found {len(page._api_responses_with_video)} API responses with video URLs")
                        # Append the API response data to the HTML for video detection
                        for api_resp in page._api_responses_with_video[:3]:
                            html_content += f"\n<!-- API Response Data: {api_resp['text'][:1000]} -->"

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
            except AsyncPlaywrightTimeoutError:
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

    async def _handle_bot_challenges_async(self, page: 'AsyncPage', url: str):
        """
        Detect and handle bot detection challenges (Press & Hold, CAPTCHA, etc.)
        Waits for manual completion if challenge is detected
        """
        try:
            # Check for "Press & Hold" challenges (common on Tegus, etc.)
            press_and_hold_selectors = [
                'text="Press & Hold"',
                'text="press and hold"',
                'text="confirm you are a human"',
                'text="verify you are human"',
            ]

            for selector in press_and_hold_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.is_visible(timeout=2000):
                        self.logger.warning(f"🤖 [BOT CHALLENGE] Detected '{selector}' challenge - waiting for manual completion...")
                        self.logger.warning(f"⏳ [BOT CHALLENGE] Please complete the challenge in the browser window...")

                        # Take screenshot of challenge
                        screenshot_path = await self._take_screenshot_async(page, url)
                        self.logger.info(f"📸 [BOT CHALLENGE] Screenshot saved: {screenshot_path}")

                        # Wait up to 60 seconds for the challenge to disappear
                        for i in range(12):  # 12 * 5 seconds = 60 seconds
                            await page.wait_for_timeout(5000)
                            if not await element.is_visible():
                                self.logger.info(f"✅ [BOT CHALLENGE] Challenge completed after {(i+1)*5} seconds!")
                                return
                            self.logger.info(f"⏳ [BOT CHALLENGE] Still waiting... ({(i+1)*5}s elapsed)")

                        self.logger.warning(f"⚠️ [BOT CHALLENGE] Challenge still present after 60 seconds - continuing anyway...")
                        return
                except Exception:
                    continue

        except Exception as e:
            self.logger.debug(f"Bot challenge detection error (non-fatal): {e}")

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

    # Old Q4-specific login method removed - now using generalized PlaywrightAuthenticator
    # See playwright_auth.py for the new implementation
