"""
Process Single Earnings Call

Processes a single earnings call through the complete pipeline.

Usage:
    python scripts/earnings_insights/process_single_earning.py --call-id 123
    python scripts/earnings_insights/process_single_earning.py --symbol AAPL --quarter "Q1 2024"
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


async def process_by_call_id(call_id: int):
    """Process earnings call by ID"""
    logger.info(f"Processing earnings call ID: {call_id}")

    success = await process_earnings_call(call_id)

    if success:
        logger.info(f"\n✅ Processing complete!")
    else:
        logger.error(f"\n❌ Processing failed!")

    return success


async def process_by_symbol_quarter(symbol: str, quarter: str):
    """Process earnings call by symbol + quarter"""
    logger.info(f"Finding earnings call for {symbol} {quarter}")

    # Initialize Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set")
        return False

    supabase: Client = create_client(supabase_url, supabase_key)

    # Find call
    try:
        result = supabase.table('earnings_calls')\
            .select('id')\
            .eq('symbol', symbol)\
            .eq('quarter', quarter)\
            .execute()

        if not result.data:
            logger.error(f"❌ No earnings call found for {symbol} {quarter}")
            return False

        call_id = result.data[0]['id']
        logger.info(f"   Found call ID: {call_id}")

        return await process_by_call_id(call_id)

    except Exception as e:
        logger.error(f"❌ Error finding call: {e}")
        return False


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Process a single earnings call")
    parser.add_argument('--call-id', type=int, help='Earnings call ID')
    parser.add_argument('--symbol', type=str, help='Stock symbol')
    parser.add_argument('--quarter', type=str, help='Quarter (e.g., "Q1 2024")')
    args = parser.parse_args()

    # Load environment variables
    from dotenv import load_dotenv
    env_path = project_root / ".env.local"
    load_dotenv(env_path)

    # Validate arguments
    if args.call_id:
        asyncio.run(process_by_call_id(args.call_id))
    elif args.symbol and args.quarter:
        asyncio.run(process_by_symbol_quarter(args.symbol, args.quarter))
    else:
        parser.print_help()
        print("\nError: Must provide either --call-id OR --symbol + --quarter")
        sys.exit(1)
