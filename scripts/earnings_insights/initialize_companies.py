"""
Initialize Companies Script

Loads initial list of companies into earnings_companies table.

Usage:
    python scripts/earnings_insights/initialize_companies.py
"""

import os
import sys
import asyncio
import logging
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

# =============================================================================
# Company List
# =============================================================================
# TODO: Replace with your 50 companies
# This is a starter list of major tech/finance companies

INITIAL_COMPANIES = [
    # Technology
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
]


async def initialize_companies():
    """
    Load companies into database
    """
    logger.info("=" * 60)
    logger.info("INITIALIZING COMPANIES")
    logger.info("=" * 60)

    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        logger.error("   Please set these environment variables")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    logger.info(f"\n📊 Loading {len(INITIAL_COMPANIES)} companies...")

    inserted_count = 0
    skipped_count = 0
    error_count = 0

    for company in INITIAL_COMPANIES:
        try:
            # Add Seeking Alpha URL
            company['seekingalpha_url'] = f"https://seekingalpha.com/symbol/{company['symbol']}"
            company['is_active'] = True

            # Try to insert
            result = supabase.table('earnings_companies').insert(company).execute()

            logger.info(f"✅ Added: {company['symbol']:6s} - {company['name']}")
            inserted_count += 1

        except Exception as e:
            error_msg = str(e)

            # Check if it's a duplicate error
            if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower():
                logger.info(f"⏭️  Skipped: {company['symbol']:6s} - {company['name']} (already exists)")
                skipped_count += 1
            else:
                logger.error(f"❌ Error adding {company['symbol']}: {e}")
                error_count += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Inserted: {inserted_count} companies")
    logger.info(f"⏭️  Skipped:  {skipped_count} companies (already existed)")
    if error_count > 0:
        logger.info(f"❌ Errors:   {error_count} companies")

    logger.info(f"\nTotal companies in list: {len(INITIAL_COMPANIES)}")
    logger.info("\n🎉 Initialization complete!")

    # Verify in database
    try:
        result = supabase.table('earnings_companies')\
            .select('count', count='exact')\
            .execute()

        total_in_db = result.count if hasattr(result, 'count') else len(result.data)
        logger.info(f"\n📊 Total companies in database: {total_in_db}")

    except Exception as e:
        logger.warning(f"Could not verify count: {e}")


if __name__ == "__main__":
    # Load environment variables from project root
    from dotenv import load_dotenv
    env_path = project_root / '.env.local'
    load_dotenv(env_path)

    asyncio.run(initialize_companies())
