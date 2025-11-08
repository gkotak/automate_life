"""
Backfill Earnings Calls

Fetches latest N quarters of earnings calls from Seeking Alpha for all companies.

Usage:
    python scripts/earnings_insights/backfill_earnings_calls.py --quarters 4
    python scripts/earnings_insights/backfill_earnings_calls.py --symbol AAPL --quarters 8
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

# Add earnings_insights to path
earnings_insights_path = project_root / 'programs' / 'earnings_insights'
sys.path.insert(0, str(earnings_insights_path))

from supabase import create_client, Client
from scrapers.seekingalpha_scraper import SeekingAlphaScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def backfill_company_earnings(
    supabase: Client,
    scraper: SeekingAlphaScraper,
    company: dict,
    num_quarters: int
):
    """
    Backfill earnings calls for a single company

    Args:
        supabase: Supabase client
        scraper: SeekingAlphaScraper instance
        company: Company dict from database
        num_quarters: Number of quarters to fetch
    """
    symbol = company['symbol']
    company_id = company['id']

    logger.info(f"\n{'=' * 60}")
    logger.info(f"BACKFILLING: {symbol} - {company['name']}")
    logger.info(f"{'=' * 60}")

    try:
        # Fetch earnings calls from Seeking Alpha
        earnings_data = await scraper.get_latest_earnings_calls(symbol, num_quarters)

        if not earnings_data:
            logger.warning(f"⚠️  No earnings calls found for {symbol}")
            return 0

        # Insert each call into database
        inserted_count = 0

        for call in earnings_data:
            try:
                # Prepare data for insertion
                call_data = {
                    "company_id": company_id,
                    "symbol": symbol,
                    "quarter": call["quarter"],
                    "fiscal_year": call["fiscal_year"],
                    "call_date": call["call_date"].isoformat() if call["call_date"] else None,

                    # Transcript
                    "transcript_text": call["transcript"],
                    "transcript_source": call["transcript_source"],

                    # Audio
                    "audio_url": call["audio_url"],
                    "audio_source": call["audio_source"],

                    # Presentation
                    "presentation_url": call["presentation_url"],
                    "presentation_source": call["presentation_source"],

                    # Status
                    "processing_status": "pending"
                }

                # Try to insert
                result = supabase.table('earnings_calls').insert(call_data).execute()

                logger.info(f"   ✅ Added: {symbol} {call['quarter']}")
                inserted_count += 1

            except Exception as e:
                error_msg = str(e)

                # Check if it's a duplicate error
                if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower():
                    logger.info(f"   ⏭️  Skipped: {symbol} {call['quarter']} (already exists)")
                else:
                    logger.error(f"   ❌ Error adding {symbol} {call['quarter']}: {e}")

        logger.info(f"✅ {symbol}: Inserted {inserted_count} earnings calls")
        return inserted_count

    except Exception as e:
        logger.error(f"❌ Error backfilling {symbol}: {e}")
        return 0


async def backfill_all_companies(num_quarters: int, symbol_filter: str = None):
    """
    Backfill earnings calls for all companies (or specific symbol)

    Args:
        num_quarters: Number of quarters to fetch per company
        symbol_filter: If provided, only process this symbol
    """
    logger.info("=" * 60)
    logger.info("BACKFILLING EARNINGS CALLS")
    logger.info("=" * 60)
    logger.info(f"Quarters per company: {num_quarters}")
    if symbol_filter:
        logger.info(f"Filter: {symbol_filter} only")

    # Initialize Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    # Initialize scraper
    scraper = SeekingAlphaScraper()

    # Get companies from database
    try:
        query = supabase.table('earnings_companies')\
            .select('*')\
            .eq('is_active', True)

        if symbol_filter:
            query = query.eq('symbol', symbol_filter)

        result = query.execute()
        companies = result.data

        logger.info(f"\n📊 Processing {len(companies)} companies...\n")

    except Exception as e:
        logger.error(f"❌ Error fetching companies: {e}")
        return

    # Process each company
    total_inserted = 0

    for i, company in enumerate(companies, 1):
        logger.info(f"\n[{i}/{len(companies)}] Processing {company['symbol']}...")

        try:
            count = await backfill_company_earnings(
                supabase,
                scraper,
                company,
                num_quarters
            )
            total_inserted += count

            # Rate limiting: wait between companies
            if i < len(companies):
                logger.info("   ⏳ Waiting 3 seconds before next company...")
                await asyncio.sleep(3)

        except Exception as e:
            logger.error(f"❌ Error processing {company['symbol']}: {e}")
            continue

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Companies processed: {len(companies)}")
    logger.info(f"Total earnings calls inserted: {total_inserted}")
    logger.info(f"Average per company: {total_inserted / len(companies):.1f}")

    # Verify in database
    try:
        result = supabase.table('earnings_calls')\
            .select('count', count='exact')\
            .execute()

        total_in_db = result.count if hasattr(result, 'count') else len(result.data)
        logger.info(f"\n📊 Total earnings calls in database: {total_in_db}")

        # Count by status
        pending_result = supabase.table('earnings_calls')\
            .select('count', count='exact')\
            .eq('processing_status', 'pending')\
            .execute()

        pending_count = pending_result.count if hasattr(pending_result, 'count') else len(pending_result.data)
        logger.info(f"   - Pending processing: {pending_count}")

    except Exception as e:
        logger.warning(f"Could not verify counts: {e}")

    logger.info("\n🎉 Backfill complete!")
    logger.info("\nNext steps:")
    logger.info("  1. Run process_single_earning.py to process calls")
    logger.info("  2. Or use the FastAPI backend to process in parallel")


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Backfill earnings calls from Seeking Alpha")
    parser.add_argument('--quarters', type=int, default=4, help='Number of quarters to fetch per company')
    parser.add_argument('--symbol', type=str, help='Process specific symbol only')
    args = parser.parse_args()

    # Load environment variables
    from dotenv import load_dotenv
    env_path = project_root / ".env.local"
    load_dotenv(env_path)

    asyncio.run(backfill_all_companies(args.quarters, args.symbol))
