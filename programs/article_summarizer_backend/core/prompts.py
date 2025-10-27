#!/usr/bin/env python3
"""
Braintrust-managed prompts for article analysis

This module contains all AI prompts used by the article summarizer.
These prompts are version-controlled in Git and automatically synced to Braintrust
for observability and debugging.

Workflow:
1. Edit prompts in this file
2. Commit to Git
3. CI/CD automatically syncs to Braintrust via `npx braintrust push`
4. Braintrust links all traces to prompt versions
"""

import json
from typing import Dict, Optional


class ArticleAnalysisPrompt:
    """
    Main  prompt for analyzing articles and generating structured summaries

    This prompt handles three content types:
    - Video content (with YouTube transcripts)
    - Audio content (with audio transcripts)
    - Text-only articles

    Output: Structured JSON with summary, key_insights, quotes, timestamps, etc.
    """

    # Braintrust metadata
    SLUG = "article-analysis"
    NAME = "Article Analysis"
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 8000

    @staticmethod
    def build(url: str, media_context: str, metadata: Dict) -> str:
        """
        Build the complete analysis prompt with all context

        Args:
            url: Article URL being analyzed
            media_context: Context string (video/audio/text specific)
            metadata: Article metadata dictionary

        Returns:
            Complete prompt string ready for Claude API
        """
        # Determine media type for prompt customization
        content_type = metadata.get('content_type')

        if hasattr(content_type, 'has_embedded_video') and content_type.has_embedded_video:
            media_type_indicator = "video"
            jump_function = "jumpToTime"
        elif hasattr(content_type, 'has_embedded_audio') and content_type.has_embedded_audio:
            media_type_indicator = "audio"
            jump_function = "jumpToAudioTime"
        else:
            media_type_indicator = "content"
            jump_function = "jumpToTime"

        return f"""
Analyze this article: {url}

Create a comprehensive summary with the following structure:
1. Write a clear, structured summary (2-4 paragraphs) in HTML format as paragraphs (NOT bullets)
2. Extract 8-12 key insights combining main points, insights, and actionable takeaways
3. If video/audio content exists, identify specific timestamps with detailed descriptions

{media_context}

Article metadata: {json.dumps(metadata, indent=2)}

Return your response in this JSON format:
{{
    "summary": "HTML formatted summary in paragraph form (2-4 paragraphs, NOT bullets). Use <p> tags for paragraphs.",
    "key_insights": [
        {{"insight": "Key insight, main point, or actionable takeaway", "timestamp_seconds": 300, "time_formatted": "5:00"}},
        {{"insight": "Another insight without timestamp", "timestamp_seconds": null, "time_formatted": null}}
    ],
    "quotes": [
        {{"quote": "Exact quote text", "speaker": "Speaker name", "timestamp_seconds": 120, "time_formatted": "2:00", "context": "Context for the quote"}}
    ],
    "duration_minutes": 45,
    "word_count": 5000,
    "topics": ["AI", "Product", "Engineering"]
}}

CRITICAL TIMESTAMP RULES:
- Each timestamp section should cover AT LEAST 30 SECONDS of continuous content
- Each description should include COMPLETE SENTENCES and full thoughts - never break mid-sentence
- Group related ideas that span 30-60 seconds into a single timestamp entry with comprehensive description
- Provide detailed summaries that capture the full context of what's discussed in that 30+ second window
- Use null for timestamp_seconds and time_formatted if you cannot find the EXACT content in the provided transcript
- NEVER guess or estimate timestamps - if you can't find it in the transcript, use null
- For quotes: search the transcript for the exact quote text and use that timestamp
- For insights: provide comprehensive descriptions that summarize the complete topic discussed in that 30+ second section
- Only include timestamps for content you can find in the provided transcript
- If transcript is truncated, only use timestamps from the visible portion
- key_insights should be 8-12 items combining key learnings, main points, and actionable takeaways
- Each insight with a timestamp should describe the complete topic/discussion in that time window, not just a single point
- quotes should be memorable/important quotes with exact speaker attribution and context
"""


