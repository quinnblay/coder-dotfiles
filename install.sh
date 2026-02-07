#!/bin/bash
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

TOOLBOX_VERSION="v0.26.0"
TOOLBOX_DIR="$HOME/.local/bin"

echo "=== Quinn's Claude Code Dotfiles Installer ==="
echo ""

# ------------------------------------------------------------------
# Helper: create a symlink, backing up any existing regular file
# ------------------------------------------------------------------
link_file() {
  local src="$1"
  local dst="$2"

  if [ -L "$dst" ]; then
    # Already a symlink — update it silently
    ln -sf "$src" "$dst"
  elif [ -f "$dst" ]; then
    # Regular file exists — back it up first
    mv "$dst" "${dst}.backup.$(date +%s)"
    ln -sf "$src" "$dst"
    echo "  Backed up existing $(basename "$dst") and symlinked"
  else
    ln -sf "$src" "$dst"
  fi
}

# ------------------------------------------------------------------
# 1. Install Claude Code (if missing)
# ------------------------------------------------------------------
if ! command -v claude &>/dev/null; then
  echo "[1/6] Installing Claude Code..."
  curl -fsSL https://claude.ai/install.sh | sh
else
  echo "[1/6] Claude Code already installed: $(claude --version 2>/dev/null || echo 'unknown')"
fi

# ------------------------------------------------------------------
# 2. Install Graphite CLI (if missing)
# ------------------------------------------------------------------
if ! command -v gt &>/dev/null; then
  echo "[2/6] Installing Graphite CLI..."
  npm config set prefix "$HOME/.local"
  npm install -g @withgraphite/graphite-cli@stable
else
  echo "[2/6] Graphite CLI already installed: $(gt --version 2>/dev/null || echo 'unknown')"
fi

# ------------------------------------------------------------------
# 3. Install BigQuery MCP Toolbox (if missing)
# ------------------------------------------------------------------
if [ -f "$TOOLBOX_DIR/toolbox" ]; then
  echo "[3/6] BigQuery toolbox already installed"
else
  echo "[3/6] Installing BigQuery MCP Toolbox ($TOOLBOX_VERSION)..."
  mkdir -p "$TOOLBOX_DIR"
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64)  TOOLBOX_ARCH="amd64" ;;
    aarch64) TOOLBOX_ARCH="arm64" ;;
    arm64)   TOOLBOX_ARCH="arm64" ;;
    *)       echo "  WARNING: Unsupported architecture $ARCH, skipping toolbox install"; TOOLBOX_ARCH="" ;;
  esac
  if [ -n "$TOOLBOX_ARCH" ]; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    curl -fsSL "https://storage.googleapis.com/genai-toolbox/${TOOLBOX_VERSION}/${OS}/${TOOLBOX_ARCH}/toolbox" \
      -o "$TOOLBOX_DIR/toolbox"
    chmod +x "$TOOLBOX_DIR/toolbox"
    echo "  Installed to $TOOLBOX_DIR/toolbox"
  fi
fi

# Ensure ~/.local/bin is on PATH
if [[ ":$PATH:" != *":$TOOLBOX_DIR:"* ]]; then
  for rcfile in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rcfile" ] && ! grep -q 'local/bin' "$rcfile"; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rcfile"
    fi
  done
  export PATH="$TOOLBOX_DIR:$PATH"
fi

# ------------------------------------------------------------------
# 4. Symlink Claude Code config files
# ------------------------------------------------------------------
echo "[4/6] Symlinking ~/.claude/ config..."

mkdir -p "$CLAUDE_DIR/hooks"

link_file "$DOTFILES_DIR/.claude/CLAUDE.md"      "$CLAUDE_DIR/CLAUDE.md"
link_file "$DOTFILES_DIR/.claude/settings.json"   "$CLAUDE_DIR/settings.json"

for hook in "$DOTFILES_DIR/.claude/hooks/"*.py; do
  link_file "$hook" "$CLAUDE_DIR/hooks/$(basename "$hook")"
done

echo "  Symlinked CLAUDE.md, settings.json, and hooks"

# ------------------------------------------------------------------
# 5. Configure user-level MCP servers in ~/.claude.json
# ------------------------------------------------------------------
echo "[5/6] Configuring MCP servers..."

