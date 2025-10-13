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
        """Load only Substack session cookies from Chrome for fast authentication"""
        try:
            import sqlite3
            import shutil
            import tempfile

            self.logger.info("🍪 [CHROME COOKIES] Loading Substack session cookies from Chrome...")

            # Chrome cookie database path on macOS
            chrome_cookie_db = Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "Default" / "Cookies"

            if not chrome_cookie_db.exists():
                self.logger.warning(f"⚠️ [CHROME COOKIES] Chrome cookie database not found at: {chrome_cookie_db}")
                return

            # Copy database to temp file (Chrome locks the original)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
                tmp_db_path = tmp_file.name

            try:
                shutil.copy2(chrome_cookie_db, tmp_db_path)

                # Connect to copied database
                conn = sqlite3.connect(tmp_db_path)
                cursor = conn.cursor()

                # Query ONLY Substack session cookies (much faster than loading all)
                # Focus on the key authentication cookies: substack.sid, substack.lli, etc.
                query = """
                    SELECT host_key, name, value, path, expires_utc, is_secure, is_httponly
                    FROM cookies
                    WHERE (host_key LIKE '%substack.com%' OR host_key LIKE '%.substack.com%')
                    AND (name LIKE '%sid%' OR name LIKE '%session%' OR name LIKE '%auth%' OR name LIKE '%token%' OR name = 'substack.lli')
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                cookie_count = 0
                cookie_names = []

                for row in rows:
                    host_key, name, value, path, expires_utc, is_secure, is_httponly = row

                    # Convert Chrome's expiry format (microseconds since 1601) to Unix timestamp
                    if expires_utc > 0:
                        # Chrome uses microseconds since Jan 1, 1601
                        expires = (expires_utc / 1000000) - 11644473600
                    else:
                        expires = None

                    # Create cookie
                    cookie = requests.cookies.create_cookie(
                        domain=host_key,
                        name=name,
                        value=value,
                        path=path,
                        secure=bool(is_secure),
                        expires=expires
                    )

                    self.session.cookies.set_cookie(cookie)
                    cookie_count += 1
                    cookie_names.append(name)

                conn.close()

                if cookie_count > 0:
                    self.logger.info(f"✅ [CHROME COOKIES] Loaded {cookie_count} Substack session cookie(s): {', '.join(cookie_names)}")
                else:
                    self.logger.info(f"⚠️ [CHROME COOKIES] No Substack session cookies found - you may need to log in to Substack in Chrome")

            finally:
                # Clean up temp file
                Path(tmp_db_path).unlink(missing_ok=True)

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
            self.logger.info(f"✅ [AUTH SKIP] URL already contains authentication token")
            return False, "url_contains_auth_token"

        self.logger.info(f"🔍 [AUTH CHECK] Testing access to '{platform}' content without authentication...")

        try:
            # Test access without authentication
            response = self.session.get(url, timeout=30)
            soup = BeautifulSoup(response.content, 'html.parser')
            content_length = len(response.text)
            has_structure = bool(soup.find(['article', 'main', 'div']))

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
            self.logger.info(f"✅ [AUTH SKIP] Content is publicly accessible for '{platform}' - no authentication needed")
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