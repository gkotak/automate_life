"""
Claude Prompts for Earnings Call Analysis

Contains prompts for extracting structured insights from earnings call transcripts.
"""

EARNINGS_INSIGHTS_PROMPT = """
You are analyzing an earnings call transcript with timestamps. The transcript format is:
[MM:SS] Speaker: Text content

Example:
[00:45] CEO: We delivered record revenue of $52.3 billion, up 15% year-over-year...
[05:30] CFO: Our operating margins expanded to 28%, the highest in company history...
[12:15] Analyst - Goldman Sachs: Can you discuss the sustainability of these margins?

Your task is to extract structured insights from this earnings call transcript.

Extract the following insights as JSON:

{{
  "key_metrics": {{
    // Financial highlights with timestamps (revenue growth, profitability, margins, etc.)
    // Structure: {{"metric_name": {{"value": "...", "timestamp": "05:30", "speaker": "CFO"}}}}
    // Examples:
    "revenue_growth": {{
      "value": "15% year-over-year to $52.3B",
      "timestamp": "00:45",
      "speaker": "CEO"
    }},
    "operating_margin": {{
      "value": "Expanded to 28%, highest ever",
      "timestamp": "05:30",
      "speaker": "CFO"
    }}
  }},

  "business_highlights": [
    // Key business updates (NOT financial metrics - those go in key_metrics)
    // Examples: product launches, partnerships, expansions, strategic initiatives
    {{
      "text": "Launched new AI assistant with 50 million active users in first month",
      "timestamp": "03:20",
      "speaker": "CEO"
    }},
    {{
      "text": "Completed acquisition of XYZ Corp to expand cloud capabilities",
      "timestamp": "07:15",
      "speaker": "CEO"
    }}
  ],

  "guidance": {{
    // Forward-looking statements from management about future quarters/years
    // Structure: {{"metric_name": {{"value": "...", "timestamp": "...", "speaker": "..."}}}}
    "q3_revenue": {{
      "value": "Expected between $54B - $56B",
      "timestamp": "08:45",
      "speaker": "CFO"
    }},
    "fy_capex": {{
      "value": "Increasing to $50B to support AI infrastructure",
      "timestamp": "09:20",
      "speaker": "CFO"
    }}
  }},

  "risks_concerns": [
    // ANY concerns mentioned - by management in prepared remarks OR raised by analysts in Q&A
    // Use "context" field to distinguish: "management_remark" vs "analyst_question"
    {{
      "text": "Increased competitive pressure from new entrants with aggressive pricing",
      "timestamp": "10:30",
      "speaker": "CEO",
      "context": "management_remark"
    }},
    {{
      "text": "Analyst questioned sustainability of margin expansion given increased AI R&D spending",
      "timestamp": "12:15",
      "speaker": "Analyst - Goldman Sachs",
      "context": "analyst_question"
    }},
    {{
      "text": "Supply chain constraints expected to persist into Q3",
      "timestamp": "13:40",
      "speaker": "CFO",
      "context": "management_remark"
    }}
  ],

  "positives": [
    // Positive developments, achievements, strengths highlighted
    // Examples: records broken, successful initiatives, competitive advantages
    {{
      "text": "Operating margins reached 28%, highest in company history",
      "timestamp": "05:30",
      "speaker": "CFO"
    }},
    {{
      "text": "Customer retention improved to 95%, highest in industry",
      "timestamp": "06:45",
      "speaker": "CEO"
    }},
    {{
      "text": "Successfully reduced operating expenses by 10% while growing revenue",
      "timestamp": "08:10",
      "speaker": "CFO"
    }}
  ],

  "notable_quotes": [
    // Memorable, impactful quotes that capture key themes or strong statements
    // 3-5 quotes that are particularly insightful or revealing
    {{
      "quote": "We're not just riding the AI wave, we're building the infrastructure that powers it",
      "timestamp": "15:45",
      "speaker": "CEO",
      "context": "strategic_vision"
    }},
    {{
      "quote": "Our disciplined capital allocation has allowed us to invest heavily in growth while returning record cash to shareholders",
      "timestamp": "18:20",
      "speaker": "CFO",
      "context": "financial_strategy"
    }}
  ]]
}}

IMPORTANT RULES:
1. **Use EXACT timestamps from the transcript** - do NOT guess, estimate, or make up timestamps
2. If a metric/highlight appears in the transcript, it MUST include its timestamp
3. For risks_concerns: Use "context" field to distinguish management remarks vs analyst questions
4. Include 3-5 notable quotes that capture key themes or strong statements
5. Be specific and include numbers/percentages where mentioned
6. Keep each text/quote concise but complete (1-3 sentences max)
7. key_metrics = FINANCIAL metrics only (revenue, margins, cash flow, etc.)
8. business_highlights = NON-FINANCIAL updates (products, markets, deals, etc.)
9. If a section has no relevant information, return empty object {{}} or empty array []
10. Ensure valid JSON format - use double quotes, escape special characters

Now extract from this timestamped earnings call transcript:

{transcript}
"""


def format_earnings_prompt(transcript_with_timestamps: str) -> str:
    """
    Format the earnings insights prompt with the transcript

    Args:
        transcript_with_timestamps: Formatted transcript with [MM:SS] timestamps

    Returns:
        Complete prompt ready for Claude
    """
    return EARNINGS_INSIGHTS_PROMPT.format(transcript=transcript_with_timestamps)
