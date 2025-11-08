"""
Generalized Playwright-based authentication helper

This module provides a flexible, configuration-based approach to handling
browser-based authentication for various platforms. It supports:
- Multi-step login flows (e.g., email first, then password)
- Different success detection methods (URL patterns, API responses, DOM elements)
- Custom button text and selectors
- Flexible timing controls
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from playwright.async_api import Page as AsyncPage, Response


@dataclass
class PlaywrightLoginConfig:
    """
    Configuration for Playwright-based authentication

    This dataclass defines all the parameters needed to authenticate with a website
    using Playwright browser automation. It's designed to be flexible and work with
    various authentication flows.
    """

    # Platform identification
    platform_name: str  # e.g., "Q4 Inc", "PocketCasts"

    # Credentials (can be set dynamically)
    email: str
    password: str

    # Initial action (before showing login form)
    initial_button_text: Optional[str] = None  # e.g., "Register with a Q4 Account"
    initial_button_selector: Optional[str] = None  # Alternative to text-based selector

    # Form field selectors
    email_selector: str = 'input[type="email"]'
    password_selector: str = 'input[type="password"]'

    # Login flow configuration
    has_two_step_flow: bool = False  # True for email → Next → password flows
    next_button_text: Optional[str] = "Next"
    next_button_selector: Optional[str] = None

    # Submit button
    submit_button_text: str = "Log in"
    submit_button_selector: Optional[str] = None

    # Success detection (at least one should be provided)
    success_url_contains: Optional[str] = None  # e.g., "events.q4inc.com"
    success_url_excludes: Optional[str] = None  # e.g., "login"
    success_api_pattern: Optional[str] = None  # e.g., "api.pocketcasts.com"
    success_api_response_key: Optional[str] = None  # e.g., "accessToken"
    success_selector: Optional[str] = None  # DOM element that appears on success

    # Timing controls (in milliseconds)
    wait_after_initial_button: int = 5000
    wait_after_next_button: int = 2000
    wait_after_submit: int = 5000
    wait_for_network_idle: bool = True

    # Timeout for success detection
    success_timeout: int = 10000


class PlaywrightAuthenticator:
    """
    Generalized Playwright authentication handler

    This class handles browser-based authentication for any platform that can be
    configured via PlaywrightLoginConfig. It's designed to be reusable across
    different authentication flows.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    async def login(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """
        Perform login using the provided configuration

        Args:
            page: Playwright page object (browser must already be navigated to the login page)
            config: Login configuration

        Returns:
            True if login successful, False otherwise
        """
        try:
            self.logger.info(f"🔐 [{config.platform_name.upper()}] Starting authentication...")

            # Step 1: Click initial button if needed (e.g., "Register with a Q4 Account")
            if config.initial_button_text or config.initial_button_selector:
                if not await self._click_initial_button(page, config):
                    return False

            # Step 2: Fill email
            if not await self._fill_email(page, config):
                return False

            # Step 3: Click "Next" if two-step flow
            if config.has_two_step_flow:
                if not await self._click_next_button(page, config):
                    return False

            # Step 4: Fill password
            if not await self._fill_password(page, config):
                return False

            # Step 5: Set up success detection before clicking submit
            success_detected = asyncio.Event()
            success_result = {'success': False, 'method': None}

            # Set up API response monitoring if configured
            if config.success_api_pattern and config.success_api_response_key:
                async def check_api_response(response: Response):
                    if config.success_api_pattern in response.url:
                        self.logger.info(f"🔍 [{config.platform_name.upper()}] API call detected: {response.url}")
                        try:
                            if response.status == 200:
                                json_data = await response.json()
                                if isinstance(json_data, dict) and config.success_api_response_key in json_data:
                                    self.logger.info(f"✅ [{config.platform_name.upper()}] Success detected via API response")
                                    success_result['success'] = True
                                    success_result['method'] = 'api_response'
                                    success_detected.set()
                        except Exception as e:
                            self.logger.debug(f"Error parsing API response: {e}")

                page.on("response", check_api_response)

            # Step 6: Click submit button
            if not await self._click_submit_button(page, config):
                return False

            # Step 7: Wait for login to complete
            await page.wait_for_timeout(config.wait_after_submit)
            if config.wait_for_network_idle:
                await page.wait_for_load_state('networkidle')

            # Step 8: Check for success
            if success_result['success']:
                self.logger.info(f"✅ [{config.platform_name.upper()}] Login successful (via {success_result['method']})")
                return True

            # Check URL-based success
            if config.success_url_contains or config.success_url_excludes:
                url_success = await self._check_url_success(page, config)
                if url_success:
                    return True

            # Check DOM-based success
            if config.success_selector:
                dom_success = await self._check_dom_success(page, config)
                if dom_success:
                    return True

            self.logger.error(f"❌ [{config.platform_name.upper()}] Login failed - no success indicators found")
            self.logger.error(f"   Current URL: {page.url}")
            return False

        except Exception as e:
            self.logger.error(f"❌ [{config.platform_name.upper()}] Login error: {e}")
            return False

    async def _click_initial_button(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """Click initial button (e.g., 'Register with a Q4 Account')"""
        try:
            self.logger.info(f"🔘 [{config.platform_name.upper()}] Looking for initial button...")

            if config.initial_button_selector:
                button = page.locator(config.initial_button_selector)
            else:
                button = page.locator(f'button:has-text("{config.initial_button_text}")')

            if await button.count() > 0:
                await button.click()
                self.logger.info(f"✅ [{config.platform_name.upper()}] Clicked initial button")
                await page.wait_for_timeout(config.wait_after_initial_button)
                if config.wait_for_network_idle:
                    await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)  # Extra wait for stability
                return True
            else:
                self.logger.warning(f"⚠️ [{config.platform_name.upper()}] Initial button not found, continuing anyway...")
                return True  # Not finding it might mean we're already on the login page

        except Exception as e:
            self.logger.error(f"❌ [{config.platform_name.upper()}] Error clicking initial button: {e}")
            return False

    async def _fill_email(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """Fill email field"""
        try:
            self.logger.info(f"📝 [{config.platform_name.upper()}] Entering email...")
            email_input = page.locator(config.email_selector).first

            if await email_input.count() > 0:
                await email_input.fill(config.email)
                return True
            else:
                self.logger.error(f"❌ [{config.platform_name.upper()}] Email field not found")
                return False

        except Exception as e:
            self.logger.error(f"❌ [{config.platform_name.upper()}] Error filling email: {e}")
            return False

    async def _click_next_button(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """Click 'Next' button in two-step flows"""
        try:
            self.logger.info(f"🔘 [{config.platform_name.upper()}] Clicking Next button...")

            if config.next_button_selector:
                button = page.locator(config.next_button_selector)
            else:
                button = page.locator(f'button:has-text("{config.next_button_text}")')

            if await button.count() > 0:
                await button.click()
                self.logger.info(f"✅ [{config.platform_name.upper()}] Clicked Next button")
                await page.wait_for_timeout(config.wait_after_next_button)
                return True
            else:
                self.logger.error(f"❌ [{config.platform_name.upper()}] Next button not found")
                return False

        except Exception as e:
            self.logger.error(f"❌ [{config.platform_name.upper()}] Error clicking Next button: {e}")
            return False

    async def _fill_password(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """Fill password field"""
        try:
            self.logger.info(f"📝 [{config.platform_name.upper()}] Entering password...")
            password_input = page.locator(config.password_selector).first

            if await password_input.count() > 0:
                await password_input.fill(config.password)
                return True
            else:
                self.logger.error(f"❌ [{config.platform_name.upper()}] Password field not found")
                return False

        except Exception as e:
            self.logger.error(f"❌ [{config.platform_name.upper()}] Error filling password: {e}")
            return False

    async def _click_submit_button(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """Click submit/login button"""
        try:
            self.logger.info(f"🔘 [{config.platform_name.upper()}] Clicking submit button...")

            if config.submit_button_selector:
                button = page.locator(config.submit_button_selector)
            else:
                button = page.locator(f'button:has-text("{config.submit_button_text}")').first

            if await button.count() > 0:
                await button.click()
                self.logger.info(f"✅ [{config.platform_name.upper()}] Clicked submit button")
                return True
            else:
                self.logger.error(f"❌ [{config.platform_name.upper()}] Submit button not found")
                return False

        except Exception as e:
            self.logger.error(f"❌ [{config.platform_name.upper()}] Error clicking submit button: {e}")
            return False

    async def _check_url_success(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """Check if URL indicates successful login"""
        current_url = page.url

        # Check if URL contains expected pattern
        if config.success_url_contains and config.success_url_contains not in current_url:
            return False

        # Check if URL excludes unwanted pattern
        if config.success_url_excludes and config.success_url_excludes in current_url.lower():
            return False

        self.logger.info(f"✅ [{config.platform_name.upper()}] Login successful (via URL check)")
        self.logger.info(f"   URL: {current_url}")
        return True

    async def _check_dom_success(self, page: AsyncPage, config: PlaywrightLoginConfig) -> bool:
        """Check if DOM element indicates successful login"""
        try:
            element = page.locator(config.success_selector)
            if await element.count() > 0:
                self.logger.info(f"✅ [{config.platform_name.upper()}] Login successful (via DOM check)")
                return True
            return False
        except Exception:
            return False


# Pre-configured authentication helpers for common platforms

def get_q4_config(email: str, password: str) -> PlaywrightLoginConfig:
    """Get Q4 Inc authentication configuration"""
    return PlaywrightLoginConfig(
        platform_name="Q4 Inc",
        email=email,
        password=password,
        initial_button_text="Register with a Q4 Account",
        has_two_step_flow=True,
        next_button_text="Next",
        submit_button_text="Log in",
        success_url_contains="events.q4inc.com",
        success_url_excludes="login",
        wait_after_initial_button=5000,
        wait_after_next_button=2000,
        wait_after_submit=5000,
    )


def get_pocketcasts_config(email: str, password: str) -> PlaywrightLoginConfig:
    """Get PocketCasts authentication configuration"""
    return PlaywrightLoginConfig(
        platform_name="PocketCasts",
        email=email,
        password=password,
        has_two_step_flow=False,  # Email and password on same page
        submit_button_text="Log in",  # PocketCasts uses "Log in"
        submit_button_selector='button:has-text("Log in"), button[type="submit"]',  # Fallback selector
        success_api_pattern="api.pocketcasts.com",
        success_api_response_key="accessToken",
        success_url_excludes="login",  # Should not be on login page after success
        wait_after_submit=3000,
    )


# Example of how to add new platforms in the future:
#
# def get_medium_config(email: str, password: str) -> PlaywrightLoginConfig:
#     """Get Medium authentication configuration"""
#     return PlaywrightLoginConfig(
#         platform_name="Medium",
#         email=email,
#         password=password,
#         initial_button_text="Sign in with email",
#         has_two_step_flow=False,
#         submit_button_text="Continue",
#         success_selector="div[data-test-id='user-menu']",  # User menu appears when logged in
#     )
