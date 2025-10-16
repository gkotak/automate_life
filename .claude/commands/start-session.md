Execute the session start script to create a new git branch for this session:

```bash
source .claude/hooks/session-start.sh "$ARGUMENTS"
```

**If user provided arguments:**
- `/start-session env-vars` → Creates `agent/env-vars-TIMESTAMP-ID`
- `/start-session fix-docs` → Creates `agent/fix-docs-TIMESTAMP-ID`

**If no arguments (empty):**
- `/start-session` → Ask: "What are you working on? (Press Enter to skip for random name)"
- If they provide description, run with that description
- If they press Enter or skip, run: `source .claude/hooks/session-start.sh` (creates `agent/work-TIMESTAMP-ID`)

Then tell the user:
1. What branch was created (show the full branch name)
2. That all commits in this session will go to that branch
3. Remind them: "End session with: /end-session"
