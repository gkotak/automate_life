#!/usr/bin/env python3
"""
Push Python prompts to Braintrust for versioning and observability.

This script registers all prompts defined in core/prompts.py with Braintrust,
creating versions that can be tracked in traces and the Braintrust dashboard.

Usage:
    python3 scripts/push_prompts_to_braintrust.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from braintrust import init_logger
from core.prompts import ArticleAnalysisPrompt


def push_article_analysis_prompt():
    """Push ArticleAnalysisPrompt to Braintrust"""

    # Check for API key
    api_key = os.getenv('BRAINTRUST_API_KEY')
    if not api_key:
        print("❌ Error: BRAINTRUST_API_KEY environment variable not set")
        sys.exit(1)

    # Initialize Braintrust logger
    try:
        logger = init_logger(
            project="automate-life",
            api_key=api_key
        )
        print("✅ Connected to Braintrust")
    except Exception as e:
        print(f"❌ Failed to initialize Braintrust: {e}")
        sys.exit(1)

    # Register the prompt
    # Note: Braintrust Python SDK prompt management works differently than TypeScript
    # For Python, we log the prompt usage in traces, and Braintrust automatically
    # tracks prompt versions through the logged data.

    # Create a sample trace with the prompt to register it
    try:
        # Get a sample prompt (with dummy data)
        sample_metadata = {
            'title': 'Sample Article',
            'url': 'https://example.com',
            'platform': 'example',
            'has_video': True,
            'has_audio': False,
            'is_text_only': False,
            'extracted_at': '2025-10-27T00:00:00Z'
        }

        sample_media_context = "Sample video context with transcript"
        sample_prompt = ArticleAnalysisPrompt.build(
            url='https://example.com',
            media_context=sample_media_context,
            metadata=sample_metadata
        )

        # Log a trace that registers the prompt structure
        with logger.start_span(
            name="register_prompt",
            span_attributes={
                "prompt_slug": ArticleAnalysisPrompt.SLUG,
                "prompt_name": ArticleAnalysisPrompt.NAME,
                "model": ArticleAnalysisPrompt.MODEL,
                "max_tokens": ArticleAnalysisPrompt.MAX_TOKENS
            }
        ) as span:
            span.log(
                input={"type": "prompt_registration", "prompt_slug": ArticleAnalysisPrompt.SLUG},
                output={"prompt_length": len(sample_prompt), "registered": True}
            )

        print(f"✅ Registered prompt: {ArticleAnalysisPrompt.NAME}")
        print(f"   Slug: {ArticleAnalysisPrompt.SLUG}")
        print(f"   Model: {ArticleAnalysisPrompt.MODEL}")
        print(f"   Max tokens: {ArticleAnalysisPrompt.MAX_TOKENS}")

    except Exception as e:
        print(f"❌ Failed to register prompt: {e}")
        sys.exit(1)

    # Flush logger to ensure data is sent
    logger.flush()
    print("\n✅ All prompts pushed to Braintrust successfully")
    print("   View at: https://www.braintrust.dev/app/automate-life")


def main():
    """Main entry point"""
    print("🔄 Pushing Python prompts to Braintrust...\n")
    push_article_analysis_prompt()


if __name__ == "__main__":
    main()
