---
description: Intelligent git commit and push with AI-powered code review and commit message generation
---

# Intelligent Git Commit and Push

You are helping the user commit and push changes to GitHub with AI assistance.

## Step 1: Identify Changes

First, run `git status` to see all uncommitted changes (modified, added, deleted, and untracked files).

## Step 2: Analyze Changes with Context

For each file that has changes:
1. Use `git diff` to see the actual changes for modified files
2. Read new/untracked files to understand what they add
3. Consider the file's location and purpose in the overall codebase structure
4. Review the CLAUDE.md file to understand project context and standards

## Step 3: AI Code Review

Codex now runs automatically via the pre-commit hook (`scripts/run_codex_review.sh`) and stores the latest report in `.codex/last_review.md`.

1. If the review file exists, read it and summarize the findings for the user with the usual ✅ / ⚠️ / 💡 callouts.
2. If the file is missing or the user requests a fresh review, rerun `scripts/run_codex_review.sh` (it respects `SKIP_CODEX=1` when a bypass is needed, especially if it take more than 90 seconds.
3. Highlight any 🔥 blockers that Codex surfaced, since the hook will stop the commit until they are resolved. 
4. if you feel the blocker is not really a blocker, ask me to review it, and go ahead with skipping codex if i say yes. 

Ask: "Would you like me to proceed with commit despite codex saying it is a blocker"

## Step 4: Generate Commit Message

Based on the changes and code review, draft a comprehensive commit message following this format:

```
<Title: Clear, concise summary (50 chars max)>

<Blank line>

<Body: Detailed description of changes, organized by category>
- Feature additions
- Bug fixes
- Refactoring
- Documentation updates
- Configuration changes

<Blank line>

Key Changes:
- Specific change 1
- Specific change 2
- Specific change 3

<Blank line>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Guidelines for commit messages:
- Title should be imperative mood ("Add feature" not "Added feature")
- Group related changes together
- Explain WHY changes were made, not just WHAT
- Include impact on functionality
- Reference any relevant context from CLAUDE.md

## Step 5: Present for Review

Show the user:
1. List of files to be committed
2. Code review summary
3. Proposed commit message

Ask: "Would you like me to proceed with this commit message, or would you like to modify it?"

## Step 6: Commit and Push

Once approved:
1. Stage all changes: `git add -A`
2. Create commit with the approved message
3. Push to remote: `git push`
4. Confirm success with the commit hash and push result

## Important Notes

- NEVER commit sensitive files (.env, credentials, tokens, etc.) - warn the user if detected
- If there are merge conflicts or push fails, explain the error and suggest next steps
- Consider the size of changes - if very large, suggest splitting into multiple commits
- Check if on the correct branch before pushing
- Verify remote repository is set up correctly

## Error Handling

If any step fails:
- Explain what went wrong clearly
- Suggest corrective actions
- Don't proceed to next steps until resolved