# Load secrets: prefer GCP Secret Manager, fall back to local file
# Retry a few times — workload identity credentials may not be ready at boot
_gcp_secrets_loaded=false
if command -v gcloud &>/dev/null; then
  echo "  gcloud identity: $(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>&1)"
  echo "  Running as user: $(whoami)"
  for _attempt in 1 2 3 4 5 6 7 8 9 10; do
    _gcp_err=$(gcloud secrets versions access latest --secret=coder_quinn_secrets --project=found-dev-335120 2>&1 > /tmp/.env.claude) || true
    if [ -s /tmp/.env.claude ]; then
      _gcp_secrets_loaded=true
      break
    fi
    echo "  Attempt $_attempt/10 failed: $_gcp_err"
    sleep 5
  done
fi

if [ "$_gcp_secrets_loaded" = true ]; then
  echo "  Loading secrets from GCP Secret Manager (coder_quinn_secrets)..."
  set -a
  source /tmp/.env.claude
  set +a
  rm -f /tmp/.env.claude
elif [ -f "$HOME/.env.claude" ]; then
  echo "  Loading secrets from ~/.env.claude"
  set -a
  source "$HOME/.env.claude"
  set +a
else
  echo "  No secrets source found. MCP servers requiring API keys will not work."
  echo "  Ask SRE to grant your pod access to coder_quinn_secrets, or create ~/.env.claude manually."
fi

# Build the MCP servers JSON.
# Servers that need API keys use env vars — they'll be empty strings
# if the secrets aren't set yet, which is fine (you can re-run later).
MCP_JSON=$(cat << EOF
{
  "mcpServers": {
    "linear": {
      "type": "sse",
      "url": "https://mcp.linear.app/sse"
    },
    "graphite": {
      "type": "stdio",
      "command": "gt",
      "args": ["mcp"],
      "env": {}
    },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY:-}"
      }
    },
    "figma-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "figma-developer-mcp", "--figma-api-key=${FIGMA_API_KEY:-}", "--stdio"],
      "env": {}
    },
    "bigquery": {
      "command": "${TOOLBOX_DIR}/toolbox",
      "args": ["--prebuilt", "bigquery", "--stdio"],
      "env": {
        "BIGQUERY_PROJECT": "${BIGQUERY_PROJECT:-bustling-syntax-229500}"
      }
    }
  }
}
EOF
)

if [ -f "$HOME/.claude.json" ]; then
  # Merge MCP servers into existing file (preserves all other state)
  if command -v jq &>/dev/null; then
    jq --argjson mcps "$(echo "$MCP_JSON" | jq '.mcpServers')" \
      '.mcpServers = (.mcpServers // {}) * $mcps' \
      "$HOME/.claude.json" > /tmp/claude-json-merged.json
    mv /tmp/claude-json-merged.json "$HOME/.claude.json"
    echo "  Merged MCP servers into existing ~/.claude.json"
  else
    echo "  WARNING: jq not found. Cannot merge MCP servers into existing ~/.claude.json"
    echo "  Install jq and re-run, or manually add MCP servers."
  fi
else
  echo "$MCP_JSON" > "$HOME/.claude.json"
  echo "  Created ~/.claude.json with MCP servers"
fi

# ------------------------------------------------------------------
# 6. Auth instructions
# ------------------------------------------------------------------
echo "[6/6] Setup complete!"
echo ""
echo "=== Next Steps ==="
echo ""
echo "1. AUTHENTICATE (one-time per workspace):"
echo "   Run 'claude' and use /login to authenticate with your Max subscription."
echo "   Tip: If on a headless server, use SSH port forwarding for the OAuth flow:"
echo "     ssh -L 8080:localhost:8080 your-coder-workspace"
echo ""

if [ -z "${CONTEXT7_API_KEY:-}" ] || [ -z "${FIGMA_API_KEY:-}" ]; then
  echo "2. SET UP API KEYS:"
  echo "   Preferred: Ask SRE to grant your pod access to the coder_quinn_secrets GCP secret."
  echo "   Fallback:  Create ~/.env.claude with your secrets, then re-run this script:"
  echo ""
  echo "     cp $DOTFILES_DIR/env.claude.example ~/.env.claude"
  echo "     vim ~/.env.claude    # Fill in your keys"
  echo "     bash $DOTFILES_DIR/install.sh  # Re-run to apply"
  echo ""
fi

echo "3. VERIFY:"
echo "   claude"
echo "   /mcp     # Check MCP servers are connected"
echo "   /status  # Check auth status"
echo ""
