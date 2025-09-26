# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code configuration repository that automates newsletter research and content creation through a specialized agent system. The project consists of custom slash commands, specialized subagents, and an organized workflow for analyzing competitor newsletters and generating compelling newsletter drafts.

## Key Commands

### Newsletter Research Workflow
- `/newsletter-research` - Initiates the complete newsletter research and writing workflow
  - Validates newsletter links exist in `.claude/newsletter/newsletter links.md`
  - Creates timestamped research session
  - Outputs newsletter URLs for agent processing
  - Sets up directory structure for saving results

### Required Setup
Before running `/newsletter-research`:
1. Ensure `.claude/newsletter/newsletter links.md` exists with actual newsletter URLs
2. Replace placeholder URLs with real competitor and industry leader newsletters
3. Have login credentials ready for any paid newsletter subscriptions

## Architecture Overview

### Core System Components

**Slash Commands** (`.claude/commands/`)
- `newsletter-research.js` - Main orchestrator that initializes the workflow and validates setup

**Specialized Agents** (`.claude/agents/`)
- `content-researcher.js` - Analyzes competitor newsletters for trending topics and content gaps
- `newsletter-writer.js` - Creates compelling newsletter drafts with subject lines

**Workflow Documentation**
- `.claude/newsletter-research-system.md` - Complete implementation guide with agent prompts and success criteria

### Agent System Architecture

The system uses a two-stage agent workflow:

1. **Content Research Phase**: `content-researcher` agent fetches recent posts from newsletter URLs, identifies 5-7 trending topics, finds content gaps, and creates structured research reports
2. **Content Creation Phase**: `newsletter-writer` agent uses research insights to create 3 subject line options and 500-800 word newsletter drafts

### File Organization

**Newsletter Content Structure**:
```
.claude/newsletter/
├── newsletter links.md          # Newsletter URLs to analyze
├── research/YYYY-MM-DD-research.md     # Research reports by date
└── drafts/YYYY-MM-DD-newsletter-draft.md # Newsletter drafts by date
```

**Configuration**:
```
.claude/
├── settings.local.json         # Claude Code permissions
├── agents/                     # Specialized subagents
├── commands/                   # Custom slash commands
└── newsletter-research-system.md # Complete workflow guide
```

### Agent Execution Flow

1. Run `/newsletter-research` to initialize and get newsletter URLs
2. Launch content-researcher agent with newsletter URLs from slash command output
3. Launch newsletter-writer agent with research findings from step 2
4. Results are saved with consistent timestamp formatting (YYYY-MM-DD)

### Content Standards

**Research Output**: Trending topics with evidence, content gaps, time-sensitive angles, competitor analysis
**Newsletter Output**: 3 subject lines under 50 characters, 500-800 word drafts with hooks, insights, practical takeaways, conversational tone

## Development Notes

- All agents are Node.js modules that export descriptions and metadata
- The system prioritizes authentic, value-first content over promotional content
- Newsletter links file must contain real URLs for effective research
- Timestamps follow YYYY-MM-DD format for consistent file organization
- Focus is on creating newsletters people want to forward to friends