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

        # Check if we have video frames that need summaries
        video_frames = metadata.get('video_frames', [])
        frame_summaries_section = ""

        if video_frames:
            frame_summaries_section = ',\n    "frame_summaries": [\n        {"frame_index": 0, "summary": "10-word summary of what happens at this timestamp"},\n        {"frame_index": 1, "summary": "Another 10-word summary"}\n    ]'

        return f"""
Analyze this article: {url}

Create a comprehensive summary with the following structure:
1. Write a clear, structured summary (2-4 paragraphs) in HTML format as paragraphs (NOT bullets)
2. Extract 5-10 key insights combining main points, insights, and actionable takeaways
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
    "topics": ["AI", "Product", "Engineering"]{frame_summaries_section}
}}

CRITICAL TIMESTAMP RULES:
- Use PRECISE timestamps from the transcript - find the exact moment where the insight/quote begins
- Search the transcript for the specific phrase or concept and use that exact timestamp
- Use null for timestamp_seconds and time_formatted if you cannot find the EXACT content in the provided transcript
- NEVER guess or estimate timestamps - if you can't find it in the transcript, use null
- For quotes: find the transcript timestamp where the quote appears, then SUBTRACT 3 seconds to ensure playback starts slightly before the quote (e.g., if quote is at [22:38], use 22:35 / "22:35")
- For insights: identify where the key concept or discussion begins and use that timestamp
- Only include timestamps for content you can find in the provided transcript
- If transcript is truncated, only use timestamps from the visible portion
- key_insights should be 5-10 items combining key learnings, main points, and actionable takeaways
- Each insight should be a clear, concise statement of the key learning or takeaway
- quotes should be memorable/important quotes with exact speaker attribution
- For quotes: include at least 30 seconds of surrounding context in the "context" field to give users sufficient background
"""


