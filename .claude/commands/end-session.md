Run the session end script to merge the current session branch back to main and clean up:

```bash
source .claude/hooks/session-end.sh
```

This will:
1. Check for uncommitted changes
2. Ask if user wants to merge to main
3. Optionally push to remote
4. Delete the session branch
5. Switch back to main
