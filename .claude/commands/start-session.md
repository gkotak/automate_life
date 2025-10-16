Check if the user already provided a task description in their message (look for words after "/start-session").

**If they provided a description already:**
Example: "/start-session env-vars" or "start session for fixing docs"
→ Extract the task name and run: `source .claude/hooks/session-start.sh "task-name"`

**If they just said "/start-session" with no description:**
→ Ask: "What are you working on? (Press Enter to skip for random name)"
→ If they provide a description, run: `source .claude/hooks/session-start.sh "their-description"`
→ If they press Enter or say "skip" or "nothing", run: `source .claude/hooks/session-start.sh`

Examples:
- "/start-session env-vars" → run: `source .claude/hooks/session-start.sh "env-vars"`
- "/start-session" then user says "docs" → run: `source .claude/hooks/session-start.sh "docs"`
- "/start-session" then user presses Enter → run: `source .claude/hooks/session-start.sh`
- "Start session for authentication fixes" → run: `source .claude/hooks/session-start.sh "auth-fixes"`

Then tell the user:
1. What branch was created (show the full branch name)
2. That all commits in this session will go to that branch
3. Remind them: "End session with: /end-session"
