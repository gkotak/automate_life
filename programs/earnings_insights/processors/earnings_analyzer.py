"""
Earnings Analyzer

Uses Claude AI to analyze earnings call transcripts and extract structured insights.

Usage:
    analyzer = EarningsAnalyzer()
    insights = await analyzer.analyze_earnings_call(transcript_text, symbol, quarter)
"""

import logging
import json
from typing import Dict, Optional

# Import from core (which re-exports from article_summarizer)
import sys
from pathlib import Path
earnings_insights_path = Path(__file__).parent.parent
sys.path.insert(0, str(earnings_insights_path))

# Add article_summarizer_backend to path for Config
project_root = earnings_insights_path.parent.parent
article_summarizer_backend = project_root / 'programs' / 'article_summarizer_backend'
if str(article_summarizer_backend) not in sys.path:
    sys.path.insert(0, str(article_summarizer_backend))

from shared import ClaudeClient
from core.config import Config
from prompts.earnings_prompts import format_earnings_prompt

logger = logging.getLogger(__name__)


class EarningsAnalyzer:
    """
    Analyzes earnings call transcripts using Claude AI

    Features:
    - Extracts key financial metrics with timestamps
    - Identifies business highlights and strategic initiatives
    - Captures forward guidance
    - Identifies risks/concerns from management and analysts
    - Highlights positive developments
    - Selects notable quotes
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize Claude client with required parameters
        claude_cmd = Config.find_claude_cli()
        base_dir = Path(__file__).parent.parent.parent.parent  # Project root
        self.claude = ClaudeClient(claude_cmd, base_dir, self.logger)

    async def analyze_earnings_call(
        self,
        transcript_text: str,
        company_symbol: str,
        quarter: str
    ) -> Dict:
        """
        Analyze earnings call transcript and extract structured insights

        Args:
            transcript_text: Formatted transcript with timestamps ([MM:SS] Speaker: Text)
            company_symbol: Stock ticker (e.g., "AAPL")
            quarter: Quarter string (e.g., "Q1 2024")

        Returns:
            Dict with structured insights:
            {
                "key_metrics": {...},
                "business_highlights": [...],
                "guidance": {...},
                "risks_concerns": [...],
                "positives": [...],
                "notable_quotes": [...]
            }
        """
        self.logger.info(f"🤖 [CLAUDE] Analyzing {company_symbol} {quarter} earnings call")
        self.logger.info(f"   Transcript length: {len(transcript_text)} chars")

        try:
            # Format prompt
            prompt = format_earnings_prompt(transcript_text)

            # Send to Claude (call_api is synchronous, not async)
            self.logger.info("   Sending to Claude API...")
            response = self.claude.call_api(prompt)

            self.logger.info(f"   ✅ Received response: {len(response)} chars")

            # Parse JSON response
            insights = self._parse_claude_response(response)

            # Validate structure
            insights = self._validate_and_fix_insights(insights, company_symbol, quarter)

            # Log summary
            self._log_insights_summary(insights, company_symbol, quarter)

            return insights

        except Exception as e:
            self.logger.error(f"❌ [CLAUDE] Error analyzing {company_symbol} {quarter}: {e}")

            # Return empty structure on error
            return self._empty_insights_structure()

    def _parse_claude_response(self, response: str) -> Dict:
        """
        Parse Claude's JSON response

        Handles:
        - JSON wrapped in markdown code blocks
        - Extra whitespace
        - JSON parsing errors

        Args:
            response: Raw response from Claude

        Returns:
            Parsed JSON dict

        Raises:
            ValueError if cannot parse
        """
        # Remove markdown code blocks if present
        response = response.strip()

        if response.startswith('```json'):
            response = response[7:]  # Remove ```json
        elif response.startswith('```'):
            response = response[3:]  # Remove ```

        if response.endswith('```'):
            response = response[:-3]  # Remove ```

        response = response.strip()

        try:
            insights = json.loads(response)
            return insights

        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Failed to parse Claude response as JSON: {e}")
            self.logger.error(f"   Response (first 500 chars): {response[:500]}")
            raise ValueError(f"Invalid JSON response from Claude: {e}")

    def _validate_and_fix_insights(
        self,
        insights: Dict,
        company_symbol: str,
        quarter: str
    ) -> Dict:
        """
        Validate insights structure and fix common issues

        Args:
            insights: Parsed insights dict
            company_symbol: Stock ticker
            quarter: Quarter string

        Returns:
            Validated and fixed insights dict
        """
        # Required keys
        required_keys = [
            "key_metrics",
            "business_highlights",
            "guidance",
            "risks_concerns",
            "positives",
            "notable_quotes"
        ]

        # Fix missing keys
        for key in required_keys:
            if key not in insights:
                self.logger.warning(f"   ⚠️ Missing key: {key} - adding empty structure")

                # Objects for metrics/guidance, arrays for others
                if key in ["key_metrics", "guidance"]:
                    insights[key] = {}
                else:
                    insights[key] = []

        # Ensure arrays are actually arrays
        for key in ["business_highlights", "risks_concerns", "positives", "notable_quotes"]:
            if not isinstance(insights[key], list):
                self.logger.warning(f"   ⚠️ {key} is not a list - converting")
                insights[key] = []

        # Ensure objects are actually objects
        for key in ["key_metrics", "guidance"]:
            if not isinstance(insights[key], dict):
                self.logger.warning(f"   ⚠️ {key} is not a dict - converting")
                insights[key] = {}

        return insights

    def _log_insights_summary(self, insights: Dict, company_symbol: str, quarter: str):
        """Log summary of extracted insights"""
        self.logger.info(f"✅ [INSIGHTS] {company_symbol} {quarter} analysis complete:")
        self.logger.info(f"   - Key metrics: {len(insights.get('key_metrics', {}))} items")
        self.logger.info(f"   - Business highlights: {len(insights.get('business_highlights', []))} items")
        self.logger.info(f"   - Guidance: {len(insights.get('guidance', {}))} items")
        self.logger.info(f"   - Risks/concerns: {len(insights.get('risks_concerns', []))} items")
        self.logger.info(f"   - Positives: {len(insights.get('positives', []))} items")
        self.logger.info(f"   - Notable quotes: {len(insights.get('notable_quotes', []))} items")

    def _empty_insights_structure(self) -> Dict:
        """Return empty insights structure (used on error)"""
        return {
            "key_metrics": {},
            "business_highlights": [],
            "guidance": {},
            "risks_concerns": [],
            "positives": [],
            "notable_quotes": []
        }
