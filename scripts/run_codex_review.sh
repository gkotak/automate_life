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
diff_content="$(cat "$tmp_diff")"

codex_state_dir="$repo_root/.codex"
mkdir -p "$codex_state_dir"
review_output="$codex_state_dir/last_review.md"

set +e
codex exec \
  -C "$repo_root" \
  --output-last-message "$review_output" \
  - <<EOF
You are OpenAI Codex. Review the staged diff for regressions, bugs,
missing tests, style inconsistencies, and risky logic. Reply as Markdown with:

- 🔥 Blockers (must fix before commit)
- ⚠️ Risks (should address soon)
- 👍 Positives worth noting

Diff:
\`\`\`diff
$diff_content
\`\`\`
EOF
codex_status=$?
set -e

if [[ $codex_status -ne 0 ]]; then
  echo "[codex-review] Codex review failed (status $codex_status)." >&2
  exit $codex_status
fi

if [[ -f "$review_output" ]] && grep -q '🔥' "$review_output"; then
  echo "[codex-review] Blockers reported by Codex; please address before committing." >&2
  exit 1
fi

exit 0
