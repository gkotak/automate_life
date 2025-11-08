"""
Seeking Alpha Scraper for Earnings Calls

Scrapes earnings call transcripts, audio files, and presentation PDFs from Seeking Alpha.

Usage:
    scraper = SeekingAlphaScraper()
    calls = await scraper.get_latest_earnings_calls("AAPL", num_quarters=4)
"""

import logging
import re
import asyncio
import os
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from pathlib import Path
import sys

# Add shared imports for AuthenticationManager
earnings_insights_dir = Path(__file__).parent.parent
sys.path.insert(0, str(earnings_insights_dir))
from shared import AuthenticationManager

logger = logging.getLogger(__name__)


class SeekingAlphaScraper:
    """
    Scrape earnings call data from Seeking Alpha

    Features:
    - Navigate to company earnings page
    - Extract latest N quarters of earnings calls
    - Get transcript, audio URL, and presentation links
    - Parse quarter/fiscal year from article titles
    - Uses authenticated session from Supabase for access
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # ⭐ Use shared AuthenticationManager for browser sessions
        project_root = Path(__file__).parent.parent.parent.parent
        self.auth_manager = AuthenticationManager(
            base_dir=project_root,
            session=self.session
        )

        # Load storage state from Supabase (queries platform='all' by default)
        # This gives us access to the shared Chrome browser session
        self.storage_state = self.auth_manager._load_storage_state_from_supabase()

        # Note: _load_storage_state_cookies() is called automatically by AuthenticationManager.__init__()
        # It injects cookies from storage_state into self.session for API calls

    async def get_latest_earnings_calls(
        self,
        symbol: str,
        num_quarters: int = 1
    ) -> List[Dict]:
        """
        Get latest N quarters of earnings calls for a symbol

        Args:
            symbol: Stock ticker (e.g., "AAPL")
            num_quarters: Number of quarters to fetch (default 1, max 4)

        Returns:
            List of earnings call dicts with transcript, audio_url, etc.
        """
        # Cap at 4 quarters maximum
        if num_quarters > 4:
            self.logger.warning(f"⚠️ Requested {num_quarters} quarters, capping at 4")
            num_quarters = 4

        self.logger.info(f"🔍 [SEEKING ALPHA] Fetching {num_quarters} earnings call{'s' if num_quarters > 1 else ''} for {symbol}")

        # Import Playwright here to avoid import errors if not installed
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            self.logger.error("❌ Playwright not installed. Install: pip install playwright && playwright install chromium")
            return []

        earnings_calls = []

        try:
            async with async_playwright() as p:
                # Launch browser with stealth settings to avoid bot detection
                # Use headless=False for debugging, change to True for production
                headless = os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
                browser = await p.chromium.launch(
                    headless=headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',  # Hide webdriver flag
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                    ]
                )

                # Create context with storage state (authentication) and stealth settings
                context_options = {
                    'viewport': {'width': 1920, 'height': 1080},
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    'locale': 'en-US',
                    'timezone_id': 'America/New_York',
                }

                if self.storage_state:
                    context_options['storage_state'] = self.storage_state
                    self.logger.info("✅ Using authenticated browser session with stealth mode")
                else:
                    self.logger.info("ℹ️ Using unauthenticated browser session with stealth mode")

                context = await browser.new_context(**context_options)

                # Add stealth scripts to hide automation
                page = await context.new_page()

                # Override navigator.webdriver
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """)

                # First navigate to homepage to establish session
                self.logger.info("   🏠 Loading homepage first to establish session...")
                await page.goto("https://seekingalpha.com/", wait_until='networkidle')
                await asyncio.sleep(3)

                # Add some human-like mouse movement
                await page.mouse.move(100, 200)
                await asyncio.sleep(0.5)
                await page.mouse.move(300, 400)

                # Navigate to symbol earnings page
                earnings_url = f"https://seekingalpha.com/symbol/{symbol}/earnings"
                self.logger.info(f"   📄 Navigating to: {earnings_url}")
                await page.goto(earnings_url, wait_until='networkidle')

                # Wait for CAPTCHA/bot detection to complete
                # Give it plenty of time - Sometimes the CAPTCHA solves itself
                self.logger.info("   ⏳ Waiting 15 seconds for page to fully load and CAPTCHA to resolve...")
                self.logger.warning("   ⚠️  DO NOT CLOSE THE BROWSER WINDOW - let it load completely")
                await asyncio.sleep(15)

                # Check if page is still valid
                try:
                    if page.is_closed():
                        self.logger.error("   ❌ Browser window was closed!")
                        await context.close()
                        await browser.close()
                        return earnings_calls
                except:
                    pass

                # Scroll down to see the earnings history section
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
                await asyncio.sleep(3)

                # Find the Earnings History section specifically
                self.logger.info("   🔍 Locating Earnings History section...")

                # Look for the earnings history heading or section
                earnings_history_section = None
                possible_selectors = [
                    'h2:has-text("Earnings History")',
                    'h3:has-text("Earnings History")',
                    '[class*="earnings-history"]',
                    '[id*="earnings-history"]',
                ]

                for selector in possible_selectors:
                    try:
                        heading = await page.query_selector(selector)
                        if heading:
                            # Get the parent container that holds the table
                            earnings_history_section = await heading.evaluate_handle(
                                'el => el.closest("section") || el.parentElement.parentElement'
                            )
                            self.logger.info(f"      ✅ Found Earnings History section using selector: {selector}")
                            break
                    except:
                        pass

                # If we can't find the section, use the whole page as fallback
                if not earnings_history_section:
                    self.logger.warning("      ⚠️ Could not locate Earnings History section, searching whole page")
                    earnings_history_section = page

                # Look for transcript buttons/links within the Earnings History section only
                self.logger.info("   🔍 Searching for Transcript buttons in Earnings History...")

                # Find all "Transcript" buttons/links within the section
                if hasattr(earnings_history_section, 'query_selector_all'):
                    all_transcript_elements = await earnings_history_section.query_selector_all(
                        'button:has-text("Transcript"), a:has-text("Transcript")'
                    )
                else:
                    all_transcript_elements = await page.query_selector_all(
                        'button:has-text("Transcript"), a:has-text("Transcript")'
                    )

                # Filter to only article links/buttons (not listing pages)
                visible_transcripts = []
                seen_hrefs = set()

                for element in all_transcript_elements:
                    try:
                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue

                        # Get href (for links) or data attribute (for buttons)
                        href = await element.get_attribute('href')

                        # If it's a button, we'll click it later and it will navigate
                        # For now, just collect all visible transcript elements
                        if not href:
                            # It's a button - store it directly
                            visible_transcripts.append(element)
                            self.logger.info(f"      Found transcript button (will click to navigate)")
                            continue

                        # Must be an article link (not a listing page)
                        if '/article/' not in href:
                            continue

                        # Deduplicate
                        if href in seen_hrefs:
                            continue

                        seen_hrefs.add(href)
                        visible_transcripts.append(element)
                        self.logger.info(f"      Found transcript link: {href}")

                    except Exception as e:
                        self.logger.debug(f"      Error checking element: {e}")
                        pass

                self.logger.info(f"   ✅ Found {len(visible_transcripts)} transcript elements in Earnings History")

                if len(visible_transcripts) == 0:
                    self.logger.warning(f"   ⚠️ No visible transcript links found for {symbol}")
                    await context.close()
                    await browser.close()
                    return earnings_calls

                # Process each transcript (up to num_quarters)
                # Use the already-found transcript links - no need to re-query on first iteration
                for i in range(min(num_quarters, len(visible_transcripts))):
                    try:
                        # Only re-query if we're going back to the earnings page (i > 0)
                        if i > 0:
                            await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
                            await asyncio.sleep(1)

                            # Re-find transcript buttons/links with same filtering logic
                            all_elements = await page.query_selector_all('button:has-text("Transcript"), a:has-text("Transcript")')
                            visible_transcripts = []
                            for elem in all_elements:
                                try:
                                    if not await elem.is_visible():
                                        continue
                                    href = await elem.get_attribute('href')
                                    # Accept buttons (no href) or article links
                                    if not href or '/article/' in href:
                                        visible_transcripts.append(elem)
                                except:
                                    pass

                        if i >= len(visible_transcripts):
                            break

                        element = visible_transcripts[i]

                        # Check if it's a button or link
                        href = await element.get_attribute('href')

                        if href:
                            # It's a link - navigate directly
                            if href.startswith('/'):
                                transcript_url = f"https://seekingalpha.com{href}"
                            else:
                                transcript_url = href
                        else:
                            # It's a button - click it and wait for navigation
                            self.logger.info(f"   🖱️  Clicking Transcript button...")
                            async with page.expect_navigation(wait_until='networkidle', timeout=30000):
                                await element.click()
                            transcript_url = page.url

                        # Get period info from the table row
                        # Look for the quarter text in the same row as the Transcript button/link
                        parent_row = await element.evaluate_handle('''el => {
                            let row = el.closest("tr");
                            if (!row) row = el.closest("[class*='period']");
                            if (!row) row = el.parentElement;
                            return row;
                        }''')

                        # Try to extract quarter from the row's first cell or period label
                        period_text = ""
                        try:
                            # Get first cell in row which usually has the period (Q4 2024, etc.)
                            first_cell = await parent_row.query_selector('td:first-child, [class*="period"]')
                            if first_cell:
                                period_text = await first_cell.inner_text()
                        except:
                            pass

                        self.logger.info(f"   📄 Transcript {i+1}: Period='{period_text}' URL={transcript_url}")

                        # Navigate to transcript page
                        await page.goto(transcript_url, wait_until='networkidle')
                        await asyncio.sleep(2)  # Let transcript page load

                        # Get current URL and title
                        article_url = page.url
                        article_title = await page.title()

                        self.logger.info(f"      Article title: {article_title}")

                        # Try to parse quarter from multiple sources
                        quarter_info = None

                        # 1. Try period text from table
                        if period_text:
                            quarter_info = self._parse_quarter_from_title(period_text)

                        # 2. Try article title
                        if not quarter_info:
                            quarter_info = self._parse_quarter_from_title(article_title)

                        # 3. Try article URL
                        if not quarter_info and 'q' in article_url.lower():
                            quarter_info = self._parse_quarter_from_title(article_url)
                        if not quarter_info:
                            self.logger.warning(f"      ⚠️ Could not parse quarter from title")
                            await page.goto(earnings_url, wait_until='networkidle')
                            await asyncio.sleep(2)
                            continue

                        # Extract article ID for audio URL
                        article_id = self._extract_article_id(article_url)

                        # Extract call date from article
                        article_date = await self._extract_call_date(page)

                        # Get transcript and audio
                        call_data = await self._extract_call_data_from_page(
                            page,
                            article_url,
                            article_id,
                            symbol,
                            quarter_info,
                            article_date
                        )

                        if call_data:
                            earnings_calls.append(call_data)
                            self.logger.info(f"      ✅ Extracted: {symbol} {call_data['quarter']}")

                        # Go back to earnings page for next transcript
                        if i < len(transcript_buttons) - 1 and len(earnings_calls) < num_quarters:
                            await page.goto(earnings_url, wait_until='networkidle')
                            await asyncio.sleep(2)
                            # Re-query transcript buttons as DOM may have changed
                            transcript_buttons = await page.query_selector_all('button:has-text("Transcript"), a:has-text("Transcript")')

                        # Stop if we have enough
                        if len(earnings_calls) >= num_quarters:
                            break

                    except Exception as e:
                        self.logger.error(f"      ❌ Error processing transcript: {e}")
                        # Try to go back to earnings page
                        try:
                            await page.goto(earnings_url, wait_until='networkidle')
                            await asyncio.sleep(2)
                        except:
                            pass
                        continue

                await context.close()
                await browser.close()

        except Exception as e:
            self.logger.error(f"❌ [SEEKING ALPHA] Error: {e}")

        self.logger.info(f"✅ [SEEKING ALPHA] Extracted {len(earnings_calls)} earnings calls for {symbol}")
        return earnings_calls

    async def _extract_call_data_from_page(
        self,
        page,
        article_url: str,
        article_id: str,
        symbol: str,
        quarter_info: Dict,
        call_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Extract transcript, audio, and presentation from current page (already on transcript article)

        Args:
            page: Playwright page object (already on transcript page)
            article_url: URL to earnings call article
            article_id: Article ID (for audio URL)
            symbol: Stock ticker
            quarter_info: Dict with 'quarter' and 'fiscal_year'
            call_date: Optional pre-extracted call date

        Returns:
            Dict with call data or None
        """
        try:
            # Extract transcript from current page
            transcript = await self._extract_transcript(page)

            if not transcript or len(transcript) < 100:
                self.logger.warning(f"      ⚠️ Transcript too short or empty")
                return None

            # Check for audio
            audio_url = self._check_audio_exists(article_id)

            # Look for presentation PDF
            presentation_url = await self._find_presentation_pdf(page)

            # Get call date if not already provided
            if not call_date:
                call_date = await self._extract_call_date(page)

            return {
                "symbol": symbol,
                "quarter": quarter_info['quarter'],
                "fiscal_year": quarter_info['fiscal_year'],
                "call_date": call_date,
                "transcript": transcript,
                "transcript_source": "seekingalpha",
                "audio_url": audio_url,
                "audio_source": "seekingalpha" if audio_url else None,
                "presentation_url": presentation_url,
                "presentation_source": "seekingalpha" if presentation_url else None,
                "article_url": article_url,
                "article_id": article_id
            }

        except Exception as e:
            self.logger.error(f"      ❌ Error extracting call data: {e}")
            return None

    async def _extract_transcript(self, page) -> str:
        """
        Extract transcript text from article page

        Returns:
            Clean transcript text with speaker labels
        """
        try:
            # Seeking Alpha stores transcripts in article body
            # Look for main content area
            content_selectors = [
                'div[data-test-id="content-container"]',
                'article',
                '.article-content',
                '#article-content'
            ]

            content_element = None
            for selector in content_selectors:
                content_element = await page.query_selector(selector)
                if content_element:
                    break

            if not content_element:
                self.logger.warning("      ⚠️ Could not find transcript content")
                return ""

            # Get HTML content
            content_html = await content_element.inner_html()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(content_html, 'html.parser')

            # Remove unwanted elements (ads, related articles, etc.)
            for unwanted in soup.find_all(['script', 'style', 'aside', 'nav']):
                unwanted.decompose()

            # Extract text
            text = soup.get_text(separator='\n', strip=True)

            # Clean up multiple newlines
            text = re.sub(r'\n{3,}', '\n\n', text)

            self.logger.info(f"      ✅ Extracted transcript: {len(text)} chars")
            return text

        except Exception as e:
            self.logger.error(f"      ❌ Error extracting transcript: {e}")
            return ""

    def _check_audio_exists(self, article_id: str) -> Optional[str]:
        """
        Check if audio file exists for this article

        Seeking Alpha audio pattern:
        https://static.seekingalpha.com/cdn/s3/transcripts_audio/{article_id}.mp3

        Args:
            article_id: Article ID (e.g., "4737214")

        Returns:
            Audio URL if exists, None otherwise
        """
        if not article_id:
            return None

        audio_url = f"https://static.seekingalpha.com/cdn/s3/transcripts_audio/{article_id}.mp3"

        try:
            # HEAD request to check if file exists
            response = self.session.head(audio_url, timeout=5)

            if response.status_code == 200:
                self.logger.info(f"      ✅ Audio found: {audio_url}")
                return audio_url
            else:
                self.logger.debug(f"      ℹ️ No audio file (status: {response.status_code})")
                return None

        except Exception as e:
            self.logger.debug(f"      Could not check audio: {e}")
            return None

    async def _find_presentation_pdf(self, page) -> Optional[str]:
        """
        Look for presentation PDF links on the page

        Returns:
            PDF URL if found, None otherwise
        """
        try:
            # Look for PDF links
            pdf_links = await page.query_selector_all('a[href$=".pdf"]')

            for link in pdf_links:
                href = await link.get_attribute('href')
                text = await link.inner_text()

                # Check if it's an earnings presentation
                if any(keyword in text.lower() for keyword in ['presentation', 'slides', 'deck', 'earnings']):
                    # Make absolute URL
                    if href.startswith('/'):
                        href = f"https://seekingalpha.com{href}"

                    self.logger.info(f"      ✅ Found presentation: {href}")
                    return href

            return None

        except Exception as e:
            self.logger.debug(f"      Could not find presentation: {e}")
            return None

    async def _extract_call_date(self, page) -> Optional[datetime]:
        """Extract call date from article metadata"""
        try:
            # Look for date in article metadata
            date_selectors = [
                'time[datetime]',
                '[data-test-id="post-date"]',
                '.article-date'
            ]

            for selector in date_selectors:
                date_element = await page.query_selector(selector)
                if date_element:
                    # Try to get datetime attribute
                    datetime_attr = await date_element.get_attribute('datetime')
                    if datetime_attr:
                        return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))

                    # Try to parse text
                    date_text = await date_element.inner_text()
                    # You could add date parsing here

            return None

        except Exception as e:
            self.logger.debug(f"      Could not extract call date: {e}")
            return None

    def _parse_quarter_from_title(self, title: str) -> Optional[Dict]:
        """
        Parse quarter and fiscal year from article title

        Examples:
        - "Apple Inc. (AAPL) Q4 2024 Earnings Call Transcript"
        - "Microsoft Corporation Q1 FY2024 Earnings Call Transcript"

        Args:
            title: Article title

        Returns:
            {"quarter": "Q1 2024", "fiscal_year": 2024} or None
        """
        # Pattern 1: Q1 2024, Q2 2023, etc.
        pattern1 = r'(Q[1-4])\s+(\d{4})'
        match = re.search(pattern1, title, re.IGNORECASE)

        if match:
            quarter = match.group(1).upper()
            year = int(match.group(2))
            return {
                "quarter": f"{quarter} {year}",
                "fiscal_year": year
            }

        # Pattern 2: Q1 FY2024, Q2 FY23, etc.
        pattern2 = r'(Q[1-4])\s+FY\s*(\d{2,4})'
        match = re.search(pattern2, title, re.IGNORECASE)

        if match:
            quarter = match.group(1).upper()
            year_str = match.group(2)

            # Handle 2-digit years
            if len(year_str) == 2:
                year = 2000 + int(year_str)
            else:
                year = int(year_str)

            return {
                "quarter": f"{quarter} {year}",
                "fiscal_year": year
            }

        return None

    def _extract_article_id(self, article_url: str) -> Optional[str]:
        """
        Extract article ID from Seeking Alpha URL

        Example:
        https://seekingalpha.com/article/4737214-apple-q4-2024-earnings -> "4737214"

        Args:
            article_url: Full article URL

        Returns:
            Article ID or None
        """
        pattern = r'/article/(\d+)'
        match = re.search(pattern, article_url)

        if match:
            return match.group(1)

        return None
