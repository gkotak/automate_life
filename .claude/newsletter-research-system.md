# Newsletter Research System Implementation Guide

This document provides Claude with the complete workflow for executing the newsletter research system.

## System Overview

The newsletter research system consists of:

1. **`/newsletter-research` slash command**: Initializes the workflow and validates setup
2. **content-researcher agent**: Analyzes competitor newsletters for trends and opportunities
3. **newsletter-writer agent**: Creates compelling drafts with subject lines
4. **Organized file structure**: Saves research and drafts with timestamps

## Workflow Execution Steps

### Step 1: Slash Command Execution
When `/newsletter-research` is run:
- Validates newsletter links exist
- Creates necessary directories
- Outputs newsletter URLs for analysis
- Provides research session ID (timestamp)

### Step 2: Content Research Phase
Launch the content-researcher agent with this prompt:

```
You are the content-researcher agent. Your task is to analyze the provided newsletter URLs and identify trending topics, content gaps, and opportunities.

Newsletter URLs to analyze:
[INSERT NEWSLETTER URLS FROM SLASH COMMAND OUTPUT]

Please:
1. Fetch recent posts from each newsletter URL (last 2-3 issues if possible)
2. Identify 5-7 trending topics across all sources
3. Find content gaps not being addressed by competitors
4. Identify time-sensitive angles or opportunities
5. Create a structured research report

Focus on actionable insights that can become compelling newsletter content.
Save your research to .claude/newsletter/research/YYYY-MM-DD-research.md
```

### Step 3: Newsletter Writing Phase
Launch the newsletter-writer agent with this prompt:

```
You are the newsletter-writer agent. Based on the content research findings, create a compelling newsletter draft.

Content Research Insights:
[INSERT RESEARCH FINDINGS FROM STEP 2]

Please create:
1. 3 compelling subject line options (under 50 chars, curiosity-driven)
2. A complete 500-800 word newsletter draft with:
   - Hook that connects to current trends
   - Personal insight or contrarian take
   - 2-3 practical takeaways
   - Conversational, authentic tone
   - Natural soft CTA if relevant

Analyze the user's existing newsletter content first to match their voice and style.
Save the draft to .claude/newsletter/drafts/YYYY-MM-DD-newsletter-draft.md
```

### Step 4: File Organization
- Research files: `.claude/newsletter/research/YYYY-MM-DD-research.md`
- Draft files: `.claude/newsletter/drafts/YYYY-MM-DD-newsletter-draft.md`
- Use consistent timestamp format from slash command

## Agent Characteristics

### Content Researcher
- Focuses on trend analysis and competitive intelligence
- Identifies content opportunities and gaps
- Provides data-driven insights
- Highlights time-sensitive angles

### Newsletter Writer
- Creates authentic, conversational content
- Writes curiosity-driven subject lines
- Includes practical, actionable advice
- Matches user's existing voice and style
- Avoids AI-generated tone

## Success Criteria

The system should produce:
- ✅ Comprehensive trend analysis from multiple sources
- ✅ 3 subject line options that create curiosity
- ✅ 500-800 word draft ready to send
- ✅ Content that sounds authentic, not AI-generated
- ✅ Practical takeaways readers can act on
- ✅ Organized files with consistent naming

## Usage Notes

- Newsletter links should be in `.claude/newsletter/newsletter links.md`
- User should provide paid subscription access if needed for premium content
- System prioritizes value-first content over promotional content
- Focus on making content that people want to forward to friends