#!/usr/bin/env bash

set -euo pipefail

# --- resolve_api_key function ---
resolve_api_key() {
    # 1. explicit --api-key / -k flag (already parsed into API_KEY variable)
    if [[ -n "${API_KEY:-}" ]]; then
        echo "$API_KEY"
        return
    fi

    # 2. AIDER_API_KEY env var
    if [[ -n "${AIDER_API_KEY:-}" ]]; then
        echo "$AIDER_API_KEY"
        return
    fi

    # 3. Cline's DeepSeek key from ~/.cline/data/secrets.json
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
            echo "$deepseek_key"
            return
        fi
    fi

    # No key found
    echo ""
}

# --- Argument parsing ---
API_KEY=""
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
        --help|-h)
            echo "Usage: ai_query.sh [--api-key KEY] \"query\""
            echo ""
            echo "Options:"
            echo "  --api-key KEY, -k KEY   API key for aider (overrides AIDER_API_KEY env var)"
            echo "  --help, -h              Show this help message"
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

QUERY="${1:-}"

if [[ -z "$QUERY" ]]; then
    echo "Usage: ai_query.sh [--api-key KEY] \"query\""
    exit 1
fi

# Resolve API key
RESOLVED_KEY=$(resolve_api_key)

if [[ -z "$RESOLVED_KEY" ]]; then
    echo "ERROR: No API key found. Provide via --api-key, AIDER_API_KEY env var, or ~/.cline/data/secrets.json"
    exit 1
fi

# Invoke aider with resolved key
aider --api-key deepseek="$RESOLVED_KEY" --message "$QUERY"
