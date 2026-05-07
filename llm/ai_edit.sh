#!/usr/bin/env bash

set -euo pipefail

# --- resolve_api_key function ---
resolve_api_key() {
    # 1. explicit --api-key / -k flag (already parsed into API_KEY variable)
    if [[ -n "${API_KEY:-}" ]]; then
        echo "explicit:$API_KEY"
        return
    fi

    # 2. OPENROUTER_API_KEY env var
    if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
        echo "openrouter:$OPENROUTER_API_KEY"
        return
    fi

    # 3. AIDER_API_KEY env var (legacy, treated as deepseek)
    if [[ -n "${AIDER_API_KEY:-}" ]]; then
        echo "deepseek:$AIDER_API_KEY"
        return
    fi


    # 4. Cline's DeepSeek key from ~/.cline/data/secrets.json
    local secrets_file="$HOME/.cline/data/secrets.json"
    if [[ -f "$secrets_file" ]]; then
        local deepseek_key
        deepseek_key=$(python3 -c "
import json, sys
try:
    with open('$secrets_file') as f:
        data = json.load(f)
    key = data.get('deepSeekApiKey')
    if key:
        print(key)
except Exception:
    pass
" 2>/dev/null)
        if [[ -n "$deepseek_key" ]]; then
            echo "deepseek:$deepseek_key"
            return
        fi
    fi

    # No key found
    echo ""
}

# --- Argument parsing ---
API_KEY=""
MODEL_NAME=""
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-key|-k)
            if [[ -n "${2:-}" ]]; then
                API_KEY="$2"
                shift 2
            else
                echo "ERROR: --api-key requires a value"
                exit 1
            fi
            ;;
        --api-key=*)
            API_KEY="${1#*=}"
            shift
            ;;
        -k*)
            API_KEY="${1#??}"
            shift
            ;;
        --model|-m)
            if [[ -n "${2:-}" ]]; then
                MODEL_NAME="$2"
                shift 2
            else
                echo "ERROR: --model requires a value"
                exit 1
            fi
            ;;
        --model=*)
            MODEL_NAME="${1#*=}"
            shift
            ;;
        -m*)
            MODEL_NAME="${1#??}"
            shift
            ;;
        --help|-h)
            echo "Usage: ai_edit.sh [--api-key KEY] [--model MODEL] \"instruction\" [files...]"
            echo ""
            echo "Options:"
            echo "  --api-key KEY, -k KEY       API key for aider (e.g., 'deepseek=KEY' or 'openrouter=KEY')"
            echo "                              Overrides OPENROUTER_API_KEY or AIDER_API_KEY env vars"
            echo "  --model MODEL, -m MODEL     Model to use (e.g., 'deepseek/deepseek-coder', 'openrouter/google/gemini-2.5-flash')"
            echo "  --help, -h                  Show this help message"
            exit 0
            ;;
        --)
            shift
            POSITIONAL_ARGS+=("$@")
            break
            ;;
        -*)
            echo "ERROR: Unknown option $1"
            exit 1
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional arguments
set -- "${POSITIONAL_ARGS[@]}"

MSG="${1:-}"

if [[ -z "$MSG" ]]; then
    echo "Usage: ai_edit.sh [--api-key KEY] [--model MODEL] \"instruction\" [files...]"
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

# Resolve API key
RESOLVED_KEY_PROVIDER=$(resolve_api_key)
KEY=""
PROVIDER=""

if [[ -n "$RESOLVED_KEY_PROVIDER" ]]; then
    IFS=':' read -r PROVIDER KEY <<< "$RESOLVED_KEY_PROVIDER"
fi

if [[ -z "$KEY" ]]; then
    echo "ERROR: No API key found. Provide via --api-key, OPENROUTER_API_KEY/AIDER_API_KEY env vars, or ~/.cline/data/secrets.json"
    exit 1
fi

# Determine model to use
if [[ -z "$MODEL_NAME" ]]; then
    if [[ "$PROVIDER" == "deepseek" ]]; then
        MODEL_NAME="deepseek/deepseek-coder"
    else
        MODEL_NAME="openrouter/google/gemini-2.5-flash"
    fi
fi

# Invoke aider with resolved key and model
if [[ "$PROVIDER" == "openrouter" ]]; then
    aider --api-key "openrouter=$KEY" --model "$MODEL_NAME" --message "$MSG" "${FILES[@]}"
elif [[ "$PROVIDER" == "deepseek" ]]; then
    aider --api-key "deepseek=$KEY" --model "$MODEL_NAME" --message "$MSG" "${FILES[@]}"
elif [[ "$PROVIDER" == "explicit" ]]; then
    # If explicit --api-key was provided, it might have a provider prefix (e.g., deepseek=...)
    # Use it directly as aider expects.
    aider --api-key "$API_KEY" --model "$MODEL_NAME" --message "$MSG" "${FILES[@]}"
else
    # Fallback for unknown provider or if specific provider not detected from explicit key
    # Default to openrouter
    aider --api-key "openrouter=$KEY" --model "$MODEL_NAME" --message "$MSG" "${FILES[@]}"
fi


NOQA_COUNT=$(git diff HEAD~1 | grep -c "# noqa" || true)

if [[ "$NOQA_COUNT" -gt 3 ]]; then
    echo "ERROR: excessive noqa additions detected"
    git reset --hard HEAD~1
    exit 1
fi

echo
echo "========================================"
echo "POST-EDIT STATUS"
echo "========================================"

git --no-pager log -1 --stat