class MediaContextBuilder:
    """Unified builder for all media content (video/audio) with transcripts"""

    @staticmethod
    def build(metadata: Dict, max_transcript_chars: int = 150000) -> str:
        """
        Build media analysis context for video or audio content

        Args:
            metadata: Article metadata with media URLs and transcripts
            max_transcript_chars: Maximum characters to include from transcript

        Returns:
            Formatted context string for media content
        """
        # Get all media URLs and determine media type
        media_info = metadata.get('media_info', {})
        media_urls = []
        media_type = 'media'  # default fallback
        platform = 'unknown'

        # Collect all media URLs and determine type
        for key in media_info.keys():
            if key.endswith('_urls'):
                urls = media_info[key]
                if not urls:  # Skip empty lists
                    continue
                media_urls.extend(urls)
                # Determine type from key (e.g., 'video_urls' -> 'video', 'audio_urls' -> 'audio')
                if 'video' in key:
                    media_type = 'video'
                elif 'audio' in key:
                    media_type = 'audio'
                # Get platform from first URL if available
                if urls and 'platform' in urls[0]:
                    platform = urls[0]['platform']

        transcripts = metadata.get('transcripts', {})
        article_text = metadata.get('article_text', 'Content not available')

        # Check if we have any successful transcripts
        has_transcript_data = False
        transcript_content = ""

        if transcripts:
            for media_id, transcript_data in transcripts.items():
                if transcript_data.get('success'):
                    formatted_transcript = MediaContextBuilder._format_transcript(transcript_data)
                    if formatted_transcript:
                        has_transcript_data = True
                        truncated = formatted_transcript[:max_transcript_chars]
                        if len(formatted_transcript) > max_transcript_chars:
                            truncated += "..."

                        transcript_content += f"""

{media_type.upper()} TRANSCRIPT for {media_id} ({transcript_data.get('type', 'unknown')} transcript):
{truncated}
"""

        # Customize wording based on media type
        action_word = "happens" if media_type == 'video' else "is discussed"
        extra_detail = "demonstrations" if media_type == 'video' else "main themes"
        platform_line = f"{media_type.capitalize()} Platform: {platform}\n" if media_type == 'audio' else ""

        # Check if we have video frames with transcript excerpts
        video_frames = metadata.get('video_frames', [])
        frames_section = ""

        if video_frames and media_type == 'video':
            frames_data = []
            for i, frame in enumerate(video_frames):
                excerpt = frame.get('transcript_excerpt', '')
                if excerpt:
                    frames_data.append({
                        "frame_index": i,
                        "timestamp": frame.get('time_formatted', ''),
                        "transcript_excerpt": excerpt
                    })

            if frames_data:
                frames_section = f"""

VIDEO FRAMES FOR SUMMARY GENERATION:
The following video frames have been extracted at key moments. For each frame, generate a concise 10-word (maximum) summary based on its transcript excerpt:

{json.dumps(frames_data, indent=2)}

IMPORTANT: You MUST include a "frame_summaries" array in your response with exactly {len(frames_data)} entries.
Each entry should have:
- "frame_index": The index number from above (0, 1, 2, etc.)
- "summary": A natural, concise summary of NO MORE THAN 10 words describing what happens at this timestamp

Example frame_summaries format:
[
    {{"frame_index": 0, "summary": "Platform demo showing AI procurement features and integrations"}},
    {{"frame_index": 1, "summary": "Discussion of customer results and time savings achieved"}}
]
"""

        # Build context based on whether we have transcript data
        if has_transcript_data:
            return f"""
IMPORTANT: This article contains {media_type}/podcast content. {media_type.capitalize()} URLs found: {media_urls}
Please focus on extracting {media_type} timestamps with the following format:
- Use MM:SS format for timestamps (e.g., "5:23", "12:45", "1:02:30")
- Provide detailed descriptions of what {action_word} at each timestamp
- Aim for 5-8 key timestamps that represent the most valuable content
- Include timestamps for: key insights, important discussions, actionable advice, {extra_detail}
{platform_line}{transcript_content}{frames_section}

ARTICLE TEXT CONTENT:
{article_text}

Please analyze both the article text and the {media_type} transcript to provide comprehensive insights.
"""
        else:
            speaker_note = "\n- Note the participants/speakers if mentioned in the content" if media_type == 'audio' else ""
            return f"""
IMPORTANT: This article contains {media_type}/podcast content. {media_type.capitalize()} URLs found: {media_urls}
Note: No {media_type} transcripts are available, so please focus on the article content itself.
DO NOT include any timestamps or time-based references in your response.
- Focus on key insights and takeaways mentioned in the article text
- Extract actionable advice from the article content
- Identify main themes and discussion points referenced in the article{speaker_note}
- Base your analysis only on the article text, not on {media_type} content
{platform_line}
ARTICLE TEXT CONTENT:
{article_text}

Please analyze the article text to provide comprehensive insights about the {media_type} content.
"""

    @staticmethod
    def _format_transcript(transcript_data: Dict, interval_seconds: int = 3) -> str:
        """
        Format transcript for AI analysis with granular timestamps

        Uses word-level timing data to create transcript segments every N seconds
        for precise timestamp lookup by AI. Falls back to segment-level if word
        data is not available.

        Args:
            transcript_data: Transcript data from DeepGram or YouTube
            interval_seconds: Interval between timestamps (default: 3 seconds)

        Returns:
            Formatted transcript with timestamps every N seconds
        """
        if not transcript_data or not transcript_data.get('success'):
            return ""

        # Try to use word-level data first (DeepGram)
        words = transcript_data.get('words', [])

        if words:
            # Use word-level data for granular timestamps
            # Group words into intervals but use ACTUAL first word start time for accuracy
            formatted_text = []
            interval_start_time = None  # Actual start time of first word in interval
            interval_boundary = 0  # Used for interval boundary checking
            current_words = []

            for word_data in words:
                word = word_data.get('word', '')
                word_start = word_data.get('start', 0)

                # Check if we've passed the next interval boundary
                if word_start >= interval_boundary + interval_seconds and current_words:
                    # Format and save this interval using the ACTUAL first word's timestamp
                    minutes = int(interval_start_time // 60)
                    seconds = int(interval_start_time % 60)
                    timestamp = f"{minutes}:{seconds:02d}"
                    text = ' '.join(current_words)
                    formatted_text.append(f"[{timestamp}] {text}")

                    # Move to next interval
                    interval_boundary = int(word_start // interval_seconds) * interval_seconds
                    interval_start_time = word_start  # Track actual start of new interval
                    current_words = []

                # Track actual start time of first word in this interval
                if interval_start_time is None:
                    interval_start_time = word_start

                current_words.append(word)

            # Add final interval
            if current_words and interval_start_time is not None:
                minutes = int(interval_start_time // 60)
                seconds = int(interval_start_time % 60)
                timestamp = f"{minutes}:{seconds:02d}"
                text = ' '.join(current_words)
                formatted_text.append(f"[{timestamp}] {text}")

            return "\n".join(formatted_text)

        else:
            # Fallback to segment-level (YouTube or old format)
            transcript = transcript_data.get('transcript', transcript_data.get('segments', []))
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


# Keep backward compatibility aliases
VideoContextBuilder = MediaContextBuilder
AudioContextBuilder = MediaContextBuilder


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
- Structuring the content logically
- NO timestamps should be included (since there's no media)
- DO NOT include quotes section - text articles don't have attributed speakers like video/audio

Article text content: {article_text}
"""


class ThemedInsightsPrompt:
    """
    Prompt for generating theme-specific insights from article content

    Organizational themes are strategic categories (e.g., "Competition", "International Expansion")
    that help users analyze content through specific lenses relevant to their organization.

    Output: JSON with insights grouped by theme
    """

    # Braintrust metadata
    SLUG = "themed-insights"
    NAME = "Themed Insights"
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4000

    @staticmethod
    def build(themes: list, transcript_text: str, article_summary: str) -> str:
        """
        Build the themed insights prompt

        Args:
            themes: List of theme dicts with 'name' and optional 'description' keys,
                    or list of theme name strings for backwards compatibility
            transcript_text: Full transcript or article text
            article_summary: The general summary already generated for this article

        Returns:
            Complete prompt string ready for Claude API
        """
        # Build themes list with descriptions if available
        themes_lines = []
        for theme in themes:
            if isinstance(theme, dict):
                name = theme.get('name', '')
                description = theme.get('description', '')
                if description:
                    themes_lines.append(f"- {name}: {description}")
                else:
                    themes_lines.append(f"- {name}")
            else:
                # Backwards compatibility: theme is just a string name
                themes_lines.append(f"- {theme}")

        themes_list = "\n".join(themes_lines)

        return f"""Analyze the following content and extract insights that are specifically relevant to each of the provided organizational themes.

IMPORTANT GUIDELINES:
- Do NOT force-fit insights. If a theme has no relevant content, return an empty array for that theme.
- Only include genuinely relevant insights - not tangentially related content.
- Each insight should provide actionable, specific information relevant to the theme.
- Include timestamps when the insight can be tied to a specific moment in the transcript.
- The same content can appear as both a general insight AND a themed insight if genuinely relevant.
- It is completely acceptable to return empty arrays for themes that aren't discussed in the content.
- Pay close attention to theme descriptions - they provide context on what to look for (e.g., specific companies, focus areas, keywords).

ORGANIZATIONAL THEMES TO ANALYZE:
{themes_list}

ARTICLE SUMMARY:
{article_summary}

TRANSCRIPT/SOURCE TEXT:
{transcript_text[:100000]}

Return your response in this exact JSON format:
{{
    "themed_insights": {{
        "Theme Name 1": [
            {{"insight_text": "Specific insight relevant to this theme", "timestamp_seconds": 300, "time_formatted": "5:00"}},
            {{"insight_text": "Another insight without timestamp", "timestamp_seconds": null, "time_formatted": null}}
        ],
        "Theme Name 2": []
    }}
}}

TIMESTAMP RULES:
- Use PRECISE timestamps from the transcript when you can identify where the insight is discussed
- Use null for timestamp_seconds and time_formatted if the insight is derived from general context
- NEVER guess or estimate timestamps - if you can't find it precisely, use null
- Search the transcript for the specific phrase or concept and use that exact timestamp

QUALITY GUIDELINES:
- Focus on insights that would help someone understand the content through the lens of each theme
- Prioritize actionable, concrete insights over vague observations
- Include specific names, numbers, or details when available
- Each insight should stand alone as a meaningful piece of information
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
        'extracted_at': metadata.get('extracted_at'),
        'video_frames': metadata.get('video_frames', [])  # Include video frames for prompt generation
    }
