"""
Authentication Module

Handles authentication for various platforms and content sources.
Supports both Chrome session cookies and credential-based authentication.
"""

import logging
import json
import requests
from pathlib import Path
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Try to import browser_cookie3 for Chrome cookie extraction
try:
    import browser_cookie3
    CHROME_COOKIES_AVAILABLE = True
except ImportError:
    CHROME_COOKIES_AVAILABLE = False
    logger.warning("browser_cookie3 not available - Chrome cookie extraction disabled")

class AuthenticationManager:
    """Manages authentication for different platforms"""

    def __init__(self, base_dir: Path, session: requests.Session):
        self.base_dir = base_dir
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.credentials = self._load_credentials()

        # Initialize browser fetcher for complex authentication
        from .browser_fetcher import BrowserFetcher
        self.browser_fetcher = BrowserFetcher(self.logger)

        # Load Chrome cookies into session
        self._load_chrome_cookies()

    def _load_credentials(self) -> Dict:
        """Load credentials from environment and credential files"""
        credentials = {}

        # Load from credential files
        cred_files = [
            self.base_dir / '.env.local',
            self.base_dir / '.env',
            self.base_dir / 'programs' / 'video_summarizer' / 'config' / 'credentials.json'
        ]

        for cred_file in cred_files:
            if cred_file.exists():
                try:
                    if cred_file.suffix == '.json':
                        with open(cred_file, 'r') as f:
                            file_creds = json.load(f)
                            credentials.update(file_creds)
                    else:
                        # Handle .env files
                        with open(cred_file, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#') and '=' in line:
                                    key, value = line.split('=', 1)
                                    credentials[key.strip()] = value.strip().strip('"\'')
                except Exception as e:
                    self.logger.warning(f"Could not load credentials from {cred_file}: {e}")

        return credentials

    def _load_chrome_cookies(self):
        """Load authentication session cookies from Chrome for common content platforms"""
        try:
            from pycookiecheat import chrome_cookies
            import urllib.parse

            self.logger.info("🍪 [CHROME COOKIES] Loading authentication cookies from Chrome...")

            # List of domains to extract cookies from
            domains = [
                'seekingalpha.com',
                '.seekingalpha.com',
                'substack.com',
                '.substack.com',
                'medium.com',
                '.medium.com',
                'patreon.com',
                '.patreon.com',
                'tegus.com',
                '.tegus.com'
            ]

            cookie_count = 0
            cookies_by_domain = {}

            # Extract cookies for each domain
            for domain in domains:
                try:
                    # Use pycookiecheat to decrypt Chrome cookies
                    url = f"https://{domain.lstrip('.')}"
                    domain_cookies = chrome_cookies(url)

                    if domain_cookies:
                        for name, value in domain_cookies.items():
                            # Create cookie for the session
                            cookie = requests.cookies.create_cookie(
                                domain=domain,
                                name=name,
                                value=value,
                                path='/',
                                secure=True
                            )

                            self.session.cookies.set_cookie(cookie)
                            cookie_count += 1

                            # Track cookies by domain for logging
                            domain_key = domain.split('.')[-2] if '.' in domain else domain
                            if domain_key not in cookies_by_domain:
                                cookies_by_domain[domain_key] = []
                            cookies_by_domain[domain_key].append(name)

                except Exception as e:
                    # Skip domains that have no cookies
                    if "No cookies found" not in str(e):
                        self.logger.debug(f"Could not load cookies for {domain}: {e}")
                    continue

            if cookie_count > 0:
                domains_summary = ', '.join([f"{domain} ({len(cookies)})" for domain, cookies in cookies_by_domain.items()])
                self.logger.info(f"✅ [CHROME COOKIES] Loaded {cookie_count} authentication cookie(s) from: {domains_summary}")
            else:
                self.logger.info(f"⚠️ [CHROME COOKIES] No authentication cookies found - you may need to log in to content sites in Chrome")

        except ImportError:
            self.logger.warning("⚠️ [CHROME COOKIES] pycookiecheat not installed - cannot decrypt Chrome cookies")
            self.logger.warning("   Install with: pip install pycookiecheat")
        except Exception as e:
            self.logger.warning(f"⚠️ [CHROME COOKIES] Could not load Chrome cookies: {e}")
            self.logger.warning("   Will fall back to credential-based authentication if needed")

    def detect_platform(self, url: str) -> str:
        """
        Detect the platform from URL (only for username/password authentication)

        Args:
            url: The URL to analyze

        Returns:
            Platform name (substack, medium, generic, etc.)
        """
        self.logger.info(f"🔍 [PLATFORM DETECTION] Analyzing URL: {url}")

        domain = self._extract_domain(url)
        self.logger.info(f"🔍 [PLATFORM DETECTION] Domain: {domain}")

        # Only detect platforms that need specific username/password authentication
        if any(substack_indicator in domain for substack_indicator in [
            'substack.com', 'newsletter.com', 'lennysnewsletter.com'
        ]):
            platform = 'substack'
        elif 'medium.com' in domain:
            platform = 'medium'
        else:
            platform = 'generic'

        self.logger.info(f"✅ [PLATFORM DETECTION] Detected platform: {platform}")
        return platform

    def check_authentication_required(self, url: str, platform: str) -> Tuple[bool, Optional[str]]:
        """
        Check if authentication is required for the given URL

        Args:
            url: The URL to check
            platform: The detected platform

        Returns:
            Tuple of (auth_required, reason)
        """
        # First check if URL already contains authentication tokens
        if self._has_access_token(url):
            self.logger.info(f"✅ [AUTH STATUS] URL contains authentication token")
            return False, "url_contains_auth_token"

        self.logger.info(f"🔍 [AUTH CHECK] Testing access to '{platform}' content...")

        try:
            # Test access (which includes any loaded Chrome cookies)
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            content_length = len(response.text)
            has_structure = bool(soup.find(['article', 'main', 'div']))

            # Check for logged-in user indicators first
            logged_in_user = self._detect_logged_in_user(soup, response.text)
            if logged_in_user:
                self.logger.info(f"✅ [AUTH STATUS] Already authenticated via browser session as: {logged_in_user}")
                self.logger.info(f"✅ [AUTH STATUS] Content accessible (length: {content_length})")
                return False, f"authenticated_via_session: {logged_in_user}"

            self.logger.info(f"🔓 [CONTENT CHECK] Content appears accessible (length: {content_length}, has structure: {has_structure})")

            # Check for paywall indicators
            paywall_indicators = [
                'subscribe', 'subscription', 'paywall', 'premium', 'members only',
                'subscribers only', 'sign up', 'unlock', 'upgrade'
            ]

            content_text = response.text.lower()
            for indicator in paywall_indicators:
                if indicator in content_text:
                    self.logger.info(f"🔒 [CONTENT CHECK] Found paywall indicator in content: '{indicator}'")
                    self.logger.info(f"🔒 [AUTH CHECK] Content appears to be behind paywall for '{platform}'")
                    return True, f"paywall_detected: {indicator}"

            # If content is accessible, no auth needed
            self.logger.info(f"✅ [AUTH STATUS] Content is publicly accessible for '{platform}'")
            return False, "publicly_accessible"

        except Exception as e:
            self.logger.warning(f"⚠️ [AUTH CHECK] Could not test access: {e}")
            return True, f"access_test_failed: {str(e)}"

    def authenticate_if_needed(self, url: str, platform: str) -> Tuple[bool, str]:
        """
        Authenticate if credentials are available and needed

        Args:
            url: The URL to authenticate for
            platform: The platform name

        Returns:
            Tuple of (success, message)
        """
        # Check if we have credentials for this platform
        platform_credentials = self._get_platform_credentials(platform)

        if not platform_credentials:
            return False, f"No credentials available for platform: {platform}"

        self.logger.info(f"🔑 [CREDENTIALS] Found credentials for '{platform}': {', '.join(platform_credentials.keys())}")
        self.logger.info(f"🔐 [AUTH ATTEMPT] Content not accessible without authentication and credentials available for '{platform}' - attempting authentication")

        # Try authentication based on platform (only for username/password)
        if platform == 'substack':
            return self._authenticate_substack(platform_credentials)
        elif platform == 'medium':
            return self._authenticate_medium(platform_credentials)
        else:
            return self._authenticate_generic(platform_credentials)

    def _detect_logged_in_user(self, soup: BeautifulSoup, html_text: str) -> Optional[str]:
        """
        Detect if user is logged in and extract username/email

        Args:
            soup: BeautifulSoup object
            html_text: Raw HTML text

        Returns:
            Username/email if logged in, None otherwise
        """
        import re

        # Pattern 1: Look for common username/email patterns in data attributes or text
        username_patterns = [
            r'"username":\s*"([^"]+)"',
            r'"email":\s*"([^"@]+@[^"]+)"',
            r'"user":\s*"([^"]+)"',
            r'data-user[^>]*=\s*"([^"]+)"',
            r'data-username[^>]*=\s*"([^"]+)"',
        ]

        for pattern in username_patterns:
            match = re.search(pattern, html_text)
            if match:
                return match.group(1)

        # Pattern 2: Look for account/profile links or buttons
        account_selectors = [
            '[data-testid="account-menu"]',
            '[class*="account"]',
            '[class*="profile"]',
            '[class*="user-menu"]',
            'a[href*="/account"]',
            'a[href*="/profile"]',
        ]

        for selector in account_selectors:
            element = soup.select_one(selector)
            if element:
                # Try to extract username from text or attributes
                text = element.get_text(strip=True)
                if text and len(text) > 2 and len(text) < 50:
                    return text

                # Check data attributes
                for attr in ['data-user', 'data-username', 'data-email', 'title', 'aria-label']:
                    value = element.get(attr)
                    if value and len(value) > 2 and len(value) < 50:
                        return value

        return None

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()

    def _has_access_token(self, url: str) -> bool:
        """
        Check if URL contains any authentication tokens (generic pattern detection)

        Args:
            url: The URL to check

        Returns:
            True if URL contains auth tokens
        """
        from urllib.parse import urlparse, parse_qs

        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # Generic token parameters that indicate authentication
            token_patterns = [
                'access_token', 'token', 'auth_token', 'bearer', 'jwt',
                'auth', 'session', 'key', 'api_key', 'authkey'
            ]

            return any(param in query_params for param in token_patterns)

        except Exception as e:
            self.logger.warning(f"Error checking URL tokens: {e}")
            return False

    def _get_platform_credentials(self, platform: str) -> Dict:
        """Get credentials for a specific platform"""
        platform_creds = {}

        # Look for platform-specific credentials
        for key, value in self.credentials.items():
            if platform.lower() in key.lower():
                platform_creds[key] = value

        # Also include generic credentials
        generic_keys = ['email', 'password', 'username', 'api_key', 'token']
        for key in generic_keys:
            if key in self.credentials:
                platform_creds[key] = self.credentials[key]

        return platform_creds

    def _authenticate_substack(self, credentials: Dict) -> Tuple[bool, str]:
        """Authenticate with Substack"""
        self.logger.info("🔐 [AUTH] Attempting Substack authentication with email/password...")

        try:
            # Substack authentication logic
            login_url = "https://substack.com/api/v1/login"
            auth_data = {
                'email': credentials.get('email', credentials.get('substack_email', credentials.get('SUBSTACK_EMAIL'))),
                'password': credentials.get('password', credentials.get('substack_password', credentials.get('SUBSTACK_PASSWORD'))),
                'captcha_response': None
            }

            response = self.session.post(login_url, json=auth_data, timeout=30)

            if response.status_code == 200:
                self.logger.info("✅ [AUTH SUCCESS] Substack authentication successful")
                return True, "Substack authentication successful"
            else:
                error_msg = f"Status: {response.status_code}, Response: {response.text[:100]}"
                self.logger.error(f"❌ [AUTH FAILED] Substack authentication failed - {error_msg}")
                return False, f"Substack authentication failed - {error_msg}"

        except Exception as e:
            self.logger.error(f"❌ [AUTH ERROR] Substack authentication error: {e}")
            return False, f"Substack authentication error: {str(e)}"

    def _authenticate_medium(self, credentials: Dict) -> Tuple[bool, str]:
        """Authenticate with Medium"""
        # Medium authentication implementation
        return False, "Medium authentication not yet implemented"


    def _authenticate_generic(self, credentials: Dict) -> Tuple[bool, str]:
        """Generic authentication attempt"""
        # Generic authentication implementation
        return False, "Generic authentication not yet implemented"

    def fetch_with_browser(self, url: str) -> Tuple[bool, Optional[str], str]:
        """
        Fetch content using browser automation (Playwright)

        This method is used as a fallback when:
        - Standard requests fail due to anti-bot measures
        - Cloudflare or similar protection is detected
        - JavaScript is required to load content

        Args:
            url: The URL to fetch

        Returns:
            Tuple of (success, html_content, message)
        """
        if not self.browser_fetcher.is_available():
            return False, None, "Playwright not available - install with: pip install playwright && playwright install chromium"

        self.logger.info(f"🌐 [BROWSER AUTH] Using Playwright to fetch: {url}")

        # Convert session cookies to dictionary for Playwright
        cookies_dict = {}
        for cookie in self.session.cookies:
            cookies_dict[cookie.name] = cookie.value

        # Fetch using Playwright with injected cookies
        success, html_content, message = self.browser_fetcher.fetch_with_playwright(url, self.session.cookies)

        if success:
            self.logger.info(f"✅ [BROWSER AUTH] Successfully fetched content via browser")
        else:
            self.logger.error(f"❌ [BROWSER AUTH] Browser fetch failed: {message}")

        return success, html_content, message

    def should_use_browser_fetch(self, url: str, response: Optional[requests.Response] = None) -> bool:
        """
        Determine if browser fetch should be used

        Args:
            url: The URL to check
            response: Optional response from standard request

        Returns:
            True if browser fetch should be used
        """
        return self.browser_fetcher.should_use_browser_fetch(url, response)