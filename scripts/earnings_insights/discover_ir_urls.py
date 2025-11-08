"""
Discover Investor Relations URLs

Finds and verifies investor relations pages for all companies in the database.

Usage:
    python scripts/earnings_insights/discover_ir_urls.py
    python scripts/earnings_insights/discover_ir_urls.py --symbol AAPL
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IRDiscoverer:
    """Discover investor relations URLs for companies"""

    # Common IR URL patterns
    IR_PATTERNS = [
        "https://investor.{domain}",
        "https://ir.{domain}",
        "https://{domain}/investor-relations",
        "https://{domain}/investors",
        "https://{domain}/ir",
    ]

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def discover_ir_url(self, symbol: str, company_name: str) -> str:
        """
        Discover investor relations URL for a company

        Tries multiple strategies:
        1. Common URL patterns
        2. Google search (TODO)
        3. Manual lookup from known list

        Args:
            symbol: Stock ticker
            company_name: Company name

        Returns:
            IR URL or constructed URL based on best guess
        """
        self.logger.info(f"🔍 Discovering IR URL for {symbol} ({company_name})")

        # Strategy 1: Try common patterns based on company domain
        domain = self._guess_company_domain(symbol, company_name)

        if domain:
            ir_url = await self._try_common_patterns(domain)
            if ir_url:
                self.logger.info(f"   ✅ Found via pattern: {ir_url}")
                return ir_url

        # Strategy 2: Use known IR URLs (manual lookup table)
        known_url = self._get_known_ir_url(symbol)
        if known_url:
            self.logger.info(f"   ✅ Found in known URLs: {known_url}")
            return known_url

        # Strategy 3: Fallback to constructed URL
        fallback_url = f"https://investor.{domain}" if domain else None
        self.logger.info(f"   ⚠️ Using fallback: {fallback_url}")

        return fallback_url

    def _guess_company_domain(self, symbol: str, company_name: str) -> str:
        """
        Guess company domain from symbol or name

        Examples:
        - AAPL -> apple.com
        - MSFT -> microsoft.com
        """
        # Manual mapping for common symbols
        symbol_to_domain = {
            "AAPL": "apple.com",
            "MSFT": "microsoft.com",
            "GOOGL": "abc.xyz",  # Google parent company
            "AMZN": "amazon.com",
            "META": "meta.com",
            "TSLA": "tesla.com",
            "NFLX": "netflix.com",
            "NVDA": "nvidia.com",
            "JPM": "jpmorganchase.com",
            "BAC": "bankofamerica.com",
            "WFC": "wellsfargo.com",
            "GS": "goldmansachs.com",
            "MS": "morganstanley.com",
            "V": "visa.com",
            "MA": "mastercard.com",
            "WMT": "walmart.com",
            "HD": "homedepot.com",
            "DIS": "thewaltdisneycompany.com",
            # Add more as needed
        }

        if symbol in symbol_to_domain:
            return symbol_to_domain[symbol]

        # Fallback: derive from company name
        # Remove "Inc.", "Corp", etc.
        clean_name = company_name.lower()
        for suffix in [' inc.', ' corporation', ' corp', ' company', ' co.', ' ltd']:
            clean_name = clean_name.replace(suffix, '')

        # Take first word
        first_word = clean_name.split()[0]
        return f"{first_word}.com"

    async def _try_common_patterns(self, domain: str) -> str:
        """
        Try common IR URL patterns

        Args:
            domain: Company domain (e.g., "apple.com")

        Returns:
            Working URL or None
        """
        import aiohttp

        async with aiohttp.ClientSession() as session:
            for pattern in self.IR_PATTERNS:
                url = pattern.format(domain=domain)

                try:
                    async with session.head(url, timeout=5, allow_redirects=True) as response:
                        if response.status == 200:
                            return str(response.url)  # Return final URL after redirects

                except Exception:
                    continue

        return None

    def _get_known_ir_url(self, symbol: str) -> str:
        """
        Get known IR URL from manual lookup table

        This is a fallback for companies where auto-discovery doesn't work
        """
        known_urls = {
            "AAPL": "https://investor.apple.com",
            "MSFT": "https://www.microsoft.com/en-us/investor",
            "GOOGL": "https://abc.xyz/investor/",
            "AMZN": "https://ir.aboutamazon.com",
            "META": "https://investor.fb.com",
            "TSLA": "https://ir.tesla.com",
            "NFLX": "https://ir.netflix.net",
            "NVDA": "https://investor.nvidia.com",
            # Add more as discovered
        }

        return known_urls.get(symbol)


async def discover_all_ir_urls(symbol_filter: str = None):
    """
    Discover IR URLs for all companies (or specific symbol)

    Args:
        symbol_filter: If provided, only process this symbol
    """
    logger.info("=" * 60)
    logger.info("DISCOVERING INVESTOR RELATIONS URLS")
    logger.info("=" * 60)

    # Initialize Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        return

    supabase: Client = create_client(supabase_url, supabase_key)
    discoverer = IRDiscoverer()

    # Get companies from database
    try:
        query = supabase.table('earnings_companies').select('*')

        if symbol_filter:
            query = query.eq('symbol', symbol_filter)

        result = query.execute()
        companies = result.data

        logger.info(f"\n📊 Processing {len(companies)} companies...\n")

    except Exception as e:
        logger.error(f"❌ Error fetching companies: {e}")
        return

    # Process each company
    updated_count = 0

    for company in companies:
        symbol = company['symbol']
        name = company['name']

        # Skip if already has IR URL
        if company.get('investor_relations_url') and not symbol_filter:
            logger.info(f"⏭️  {symbol:6s} - Already has IR URL")
            continue

        try:
            # Discover IR URL
            ir_url = await discoverer.discover_ir_url(symbol, name)

            # Update database
            if ir_url:
                supabase.table('earnings_companies')\
                    .update({'investor_relations_url': ir_url})\
                    .eq('symbol', symbol)\
                    .execute()

                updated_count += 1
                logger.info(f"✅ {symbol:6s} - Updated IR URL: {ir_url}")
            else:
                logger.warning(f"⚠️  {symbol:6s} - Could not find IR URL")

        except Exception as e:
            logger.error(f"❌ {symbol:6s} - Error: {e}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Updated: {updated_count} companies")
    logger.info("\n🎉 Discovery complete!")


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Discover investor relations URLs")
    parser.add_argument('--symbol', type=str, help='Process specific symbol only')
    args = parser.parse_args()

    # Load environment variables
    from dotenv import load_dotenv
    env_path = project_root / ".env.local"
    load_dotenv(env_path)

    asyncio.run(discover_all_ir_urls(args.symbol))
