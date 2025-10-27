#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "programs" / "article_summarizer_backend"))

import braintrust
from core.prompts import ArticleAnalysisPrompt

# Initialize project (API key from BRAINTRUST_API_KEY env var)
project = braintrust.projects.create(name="automate-life")

# Create article analysis prompt
# Build a sample prompt to get the template structure
sample_metadata = {
    'title': 'Sample Article',
    'url': 'https://example.com',
    'platform': 'example',
    'has_video': True,
    'has_audio': False,
    'is_text_only': False,
    'extracted_at': '2025-10-27T00:00:00Z'
}
sample_context = "{{{media_context}}}"
prompt_template = ArticleAnalysisPrompt.build(
    url="{{{url}}}",
    media_context=sample_context,
    metadata=sample_metadata
)

project.prompts.create(
    slug=ArticleAnalysisPrompt.SLUG,
    name=ArticleAnalysisPrompt.NAME,
    description="Main prompt for analyzing articles and generating structured summaries (video/audio/text)",
    model=ArticleAnalysisPrompt.MODEL,
    params={"max_tokens": ArticleAnalysisPrompt.MAX_TOKENS},
    messages=[
        {
            "role": "user",
            "content": prompt_template,
        }
    ],
    if_exists="replace",
)

# Publish prompts to Braintrust
project.publish()
print("✅ Python prompts published to Braintrust")
