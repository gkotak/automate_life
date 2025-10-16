Check what git branch the current session is on:

```bash
git branch --show-current
```

Also check if there's an active session:
```bash
if [ -f .git/CURRENT_SESSION_BRANCH ]; then
  echo "Active session branch: $(cat .git/CURRENT_SESSION_BRANCH)"
else
  echo "No session tracking file found (manual branch or no session started)"
fi
```

Tell the user:
1. The current branch name
2. Whether this is a session branch or manual branch
3. Whether they started a session with /start-session
