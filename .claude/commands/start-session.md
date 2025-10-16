Ask the user: "What are you working on?" (to name the branch descriptively).

If they provide a description, run:
```bash
source .claude/hooks/session-start.sh "their-description"
```

If they don't provide one, run:
```bash
source .claude/hooks/session-start.sh
```

Examples:
- User says "environment variables" → run: `source .claude/hooks/session-start.sh "env-vars"`
- User says "fixing docs" → run: `source .claude/hooks/session-start.sh "fix-docs"`
- User says "nothing specific" → run: `source .claude/hooks/session-start.sh`

Then tell the user:
1. What branch was created
2. That all commits in this session will go to that branch
3. How to check their branch later: `git branch --show-current` or `/check-branch`
