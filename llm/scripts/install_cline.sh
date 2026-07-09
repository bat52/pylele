#!/usr/bin/env bash
#
# install_cline.sh — Install Cline CLI on Ubuntu
#
# Usage:
#   ./install_cline.sh           # Install latest cline v2 (default)
#   ./install_cline.sh -v 1      # Install cline v1
#   ./install_cline.sh --dry-run # Print steps without executing
#   ./install_cline.sh -h        # Print this help
#
# Installs nvm + Node.js LTS + cline npm package globally.

set -euo pipefail

# ---- Config ----
NVM_VERSION="0.40.1"
NODE_LTS="--lts"
CLINE_V2_PKG="cline"           # npm install -g cline → latest v2
CLINE_V1_PKG="cline@1.0.10"    # pinned v1

# ---- Help ----
usage() {
    # Print lines from line 2 until the first blank line (end of header comment)
    sed -n '2,/^[^#]/p' "$0" | sed -n '/^#/p' | sed 's/^# \?//'
    exit 0
}

# ---- Parse args ----
DRY_RUN=false
VERSION="2"  # default to v2

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) usage ;;
        --dry-run) DRY_RUN=true; shift ;;
        -v|--version)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --version requires an argument (1 or 2)" >&2
                exit 1
            fi
            VERSION="$2"
            shift 2
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            usage
            ;;
    esac
done

if [[ "$VERSION" != "1" && "$VERSION" != "2" ]]; then
    echo "Error: version must be 1 or 2, got '$VERSION'" >&2
    exit 1
fi

CLINE_PKG="$CLINE_V2_PKG"
[[ "$VERSION" == "1" ]] && CLINE_PKG="$CLINE_V1_PKG"

# ---- Helpers ----
info()  { echo "  [INFO]  $*"; }
warn()  { echo "  [WARN]  $*"; }
action() { echo "  [ACTION] $*"; }
dry()   { echo "  [DRY-RUN] $*"; }

run() {
    if "$DRY_RUN"; then
        dry "$@"
    else
        "$@"
    fi
}

# ---- Pre-flight checks ----
check_prereqs() {
    local missing=false
    for cmd in curl; do
        if ! command -v "$cmd" &>/dev/null; then
            warn "Missing prerequisite: $cmd"
            missing=true
        fi
    done
    if "$missing"; then
        echo "  Install missing packages with: sudo apt install curl" >&2
        exit 1
    fi
}

# ---- Install nvm ----
install_nvm() {
    if [[ -d "$HOME/.nvm" ]]; then
        info "nvm already installed at ~/.nvm"
        # Source it so nvm function is available
        export NVM_DIR="$HOME/.nvm"
        # shellcheck source=/dev/null
        [[ -s "$NVM_DIR/nvm.sh" ]] && . "$NVM_DIR/nvm.sh"
        return
    fi

    action "Installing nvm v${NVM_VERSION}..."
    run bash -c \
        "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v${NVM_VERSION}/install.sh | bash"

    export NVM_DIR="$HOME/.nvm"
    # shellcheck source=/dev/null
    [[ -s "$NVM_DIR/nvm.sh" ]] && . "$NVM_DIR/nvm.sh"
}

# ---- Install Node.js LTS ----
install_node() {
    if command -v node &>/dev/null; then
        info "Node.js already installed: $(node --version)"
        return
    fi

    action "Installing Node.js LTS via nvm..."
    run nvm install "$NODE_LTS"
    run nvm use "$NODE_LTS"
    run nvm alias default "$NODE_LTS"
}

# ---- Install cline ----
install_cline() {
    if command -v cline &>/dev/null; then
        local current
        current=$(cline --version 2>/dev/null || echo "unknown")
        info "cline already installed: v${current}"
        if [[ "$VERSION" == "1" ]]; then
            if echo "$current" | grep -q "^1\."; then
                info "Already cline v1, skipping."
                return
            fi
            warn "Upgrading/downgrading to cline v1..."
        else
            if echo "$current" | grep -q "^2\."; then
                info "Already cline v2, skipping."
                return
            fi
            warn "Upgrading/downgrading to cline v2..."
        fi
    fi

    action "Installing ${CLINE_PKG} globally..."
    run npm install -g "$CLINE_PKG"
}

# ---- Verify ----
verify() {
    if command -v cline &>/dev/null; then
        echo ""
        echo "  ✓ cline installed: $(cline --version 2>/dev/null)"
        echo "  ✓ location: $(command -v cline)"
        echo ""
        echo "  Run 'cline --help' to get started."
    else
        warn "cline not found on PATH after installation."
        echo "  You may need to restart your shell or add ~/.nvm/versions/node/*/bin to your PATH."
    fi
}

# ---- Main ----
echo ""
echo "  === Cline CLI Installer ==="
echo ""

check_prereqs
install_nvm
install_node
install_cline

if ! "$DRY_RUN"; then
    verify
fi

echo ""
echo "  Done."
echo ""
