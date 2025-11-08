"""
Earnings Processor - Main Orchestrator

Coordinates the complete earnings call processing pipeline:
1. Download audio (if available)
2. Extract transcript (if available)
3. Align transcript with audio (add timestamps)
4. Format for Claude
5. Claude analysis → insights
6. Save to database

Usage:
    from services.earnings_processor import process_earnings_call
    await process_earnings_call(earnings_call_id)
"""

import logging
import os
from typing import Dict, Optional
from supabase import create_client, Client

# Import from parent directories
import sys
from pathlib import Path
earnings_insights_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(earnings_insights_path))

from shared import (
    TranscriptAligner,
    format_aligned_transcript_for_claude
)
from programs.earnings_insights.processors.earnings_analyzer import EarningsAnalyzer

logger = logging.getLogger(__name__)


class EarningsProcessor:
    """Main orchestrator for earnings call processing"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize Supabase
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        self.supabase: Client = create_client(supabase_url, supabase_key)

        # Initialize processors
        self.aligner = TranscriptAligner()
        self.analyzer = EarningsAnalyzer()

        # Note: FileTranscriber not initialized - audio-only transcription not yet supported
        # For now, we require transcript_text from scraper (SeekingAlpha provides this)

    async def process_earnings_call(self, earnings_call_id: int):
        """
        Process a single earnings call through the complete pipeline

        Args:
            earnings_call_id: ID of earnings_calls record

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"\n{'=' * 60}")
        self.logger.info(f"PROCESSING EARNINGS CALL ID: {earnings_call_id}")
        self.logger.info(f"{'=' * 60}\n")

        try:
            # 1. Load call from database
            call = await self._load_call(earnings_call_id)
            if not call:
                return False

            self.logger.info(f"📊 {call['symbol']} {call['quarter']}")

            # Update status to 'processing'
            await self._update_call_status(earnings_call_id, 'processing')

            # 2. Ensure we have both audio and transcript
            if not call.get('audio_url'):
                self.logger.warning("⚠️  No audio URL - transcript-only processing")

            if not call.get('transcript_text'):
                self.logger.warning("⚠️  No transcript text - will transcribe from audio")

            # 3. Align transcript with audio (add timestamps)
            transcript_for_claude = await self._prepare_transcript(call, earnings_call_id)

            if not transcript_for_claude:
                raise ValueError("Could not prepare transcript for analysis")

            # 4. Run Claude analysis
            insights = await self.analyzer.analyze_earnings_call(
                transcript_text=transcript_for_claude,
                company_symbol=call['symbol'],
                quarter=call['quarter']
            )

            # 5. Save insights to database
            await self._save_insights(earnings_call_id, call, insights)

            # 6. Update status to 'completed'
            await self._update_call_status(earnings_call_id, 'completed')

            self.logger.info(f"\n✅ Successfully processed {call['symbol']} {call['quarter']}\n")
            return True

        except Exception as e:
            self.logger.error(f"❌ Error processing call {earnings_call_id}: {e}")

            # Update status to 'failed' with error message
            await self._update_call_status(
                earnings_call_id,
                'failed',
                error_message=str(e)
            )

            return False

    async def _load_call(self, earnings_call_id: int) -> Optional[Dict]:
        """Load earnings call from database"""
        try:
            result = self.supabase.table('earnings_calls')\
                .select('*')\
                .eq('id', earnings_call_id)\
                .execute()

            if not result.data:
                self.logger.error(f"❌ Earnings call {earnings_call_id} not found")
                return None

            return result.data[0]

        except Exception as e:
            self.logger.error(f"❌ Error loading call: {e}")
            return None

    async def _prepare_transcript(
        self,
        call: Dict,
        earnings_call_id: int
    ) -> Optional[str]:
        """
        Prepare transcript for Claude analysis

        Handles three scenarios:
        1. Both audio + transcript: Align and format with timestamps
        2. Audio only: Transcribe with Deepgram
        3. Transcript only: Format without timestamps (warn user)

        Args:
            call: Earnings call dict from database
            earnings_call_id: Call ID for database updates

        Returns:
            Formatted transcript ready for Claude
        """
        audio_url = call.get('audio_url')
        transcript_text = call.get('transcript_text')

        # Scenario 1: Both audio and transcript - ALIGN
        if audio_url and transcript_text:
            self.logger.info("✅ Both audio and transcript available - aligning timestamps")

            try:
                aligned_data = await self.aligner.align_transcript(
                    audio_url,
                    transcript_text
                )

                # Save aligned version to database (Supabase is sync, not async)
                self.supabase.table('earnings_calls').update({
                    'transcript_json': aligned_data
                }).eq('id', earnings_call_id).execute()

                self.logger.info("   ✅ Saved aligned transcript to database")

                # Format for Claude with timestamps
                formatted = format_aligned_transcript_for_claude(aligned_data)
                return formatted

            except Exception as e:
                self.logger.error(f"   ❌ Alignment failed: {e}")
                self.logger.warning("   Falling back to transcript-only (no timestamps)")
                return transcript_text

        # Scenario 2: Audio only - TRANSCRIBE
        elif audio_url and not transcript_text:
            self.logger.error("❌ Audio-only transcription not yet supported")
            self.logger.error("   SeekingAlpha scraper should provide transcript_text")
            self.logger.error("   If you need this feature, FileTranscriber needs audio URL support")
            return None

        # Scenario 3: Transcript only - NO TIMESTAMPS
        elif transcript_text and not audio_url:
            self.logger.warning("⚠️  Transcript only - no timestamps available")
            self.logger.warning("   Claude analysis will proceed without timestamps")
            return transcript_text

        # Scenario 4: Neither audio nor transcript
        else:
            self.logger.error("❌ No audio or transcript available - cannot process")
            return None

    async def _save_insights(
        self,
        earnings_call_id: int,
        call: Dict,
        insights: Dict
    ):
        """
        Save insights to database

        Updates two tables:
        1. earnings_calls.summary_json (full insights)
        2. earnings_insights (structured table)

        Args:
            earnings_call_id: Call ID
            call: Call dict (for company_id, symbol, quarter)
            insights: Insights dict from analyzer
        """
        try:
            # 1. Update earnings_calls.summary_json
            self.supabase.table('earnings_calls').update({
                'summary_json': insights
            }).eq('id', earnings_call_id).execute()

            self.logger.info("   ✅ Saved summary_json to earnings_calls")

            # 2. Upsert into earnings_insights table (delete old if exists, then insert)
            # First, delete any existing insights for this earnings_call_id
            self.supabase.table('earnings_insights').delete().eq('earnings_call_id', earnings_call_id).execute()

            insights_record = {
                'earnings_call_id': earnings_call_id,
                'company_id': call['company_id'],
                'symbol': call['symbol'],
                'quarter': call['quarter'],
                'key_metrics': insights.get('key_metrics', {}),
                'business_highlights': insights.get('business_highlights', []),
                'guidance': insights.get('guidance', {}),
                'risks_concerns': insights.get('risks_concerns', []),
                'positives': insights.get('positives', []),
                'notable_quotes': insights.get('notable_quotes', [])
            }

            self.supabase.table('earnings_insights').insert(insights_record).execute()

            self.logger.info("   ✅ Saved structured insights to earnings_insights")

        except Exception as e:
            self.logger.error(f"   ❌ Error saving insights: {e}")
            raise

    async def _update_call_status(
        self,
        earnings_call_id: int,
        status: str,
        error_message: str = None
    ):
        """Update processing status in database"""
        try:
            update_data = {'processing_status': status}

            if error_message:
                update_data['error_message'] = error_message

            self.supabase.table('earnings_calls').update(update_data)\
                .eq('id', earnings_call_id)\
                .execute()

        except Exception as e:
            self.logger.warning(f"Could not update status: {e}")


# =============================================================================
# Convenience function for scripts
# =============================================================================

async def process_earnings_call(earnings_call_id: int):
    """
    Convenience function to process a single earnings call

    Usage:
        from services.earnings_processor import process_earnings_call
        await process_earnings_call(123)

    Args:
        earnings_call_id: ID of earnings_calls record

    Returns:
        True if successful, False otherwise
    """
    processor = EarningsProcessor()
    return await processor.process_earnings_call(earnings_call_id)
