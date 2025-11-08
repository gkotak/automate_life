"""
Process All Pending Earnings Calls

Batch processes all earnings calls with status='pending'.

Usage:
    python scripts/earnings_insights/process_all_pending.py
    python scripts/earnings_insights/process_all_pending.py --limit 10
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
from app.services.earnings_processor import process_earnings_call

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def process_all_pending(limit: int = None):
    """
    Process all pending earnings calls

    Args:
        limit: Optional limit on number of calls to process
    """
    logger.info("=" * 60)
    logger.info("PROCESSING ALL PENDING EARNINGS CALLS")
    logger.info("=" * 60)

    # Initialize Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        return

    supabase: Client = create_client(supabase_url, supabase_key)

    # Get pending calls
    try:
        query = supabase.table('earnings_calls')\
            .select('id, symbol, quarter')\
            .eq('processing_status', 'pending')\
            .order('call_date', desc=True)

        if limit:
            query = query.limit(limit)

        result = query.execute()
        pending_calls = result.data

        logger.info(f"\n📊 Found {len(pending_calls)} pending calls")

        if limit and len(pending_calls) > 0:
            logger.info(f"   (Processing first {limit})\n")

    except Exception as e:
        logger.error(f"❌ Error fetching pending calls: {e}")
        return

    # Process each call
    success_count = 0
    failed_count = 0

    for i, call in enumerate(pending_calls, 1):
        logger.info(f"\n[{i}/{len(pending_calls)}] Processing {call['symbol']} {call['quarter']} (ID: {call['id']})")

        try:
            success = await process_earnings_call(call['id'])

            if success:
                success_count += 1
            else:
                failed_count += 1

            # Rate limiting: wait between calls
            if i < len(pending_calls):
                logger.info("   ⏳ Waiting 5 seconds before next call...")
                await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"❌ Error processing call {call['id']}: {e}")
            failed_count += 1
            continue

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total calls processed: {len(pending_calls)}")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed: {failed_count}")

    # Check remaining pending
    try:
        remaining_result = supabase.table('earnings_calls')\
            .select('count', count='exact')\
            .eq('processing_status', 'pending')\
            .execute()

        remaining_count = remaining_result.count if hasattr(remaining_result, 'count') else len(remaining_result.data)
        logger.info(f"\n📊 Remaining pending calls: {remaining_count}")

    except Exception as e:
        logger.warning(f"Could not check remaining calls: {e}")

    logger.info("\n🎉 Batch processing complete!")


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Process all pending earnings calls")
    parser.add_argument('--limit', type=int, help='Limit number of calls to process')
    args = parser.parse_args()

    # Load environment variables
    from dotenv import load_dotenv
    env_path = project_root / ".env.local"
    load_dotenv(env_path)

    asyncio.run(process_all_pending(args.limit))
