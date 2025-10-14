#!/usr/bin/env python3
"""
Spotify OAuth 2.0 authentication handler for podcast tracking
Uses Authorization Code Flow with PKCE for CLI applications
"""

import os
import sys
import json
import base64
import hashlib
import secrets
import logging
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests


class SpotifyAuth:
    """Handle Spotify OAuth 2.0 authentication with token refresh"""

    # Spotify API endpoints
    AUTH_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"

    # Required scopes for podcast tracking
    SCOPES = [
        "user-read-recently-played",
        "user-library-read"  # For accessing saved episodes/shows
    ]

    def __init__(self, base_dir: Path, logger: logging.Logger = None):
        self.base_dir = base_dir
        self.logger = logger or logging.getLogger(__name__)

        # Load credentials from environment
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback')

        # Token storage
        self.token_file = base_dir / "programs" / "check_new_posts" / "output" / ".spotify_tokens.json"

        # Current tokens
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

        # Load existing tokens if available
        self._load_tokens()

    def _load_tokens(self):
        """Load tokens from storage file"""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)

                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')

                expires_at_str = data.get('expires_at')
                if expires_at_str:
                    self.token_expires_at = datetime.fromisoformat(expires_at_str)

                self.logger.info("✅ Loaded Spotify tokens from storage")
            except Exception as e:
                self.logger.warning(f"⚠️ Error loading tokens: {e}")

    def _save_tokens(self):
        """Save tokens to storage file"""
        try:
            data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
                'updated_at': datetime.now().isoformat()
            }

            # Ensure directory exists
            self.token_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.token_file, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info("💾 Saved Spotify tokens to storage")
        except Exception as e:
            self.logger.error(f"❌ Error saving tokens: {e}")

    def _generate_pkce_pair(self):
        """Generate PKCE code verifier and challenge"""
        # Generate code verifier (43-128 characters)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.replace('=', '')

        # Generate code challenge
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').replace('=', '')

        return code_verifier, code_challenge

    def _start_callback_server(self, code_verifier: str) -> str:
        """Start local server to receive OAuth callback"""
        auth_code = None

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                nonlocal auth_code

                # Parse query parameters
                query = parse_qs(handler_self.path.split('?')[1] if '?' in handler_self.path else '')

                if 'code' in query:
                    auth_code = query['code'][0]

                    # Send success response
                    handler_self.send_response(200)
                    handler_self.send_header('Content-type', 'text/html')
                    handler_self.end_headers()
                    handler_self.wfile.write(b"""
                        <html>
                        <body>
                        <h1>Success!</h1>
                        <p>You can close this window and return to the terminal.</p>
                        </body>
                        </html>
                    """)
                else:
                    # Handle error
                    handler_self.send_response(400)
                    handler_self.send_header('Content-type', 'text/html')
                    handler_self.end_headers()
                    handler_self.wfile.write(b"""
                        <html>
                        <body>
                        <h1>Error</h1>
                        <p>Authorization failed. Please try again.</p>
                        </body>
                        </html>
                    """)

            def log_message(self, format, *args):
                # Suppress server logs
                pass

        # Extract port from redirect_uri
        port = int(self.redirect_uri.split(':')[-1].split('/')[0])

        # Start server
        server = HTTPServer(('localhost', port), CallbackHandler)

        self.logger.info(f"🌐 Started callback server on port {port}")

        # Handle single request
        server.handle_request()

        return auth_code

    def authenticate(self) -> bool:
        """
        Perform full OAuth flow to get access token

        Returns:
            True if authentication successful, False otherwise
        """
        if not self.client_id or not self.client_secret:
            self.logger.error("❌ Spotify credentials not found in environment")
            self.logger.error("   Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env.local")
            return False

        self.logger.info("🔐 Starting Spotify OAuth authentication...")

        # Generate PKCE pair
        code_verifier, code_challenge = self._generate_pkce_pair()

        # Build authorization URL
        auth_params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(self.SCOPES),
            'code_challenge_method': 'S256',
            'code_challenge': code_challenge
        }

        auth_url = f"{self.AUTH_URL}?{urlencode(auth_params)}"

        self.logger.info("🌐 Opening browser for Spotify authorization...")
        self.logger.info(f"   URL: {auth_url}")

        # Open browser
        webbrowser.open(auth_url)

        # Start callback server to receive code
        auth_code = self._start_callback_server(code_verifier)

        if not auth_code:
            self.logger.error("❌ Failed to receive authorization code")
            return False

        self.logger.info("✅ Received authorization code")

        # Exchange code for tokens
        return self._exchange_code_for_tokens(auth_code, code_verifier)

    def _exchange_code_for_tokens(self, auth_code: str, code_verifier: str) -> bool:
        """Exchange authorization code for access and refresh tokens"""
        self.logger.info("🔄 Exchanging authorization code for tokens...")

        token_data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code_verifier': code_verifier
        }

        try:
            response = requests.post(self.TOKEN_URL, data=token_data)
            response.raise_for_status()

            data = response.json()

            self.access_token = data.get('access_token')
            self.refresh_token = data.get('refresh_token')

            # Calculate expiration time
            expires_in = data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            # Save tokens
            self._save_tokens()

            self.logger.info("✅ Successfully obtained access token")
            self.logger.info(f"   Token expires at: {self.token_expires_at.strftime('%Y-%m-%d %H:%M:%S')}")

            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to exchange code for tokens: {e}")
            return False

    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            self.logger.warning("⚠️ No refresh token available, need to authenticate")
            return self.authenticate()

        self.logger.info("🔄 Refreshing access token...")

        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        try:
            response = requests.post(self.TOKEN_URL, data=token_data)
            response.raise_for_status()

            data = response.json()

            self.access_token = data.get('access_token')

            # Update refresh token if provided
            if 'refresh_token' in data:
                self.refresh_token = data['refresh_token']

            # Calculate expiration time
            expires_in = data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            # Save tokens
            self._save_tokens()

            self.logger.info("✅ Successfully refreshed access token")

            return True

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Failed to refresh token: {e}")
            self.logger.warning("   Will attempt full re-authentication")
            return self.authenticate()

    def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary

        Returns:
            Valid access token or None if authentication fails
        """
        # Check if we have a token
        if not self.access_token:
            self.logger.info("🔐 No access token found, starting authentication...")
            if not self.authenticate():
                return None
            return self.access_token

        # Check if token is expired or about to expire (within 5 minutes)
        if self.token_expires_at:
            time_until_expiry = self.token_expires_at - datetime.now()
            if time_until_expiry.total_seconds() < 300:  # 5 minutes
                self.logger.info("⏰ Access token expired or expiring soon, refreshing...")
                if not self.refresh_access_token():
                    return None

        return self.access_token

    def is_authenticated(self) -> bool:
        """Check if we have valid credentials"""
        return self.get_valid_token() is not None