class VideoContextBuilder:
    """Build context string for video content with transcripts"""

    @staticmethod
    def build(metadata: Dict, max_transcript_chars: int = 150000) -> str:
        """
        Build video analysis context

        Args:
            metadata: Article metadata with video_urls and transcripts
            max_transcript_chars: Maximum characters to include from transcript

        Returns:
            Formatted context string for video content
        """
        video_urls = metadata.get('media_info', {}).get('youtube_urls', [])
        transcripts = metadata.get('transcripts', {})
        article_text = metadata.get('article_text', 'Content not available')

        # Check if we have any successful transcripts
        has_transcript_data = False
        transcript_content = ""

        if transcripts:
            for video_id, transcript_data in transcripts.items():
                if transcript_data.get('success'):
                    formatted_transcript = VideoContextBuilder._format_transcript(transcript_data)
                    if formatted_transcript:
                        has_transcript_data = True
                        truncated = formatted_transcript[:max_transcript_chars]
                        if len(formatted_transcript) > max_transcript_chars:
                            truncated += "..."

                        transcript_content += f"""

VIDEO TRANSCRIPT for {video_id} ({transcript_data.get('type', 'unknown')} transcript):
{truncated}
"""

        # Build context based on whether we have transcript data
        if has_transcript_data:
            return f"""
IMPORTANT: This article contains video content. Video URLs found: {video_urls}
Please focus on extracting video timestamps with the following format:
- Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
- Provide detailed descriptions of what happens at each timestamp
- Aim for 5-8 key timestamps that represent the most valuable content
- Include timestamps for: key insights, important discussions, actionable advice, demonstrations
{transcript_content}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze both the article text and the video transcript to provide comprehensive insights.
"""
        else:
            return f"""
IMPORTANT: This article contains video content. Video URLs found: {video_urls}
Note: No video transcripts are available, so please focus on the article content itself.
DO NOT include any timestamps or time-based references in your response.
- Focus on key insights and takeaways mentioned in the article text
- Extract actionable advice from the article content
- Identify main themes and discussion points referenced in the article
- Base your analysis only on the article text, not on video content

ARTICLE TEXT CONTENT:
{article_text}
"""

    @staticmethod
    def _format_transcript(transcript_data: Dict) -> str:
        """Format transcript for AI analysis (line-by-line)"""
        if not transcript_data or not transcript_data.get('success'):
            return ""

        transcript = transcript_data.get('transcript', [])
        formatted_text = []

        for entry in transcript:
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            # Convert seconds to MM:SS format
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"

            if text:
                formatted_text.append(f"[{timestamp}] {text}")

        return "\n".join(formatted_text)


class AudioContextBuilder:
    """Build context string for audio content with transcripts"""

    @staticmethod
    def build(metadata: Dict, max_transcript_chars: int = 150000) -> str:
        """
        Build audio analysis context

        Args:
            metadata: Article metadata with audio_urls and transcripts
            max_transcript_chars: Maximum characters to include from transcript

        Returns:
            Formatted context string for audio content
        """
        audio_urls = metadata.get('media_info', {}).get('audio_urls', [])
        transcripts = metadata.get('transcripts', {})
        article_text = metadata.get('article_text', 'Content not available')

        # Check if we have any successful transcripts
        has_transcript_data = False
        transcript_content = ""

        if transcripts:
            for audio_id, transcript_data in transcripts.items():
                if transcript_data.get('success'):
                    formatted_transcript = AudioContextBuilder._format_transcript(transcript_data)
                    if formatted_transcript:
                        has_transcript_data = True
                        truncated = formatted_transcript[:max_transcript_chars]
                        if len(formatted_transcript) > max_transcript_chars:
                            truncated += "..."

                        transcript_content += f"""

AUDIO TRANSCRIPT for {audio_id} ({transcript_data.get('type', 'unknown')} transcript):
{truncated}
"""

        # Build context based on whether we have transcript data
        if has_transcript_data:
            return f"""
IMPORTANT: This article contains audio/podcast content. Audio URLs found: {audio_urls}
Please focus on extracting audio timestamps with the following format:
- Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
- Provide detailed descriptions of what is discussed at each timestamp
- Aim for 5-8 key timestamps that represent the most valuable content
- Include timestamps for: key insights, important discussions, actionable advice, main themes
Audio Platform: {audio_urls[0]['platform'] if audio_urls else 'unknown'}
{transcript_content}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze both the article text and the audio transcript to provide comprehensive insights.
"""
        else:
            return f"""
IMPORTANT: This article contains audio/podcast content. Audio URLs found: {audio_urls}
Note: No audio transcripts are available, so please focus on the article content itself.
DO NOT include any timestamps or time-based references in your response.
- Focus on key insights and takeaways mentioned in the article text
- Extract actionable advice from the article content
- Identify main themes and discussion points referenced in the article
- Note the participants/speakers if mentioned in the content
- Base your analysis only on the article text, not on audio content
Audio Platform: {audio_urls[0]['platform'] if audio_urls else 'unknown'}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze the article text to provide comprehensive insights about the audio content.
"""

    @staticmethod
    def _format_transcript(transcript_data: Dict) -> str:
        """Format transcript for AI analysis (line-by-line)"""
        if not transcript_data or not transcript_data.get('success'):
            return ""

        transcript = transcript_data.get('transcript', [])
        formatted_text = []

        for entry in transcript:
            start_time = entry.get('start', 0)
            text = entry.get('text', '').strip()

            # Convert seconds to MM:SS format
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = f"{minutes}:{seconds:02d}"

            if text:
                formatted_text.append(f"[{timestamp}] {text}")

        return "\n".join(formatted_text)


