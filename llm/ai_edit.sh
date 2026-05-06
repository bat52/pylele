#!/usr/bin/env bash

set -euo pipefail

MSG="${1:-}"

if [[ -z "$MSG" ]]; then
    echo "Usage: ai_edit.sh \"instruction\" [files...]"
    exit 1
fi

shift || true
FILES=("$@")

echo
echo "========================================"
echo "AI EDIT REQUEST"
echo "========================================"
echo "$MSG"
echo

# Ensure repo is clean enough
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "ERROR: not inside git repo"
    exit 1
fi

# Optional: prevent giant dirty worktrees
DIRTY_COUNT=$(git status --porcelain | wc -l)

if [[ "$DIRTY_COUNT" -gt 50 ]]; then
    echo "ERROR: too many uncommitted changes"
    exit 1
fi

# Log request
mkdir -p .ai_logs

echo "$(date)" >> .ai_logs/history.log
echo "$MSG" >> .ai_logs/history.log
echo "---" >> .ai_logs/history.log

# Invoke aider
aider --message "$MSG" "${FILES[@]}"

echo
echo "========================================"
echo "POST-EDIT STATUS"
echo "========================================"

git --no-pager log -1 --stat