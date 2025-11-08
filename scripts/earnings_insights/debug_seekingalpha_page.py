"""
Debug script to investigate Seeking Alpha page structure
Takes a screenshot and saves HTML to understand why scraping is failing
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import shared modules
earnings_insights_dir = project_root / 'programs' / 'earnings_insights'
sys.path.insert(0, str(earnings_insights_dir))
from shared import AuthenticationManager

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def debug_seekingalpha_page(symbol: str = "AAPL"):
    """
    Load Seeking Alpha earnings page and save screenshot + HTML
    """
    logger.info(f"🔍 Debugging Seeking Alpha page for {symbol}")

    # Initialize AuthenticationManager with dummy session (we only need storage_state loading)
    import requests
    session = requests.Session()
    auth_manager = AuthenticationManager(base_dir=project_root, session=session)

    # Load storage state from Supabase
    storage_state = auth_manager._load_storage_state_from_supabase()

    if not storage_state:
        logger.error("❌ No authentication session found")
        return

    logger.info(f"✅ Loaded {len(storage_state.get('cookies', []))} cookies")

    async with async_playwright() as p:
        # Launch browser with same settings as scraper
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        )

        # Create context with storage state
        context = await browser.new_context(
            storage_state=storage_state,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )

        # Add stealth scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        # Load homepage first
        logger.info("🏠 Loading homepage...")
        await page.goto('https://seekingalpha.com', wait_until='networkidle')
        await asyncio.sleep(3)

        # Navigate to earnings page
        earnings_url = f"https://seekingalpha.com/symbol/{symbol}/earnings"
        logger.info(f"📄 Navigating to: {earnings_url}")
        await page.goto(earnings_url, wait_until='networkidle')

        # Wait for page to load
        logger.info("⏳ Waiting 15 seconds...")
        await asyncio.sleep(15)

        # Scroll to middle
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
        await asyncio.sleep(3)

        # Save screenshot
        screenshot_path = project_root / 'debug_seekingalpha.png'
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"📸 Screenshot saved: {screenshot_path}")

        # Save HTML
        html_content = await page.content()
        html_path = project_root / 'debug_seekingalpha.html'
        html_path.write_text(html_content, encoding='utf-8')
        logger.info(f"💾 HTML saved: {html_path}")

        # Check for specific elements
        logger.info("\n🔍 Checking page elements:")

        # Check page title
        title = await page.title()
        logger.info(f"   Title: {title}")

        # Check for CAPTCHA
        captcha = await page.query_selector('[class*="captcha"]')
        if captcha:
            logger.warning("   ⚠️ CAPTCHA detected!")

        # Check for login prompt
        login = await page.query_selector('button:has-text("Log in"), a:has-text("Log in")')
        if login:
            logger.warning("   ⚠️ Login prompt detected!")

        # Check for "Earnings History" text
        earnings_history_text = await page.query_selector('text="Earnings History"')
        if earnings_history_text:
            logger.info("   ✅ Found 'Earnings History' text")
        else:
            logger.warning("   ⚠️ 'Earnings History' text not found")

        # Check for "Transcript" text anywhere on page
        transcript_count = await page.query_selector_all('text="Transcript"')
        logger.info(f"   Found {len(transcript_count)} elements with 'Transcript' text")

        # Check for transcript buttons
        transcript_buttons = await page.query_selector_all('button:has-text("Transcript")')
        logger.info(f"   Found {len(transcript_buttons)} transcript buttons")

        # Check for transcript links
        transcript_links = await page.query_selector_all('a:has-text("Transcript")')
        logger.info(f"   Found {len(transcript_links)} transcript links")

        # List all visible buttons
        all_buttons = await page.query_selector_all('button')
        visible_buttons = []
        for btn in all_buttons[:20]:  # Check first 20 buttons
            if await btn.is_visible():
                text = await btn.inner_text()
                visible_buttons.append(text.strip())

        logger.info(f"\n📋 First 20 visible buttons:")
        for i, btn_text in enumerate(visible_buttons, 1):
            logger.info(f"   {i}. {btn_text[:100]}")  # Truncate long text

        # Wait for user to inspect
        logger.info("\n⏸️  Browser will stay open for inspection. Press Ctrl+C to close.")
        try:
            await asyncio.sleep(300)  # 5 minutes
        except KeyboardInterrupt:
            logger.info("🛑 Closing browser...")

        await context.close()
        await browser.close()


if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    asyncio.run(debug_seekingalpha_page(symbol))