class TextContextBuilder:
    """Build context string for text-only content"""

    @staticmethod
    def build(metadata: Dict) -> str:
        """
        Build text-only analysis context

        Args:
            metadata: Article metadata

        Returns:
            Formatted context string for text content
        """
        article_text = metadata.get('article_text', 'Content not available')

        return f"""
IMPORTANT: This is a TEXT-ONLY article with no video or audio content.
For text-only articles, please focus on:
- Extracting key insights from the written content
- Identifying main themes and arguments
- Summarizing actionable takeaways
- Highlighting important quotes or data points
- Structuring the content logically with clear headings
- NO timestamps should be included (since there's no media)

Article text content: {article_text}
"""


class ChatAssistantPrompt:
    """
    Prompt for chat assistant that answers questions based on article context

    This is a RAG (Retrieval Augmented Generation) pattern where we:
    1. Search for relevant articles semantically
    2. Build context from top articles
    3. Answer user questions based on that context
    """

    # Braintrust metadata
    SLUG = "chat-assistant"
    NAME = "Chat Assistant"
    MODEL = "gpt-4-turbo-preview"

    @staticmethod
    def build_system_message(context: list) -> str:
        """
        Build system message for chat assistant

        Args:
            context: List of article dictionaries with title, summary, insights, etc.

        Returns:
            System message string
        """
        return f"""You are a helpful AI assistant that answers questions based on article summaries and transcripts.

Context from relevant articles:
{json.dumps(context, indent=2)}

Guidelines:
- Answer questions based on the provided context from articles
- Cite articles by their title when referencing specific information
- If the context doesn't contain relevant information to answer the question, politely say so
- Be conversational, helpful, and concise
- Use markdown formatting for better readability
- If asked about sources, refer to the article titles provided in context"""


# Utility function to simplify metadata for prompts
def create_metadata_for_prompt(metadata: Dict) -> Dict:
    """
    Create simplified metadata dictionary for AI prompts

    Args:
        metadata: Full article metadata

    Returns:
        Simplified metadata for prompt inclusion
    """
    content_type = metadata.get('content_type')

    return {
        'title': metadata.get('title'),
        'url': metadata.get('url'),
        'platform': metadata.get('platform'),
        'has_video': hasattr(content_type, 'has_embedded_video') and content_type.has_embedded_video if content_type else False,
        'has_audio': hasattr(content_type, 'has_embedded_audio') and content_type.has_embedded_audio if content_type else False,
        'is_text_only': hasattr(content_type, 'is_text_only') and content_type.is_text_only if content_type else False,
        'extracted_at': metadata.get('extracted_at')
    }
