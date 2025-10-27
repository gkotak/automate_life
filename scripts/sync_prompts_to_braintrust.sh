#!/bin/bash
#
# Smart Prompt Sync to Braintrust
#
# This script only syncs prompts to Braintrust when they've been modified.
# It uses Git to detect changes, making it efficient and safe.
#
# Usage:
#   ./scripts/sync_prompts_to_braintrust.sh [--force]
#
# Integration:
#   - Git hook: ln -s ../../scripts/sync_prompts_to_braintrust.sh .git/hooks/post-commit
#   - CI/CD: Run this script after code checkout
#   - Manual: Run when you've updated prompts
#
# Environment Variables:
#   BRAINTRUST_API_KEY - Required for syncing to Braintrust
#   SKIP_PROMPT_SYNC - Set to "1" to skip syncing (for local dev)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROMPT_FILES=(
    "programs/article_summarizer_backend/core/prompts.py"
    "web-apps/article-summarizer/src/lib/prompts.ts"
)

# Function to print colored output
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Load environment variables from .env.local if it exists
if [ -f "$PROJECT_ROOT/.env.local" ]; then
    log_info "Loading environment from .env.local"
    set -a  # Automatically export all variables
    source "$PROJECT_ROOT/.env.local"
    set +a
fi

# Check if we should skip sync
if [ "$SKIP_PROMPT_SYNC" = "1" ]; then
    log_warning "SKIP_PROMPT_SYNC is set, skipping sync"
    exit 0
fi

# Check for Braintrust API key
if [ -z "$BRAINTRUST_API_KEY" ]; then
    log_error "BRAINTRUST_API_KEY environment variable not set"
    log_info "Set it in your .env.local or export it before running this script"
    exit 1
fi

# Change to project root
cd "$PROJECT_ROOT"

# Check if running with --force flag
FORCE_SYNC=false
if [ "$1" = "--force" ]; then
    FORCE_SYNC=true
    log_info "Force sync enabled - will sync all prompts regardless of changes"
fi

# Function to check if prompt files have changed
prompts_changed() {
    # If force sync, always return true
    if [ "$FORCE_SYNC" = true ]; then
        return 0
    fi

    # Check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_warning "Not in a git repository, assuming prompts changed"
        return 0
    fi

    # Get the last commit that modified prompt files
    local last_change=$(git log -1 --format="%H" -- "${PROMPT_FILES[@]}" 2>/dev/null)

    if [ -z "$last_change" ]; then
        log_warning "No git history for prompt files, assuming first sync"
        return 0
    fi

    # Check if prompts were modified in the last commit
    if git diff HEAD~1 HEAD --name-only 2>/dev/null | grep -qE "prompts\.(py|ts)"; then
        log_info "Prompt files modified in last commit: $last_change"
        return 0
    fi

    # Check if there are uncommitted changes to prompt files
    if git status --porcelain "${PROMPT_FILES[@]}" 2>/dev/null | grep -q "^.M"; then
        log_warning "Uncommitted changes detected in prompt files"
        return 0
    fi

    # Check tracked but unstaged changes
    if git diff --name-only "${PROMPT_FILES[@]}" 2>/dev/null | grep -qE "prompts\.(py|ts)"; then
        log_warning "Unstaged changes detected in prompt files"
        return 0
    fi

    return 1
}

# Main sync logic
main() {
    log_info "Checking if prompts need syncing..."

    # Check if any prompt files exist
    local files_exist=false
    for file in "${PROMPT_FILES[@]}"; do
        if [ -f "$file" ]; then
            files_exist=true
            break
        fi
    done

    if [ "$files_exist" = false ]; then
        log_warning "No prompt files found at expected locations"
        log_info "Expected files:"
        for file in "${PROMPT_FILES[@]}"; do
            echo "  - $file"
        done
        exit 1
    fi

    # Check if prompts have changed
    if ! prompts_changed; then
        log_success "No changes detected in prompt files, skipping sync"
        log_info "Run with --force to sync anyway"
        exit 0
    fi

    log_info "Changes detected, syncing prompts to Braintrust..."

    # Create Braintrust config directory if it doesn't exist
    mkdir -p .braintrust

    # Create a Node.js script to push TypeScript prompts using Braintrust SDK
    log_info "Pushing TypeScript prompts via Braintrust SDK..."

    cat > web-apps/article-summarizer/push_prompts.mjs << 'TYPESCRIPT_SCRIPT'
import * as braintrust from "braintrust";

async function main() {
  // Initialize project (API key from BRAINTRUST_API_KEY env var)
  const project = braintrust.projects.create({ name: "automate-life" });

  // Create chat assistant prompt
  // Values from src/lib/prompts.ts CHAT_ASSISTANT_METADATA
  project.prompts.create({
    slug: "chat-assistant",
    name: "Chat Assistant",
    description: "RAG chat assistant for article Q&A",
    model: "gpt-4-turbo-preview",
    params: {
      temperature: 0.7,
      max_tokens: 1500,
    },
    messages: [
      {
        role: "system",
        content: `You are a helpful AI assistant that answers questions based on article summaries and transcripts.

Context from relevant articles:
{{{context}}}

Guidelines:
- Answer questions based on the provided context from articles
- Cite articles by their title when referencing specific information
- If the context doesn't contain relevant information to answer the question, politely say so
- Be conversational, helpful, and concise
- Use markdown formatting for better readability
- If asked about sources, refer to the article titles provided in context`,
      },
    ],
    if_exists: "replace",
  });

  // Publish prompts to Braintrust
  await project.publish();
  console.log("✅ TypeScript prompts published to Braintrust");
}

main().catch((error) => {
  console.error("❌ Error pushing TypeScript prompts:", error);
  process.exit(1);
});
TYPESCRIPT_SCRIPT

    # Run the Node.js script from web-apps directory (where node_modules is)
    if command -v node >/dev/null 2>&1; then
        if (cd web-apps/article-summarizer && node push_prompts.mjs 2>&1); then
            log_success "TypeScript prompts pushed successfully"
        else
            log_warning "TypeScript prompt push failed"
        fi
    else
        log_warning "Node.js not found, skipping TypeScript prompt sync"
    fi

    # Create Python script to push Python prompts using Braintrust SDK
    log_info "Pushing Python prompts via Braintrust SDK..."

    cat > .braintrust/push_py_prompts.py << 'PYTHON_SCRIPT'
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
PYTHON_SCRIPT

    chmod +x .braintrust/push_py_prompts.py

    # Run the Python script
    if command -v python3 >/dev/null 2>&1; then
        if python3 .braintrust/push_py_prompts.py 2>&1; then
            log_success "Python prompts pushed successfully"
        else
            log_warning "Python prompt push failed"
        fi
    else
        log_warning "Python not found, skipping Python prompt sync"
    fi

    log_success "Prompts synced to Braintrust successfully!"

    # Record the sync in git notes (optional, for audit trail)
    if git rev-parse --git-dir > /dev/null 2>&1; then
        local commit_hash=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        echo "$timestamp - Synced prompts for commit $commit_hash" >> .braintrust/sync_history.log
        log_info "Sync logged to .braintrust/sync_history.log"
    fi
}

# Run main function
main "$@"
