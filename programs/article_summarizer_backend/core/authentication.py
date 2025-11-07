"""
Authentication Module - Railway Version

Handles authentication for various platforms and content sources.
Uses Playwright browser sessions stored in Supabase database for Railway deployment.
"""

import os
import logging
import json
import requests
from pathlib import Path
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

logger = logging.getLogger(__name__)

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

        # Store full storage_state for Playwright (includes cookies + localStorage + sessionStorage)
        self.storage_state = None

        # Load cookies from Playwright storage state (Railway)
        self._load_storage_state_cookies()

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

    def _load_storage_state_from_supabase(self) -> Optional[Dict]:
        """
        Load browser session storage_state from Supabase database

        Returns:
            Storage state dict if found, None otherwise
        """
        if not SUPABASE_AVAILABLE:
            self.logger.debug("Supabase library not available")
            return None

        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

            if not supabase_url or not supabase_key:
                self.logger.debug("Supabase credentials not configured")
                return None

            self.logger.info("🔍 [SUPABASE] Loading browser session from Supabase...")

            # Initialize Supabase client
            supabase: Client = create_client(supabase_url, supabase_key)

            # Query for active browser session (platform='all')
            result = supabase.table('browser_sessions')\
                .select('*')\
                .eq('platform', 'all')\
                .eq('is_active', True)\
                .order('updated_at', desc=True)\
                .limit(1)\
                .execute()

            if result.data and len(result.data) > 0:
                session_data = result.data[0]
                storage_state = session_data['storage_state']

                self.logger.info(f"✅ [SUPABASE] Loaded browser session from Supabase")
                self.logger.info(f"   Session ID: {session_data['id']}")
                self.logger.info(f"   Updated: {session_data['updated_at']}")
                self.logger.info(f"   Cookies: {len(storage_state.get('cookies', []))}")

                return storage_state
            else:
                self.logger.warning("⚠️ [SUPABASE] No active browser session found in database")
                return None

        except Exception as e:
            self.logger.warning(f"⚠️ [SUPABASE] Error loading session from database: {e}")
            return None

    def _load_storage_state_cookies(self):
        """
        Load authentication cookies from Supabase browser_sessions table

        This replaces Chrome cookie extraction for Railway deployment.
        Cookies are loaded from Supabase database instead of file storage.
        """
        try:
            # First try to load from Supabase
            storage_state = self._load_storage_state_from_supabase()

            # Fallback to file-based storage if Supabase fails
            if not storage_state:
                self.logger.info(f"🔄 [STORAGE STATE] Falling back to file-based storage...")
                storage_dir = os.getenv('STORAGE_DIR', '/app/storage')
                storage_state_file = Path(storage_dir) / 'storage_state.json'

                if not storage_state_file.exists():
                    self.logger.warning(f"⚠️ [STORAGE STATE] No browser session found")
                    self.logger.warning("   Upload session to Supabase using: python scripts/upload_session_to_supabase.py")
                    return

                self.logger.info(f"🍪 [STORAGE STATE] Loading authentication cookies from {storage_state_file}...")

                # Load storage state from file
                with open(storage_state_file, 'r') as f:
                    storage_state = json.load(f)

            # Store full storage_state for later use with Playwright
            self.storage_state = storage_state

            cookies = storage_state.get('cookies', [])
            cookie_count = 0
            cookies_by_domain = {}

            # Load cookies into session
            for cookie_data in cookies:
                try:
                    # Create cookie for the session
                    cookie = requests.cookies.create_cookie(
                        domain=cookie_data.get('domain', ''),
                        name=cookie_data.get('name', ''),
                        value=cookie_data.get('value', ''),
                        path=cookie_data.get('path', '/'),
                        secure=cookie_data.get('secure', True),
                        expires=cookie_data.get('expires'),
                    )

                    self.session.cookies.set_cookie(cookie)
                    cookie_count += 1

                    # Track cookies by domain for logging
                    domain = cookie_data.get('domain', '').lstrip('.')
                    domain_key = domain.split('.')[-2] if '.' in domain else domain
                    if domain_key not in cookies_by_domain:
                        cookies_by_domain[domain_key] = []
                    cookies_by_domain[domain_key].append(cookie_data.get('name', ''))

                except Exception as e:
                    self.logger.debug(f"Could not load cookie: {e}")
                    continue

            if cookie_count > 0:
                domains_summary = ', '.join([f"{domain} ({len(cookies)})" for domain, cookies in cookies_by_domain.items()])
                self.logger.info(f"✅ [STORAGE STATE] Loaded {cookie_count} authentication cookie(s) from: {domains_summary}")
            else:
                self.logger.warning(f"⚠️ [STORAGE STATE] No cookies found in storage state")

        except Exception as e:
            self.logger.warning(f"⚠️ [STORAGE STATE] Could not load browser session: {e}")
            self.logger.warning("   Will fall back to Playwright browser fetching if needed")

    def load_cookies_for_url(self, url: str) -> bool:
        """
        Load cookies for a specific URL from storage state

        This is useful for sites like Substack newsletters where each subdomain
        (e.g., lennysnewsletter.com) has its own cookies.

        Args:
            url: The URL to load cookies for

        Returns:
            True if cookies were loaded successfully (always returns True on Railway since
            cookies are already loaded from storage_state.json)
        """
        # On Railway, cookies are already loaded from storage_state.json on init
        # No need to load additional cookies per-URL
        # This method is kept for compatibility with existing code
        return True

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

    async def fetch_with_browser_async(self, url: str) -> Tuple[bool, Optional[str], str]:
        """
        Async version of fetch_with_browser for use with FastAPI/async contexts

        Args:
            url: The URL to fetch

        Returns:
            Tuple of (success, html_content, message)
        """
        if not self.browser_fetcher.is_available():
            return False, None, "Playwright not available - install with: pip install playwright && playwright install chromium"

        self.logger.info(f"🌐 [BROWSER AUTH ASYNC] Using Playwright to fetch: {url}")

        # Fetch using async Playwright with full storage_state (preferred) or fallback to cookies
        if self.storage_state:
            self.logger.info(f"🌐 [BROWSER AUTH ASYNC] Using storage_state (cookies + localStorage + sessionStorage)")
            success, html_content, message = await self.browser_fetcher.fetch_with_playwright_async(
                url,
                storage_state=self.storage_state
            )
        else:
            self.logger.info(f"🌐 [BROWSER AUTH ASYNC] Using session cookies only")
            success, html_content, message = await self.browser_fetcher.fetch_with_playwright_async(
                url,
                cookies=self.session.cookies
            )

        if success:
            self.logger.info(f"✅ [BROWSER AUTH ASYNC] Successfully fetched content via browser")
        else:
            self.logger.error(f"❌ [BROWSER AUTH ASYNC] Browser fetch failed: {message}")

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