#!/usr/bin/env python3
"""
Base classes and shared functionality for check_new_posts program
"""

import os
import sys
import logging
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv


class BaseProcessor:
    """Base class for all processors with shared functionality"""

    def __init__(self, session_name="base"):
        self.session_name = session_name
        self.base_dir = self._find_project_root()

        # Setup standard directories for this program
        self.logs_dir = self.base_dir / "programs" / "check_new_posts" / "logs"
        self.output_dir = self.base_dir / "programs" / "check_new_posts" / "output"

        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Load environment variables
        self._load_environment()

        # Setup logging
        self.logger = self._setup_logging()

        # Setup HTTP session
        self.session = self._create_session()

        # Log initialization
        self.logger.info("=" * 80)
        self.logger.info(f"{session_name.upper()} SESSION STARTED")
        self.logger.info(f"Session Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Base Directory: {self.base_dir}")
        self.logger.info("=" * 80)

    def _find_project_root(self):
        """Find the project root by looking for characteristic files"""
        current_dir = Path(__file__).parent
        while current_dir != current_dir.parent:
            if (current_dir / '.git').exists() or (current_dir / 'CLAUDE.md').exists():
                return current_dir
            current_dir = current_dir.parent

        # Fallback: assume we're in programs/check_new_posts/common/
        return Path(__file__).parent.parent.parent.parent

    def _load_environment(self):
        """Load environment variables from .env files"""
        # Prioritize .env.local over .env
        env_local = self.base_dir / '.env.local'
        env_default = self.base_dir / '.env'

        if env_local.exists():
            load_dotenv(env_local)
        elif env_default.exists():
            load_dotenv(env_default)

    def _setup_logging(self):
        """Setup logging to both console and file with rotation"""
        log_file = self.logs_dir / f"{self.session_name}.log"

        # Rotate log if it's too large (2MB limit - keeps ~few days)
        self._rotate_log_if_needed(log_file, max_size_mb=2)

        logger = logging.getLogger(f'{self.session_name}_logger')
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        # File handler with detailed formatting
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            f'%(asctime)s - [{self.session_name.upper()}] - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler with simple formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def _rotate_log_if_needed(self, log_file, max_size_mb=10):
        """Rotate log file if it exceeds the maximum size"""
        if not log_file.exists():
            return

        # Check file size in MB
        file_size_mb = log_file.stat().st_size / (1024 * 1024)

        if file_size_mb > max_size_mb:
            # Read last 25% of the file to preserve recent logs
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Keep the last 25% of lines
            keep_lines = int(len(lines) * 0.25)
            if keep_lines < 100:  # Always keep at least 100 lines
                keep_lines = min(100, len(lines))

            recent_lines = lines[-keep_lines:] if keep_lines > 0 else []

            # Write truncated content back
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"# Log rotated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - keeping last {keep_lines} entries\n")
                f.writelines(recent_lines)

            print(f"📋 Log rotated: kept last {keep_lines} entries (was {file_size_mb:.1f}MB)")

    def _create_session(self):
        """Create and configure HTTP session with authentication"""
        session = requests.Session()

        # Set default headers
        user_agent = os.getenv(
            'USER_AGENT',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )

        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        # Add session cookies if provided
        session_cookies = os.getenv('NEWSLETTER_SESSION_COOKIES')
        if session_cookies:
            try:
                # Parse cookies from environment variable
                for cookie in session_cookies.split(';'):
                    if '=' in cookie:
                        name, value = cookie.strip().split('=', 1)
                        session.cookies.set(name.strip(), value.strip())
                self.logger.info("✅ Session cookies loaded from environment")
            except Exception as e:
                self.logger.warning(f"⚠️ Error loading session cookies: {e}")

        return session

    def safe_request(self, url, method='GET', timeout=30, retries=3, **kwargs):
        """Make HTTP request with retry logic and error handling"""
        for attempt in range(retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, timeout=timeout, **kwargs)
                elif method.upper() == 'POST':
                    response = self.session.post(url, timeout=timeout, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"⚠️ Request attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    raise

        return None

    def log_session_summary(self, **stats):
        """Log a standardized session summary"""
        self.logger.info("=" * 80)
        self.logger.info("📊 SESSION SUMMARY")
        self.logger.info("=" * 80)

        for key, value in stats.items():
            formatted_key = key.replace('_', ' ').title()
            self.logger.info(f"{formatted_key}: {value}")

        self.logger.info(f"🕐 Session completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80)
