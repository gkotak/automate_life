#!/usr/bin/env bash
set -euo pipefail

# Allow quick bypass when needed.
if [[ "${SKIP_CODEX:-0}" == "1" ]]; then
  echo "[codex-review] Skipping (SKIP_CODEX=1)." >&2
  exit 0
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "[codex-review] Codex CLI not found; install it or export SKIP_CODEX=1 to proceed." >&2
  exit 1
fi

if git diff --cached --quiet; then
  echo "[codex-review] No staged changes detected; nothing to review." >&2
  exit 0
fi

repo_root="$(git rev-parse --show-toplevel)"
tmp_diff="$(mktemp)"
trap 'rm -f "$tmp_diff"' EXIT

git diff --cached >"$tmp_diff"

codex_state_dir="$repo_root/.codex"
mkdir -p "$codex_state_dir"
review_output="$codex_state_dir/last_review.md"

# Create prompt with diff
prompt_file="$(mktemp)"
trap 'rm -f "$tmp_diff" "$prompt_file"' EXIT

cat >"$prompt_file" <<'PROMPT_END'
You are OpenAI Codex. Review the staged diff for regressions, bugs,
missing tests, style inconsistencies, and risky logic. Reply as Markdown with:

- 🔥 Blockers (must fix before commit)
- ⚠️ Risks (should address soon)
- 👍 Positives worth noting

Diff:
```diff
PROMPT_END

cat "$tmp_diff" >>"$prompt_file"

cat >>"$prompt_file" <<'PROMPT_END'
```
PROMPT_END

set +e
codex exec \
  -C "$repo_root" \
  --output-last-message "$review_output" \
  - <"$prompt_file"
codex_status=$?
set -e

if [[ $codex_status -ne 0 ]]; then
  echo "[codex-review] Codex review failed (status $codex_status)." >&2
  exit $codex_status
fi

if [[ -f "$review_output" ]]; then
  # Check if there are actual blocker items (lines starting with - after the 🔥 Blockers header)
  # Not just the header itself, but actual content under it
  if grep -A 1 '🔥 Blockers' "$review_output" | tail -n +2 | grep -q '^- '; then
    echo "[codex-review] Blockers reported by Codex; please address before committing." >&2
    cat "$review_output" >&2
    exit 1
  fi
fi

exit 0
