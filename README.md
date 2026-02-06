# Claude Code Dotfiles for Coder Workspaces

Personal Claude Code configuration for remote [Coder](https://coder.com) dev environments. Designed for the workflow: create a workspace, SSH in, run `claude`, and have everything ready to go.

## Quick Start

### First-time setup on a new Coder workspace

```bash
# 1. Clone this repo (Coder does this automatically via the dotfiles module)
git clone git@github.com:<you>/dotfiles.git ~/dotfiles

# 2. Run the installer
bash ~/dotfiles/install.sh

# 3. Set up API keys for MCP servers that need them
cp ~/dotfiles/env.claude.example ~/.env.claude
vim ~/.env.claude    # Fill in your keys
bash ~/dotfiles/install.sh   # Re-run to apply keys

# 4. Authenticate with Claude Max (one-time per workspace)
claude
# Then type /login and follow the OAuth flow
```

### With Coder's dotfiles module

Add this to your Coder template so it runs automatically on workspace creation:

```hcl
module "dotfiles" {
  source   = "registry.coder.com/modules/dotfiles/coder"
  agent_id = coder_agent.main.id
}
```

Each engineer is prompted for their dotfiles repo URL on first workspace creation. Coder clones it and runs `install.sh` (highest priority among Coder's [supported script names](https://coder.com/docs/user-guides/workspace-dotfiles)).

## What Gets Installed

The installer (`install.sh`) does 6 things:

| Step | What | Details |
|------|------|---------|
| 1 | Claude Code | Installed via `claude.ai/install.sh` if missing |
| 2 | Graphite CLI (`gt`) | For PR stacking workflow |
| 3 | BigQuery MCP Toolbox | Google's `genai-toolbox` binary (v0.26.0) for BigQuery access |
| 4 | Config symlinks | Symlinks `CLAUDE.md`, `settings.json`, and hooks into `~/.claude/` |
| 5 | MCP servers | Configures user-level MCP servers in `~/.claude.json` |
| 6 | Prints next steps | Auth instructions and verification commands |

## File Structure

The `.claude/` directory mirrors `~/.claude/` in your home directory (standard dotfiles convention). The installer creates **symlinks** back to this repo, so edits in either location are reflected immediately.

```
.
├── install.sh                 # Main installer — entry point for Coder dotfiles
├── env.claude.example         # Template for API keys (copy to ~/.env.claude)
├── .gitignore                 # Prevents committing secrets
├── README.md
└── .claude/                   # Mirrors ~/.claude/ (symlinked, not copied)
    ├── CLAUDE.md              # Personal instructions loaded into every Claude session
    ├── settings.json          # Permissions, hooks, plugins, preferences
    └── hooks/
        ├── git-to-graphite-interceptor.py   # Redirects git commit/push/branch to gt
        ├── npx-to-yarn-interceptor.py       # Redirects npx to yarn in frontend projects
        └── rspec-docker-interceptor.py      # Ensures rspec runs inside Docker
```

### How symlinking works

| Source (in this repo) | Symlinked to | Purpose |
|--------|-------------|---------|
| `.claude/CLAUDE.md` | `~/.claude/CLAUDE.md` | Personal memory — loaded into every Claude Code session |
| `.claude/settings.json` | `~/.claude/settings.json` | Permissions, hooks, plugins, allowed/denied tools |
| `.claude/hooks/*.py` | `~/.claude/hooks/*.py` | Pre-tool-use hooks that intercept commands |
| Generated at install | `~/.claude.json` | User-level MCP server configuration (merged, not symlinked) |
| `~/.env.claude` (manual) | Read by `install.sh` | API keys for MCP servers (never committed) |

Config files are symlinked so you can edit `~/.claude/settings.json` in a workspace and the change is reflected in the dotfiles repo (and vice versa). `~/.claude.json` is the exception — Claude Code constantly writes state into it, so the installer merges MCP servers into it rather than symlinking.

If a regular file already exists at a symlink destination, the installer backs it up to `<filename>.backup.<timestamp>` before creating the symlink.

## MCP Servers

These are configured as **user-level** MCP servers (available in every project):

| Server | Transport | Auth Required | Notes |
|--------|-----------|---------------|-------|
| **Linear** | SSE | Browser auth via Linear | Issue tracking |
| **Graphite** | stdio (`gt mcp`) | `gt auth` | PR stacking |
| **Context7** | HTTP | `CONTEXT7_API_KEY` | Library documentation lookup |
| **Figma** | stdio (npx) | `FIGMA_API_KEY` | Design file access |
| **BigQuery** | stdio (toolbox) | `gcloud auth` | Query data warehouse |

**Project-level** MCP servers (like Notion, Statsig, Sentry) are configured in each repo's `.mcp.json` file, not here.

## Authentication

### Claude Max

This setup uses a Claude Max subscription (not an API key). You authenticate once per workspace:

```bash
claude        # Start Claude Code
# Type /login and complete the OAuth flow in your browser
```

The OAuth token is stored in `~/.claude/` and persists across workspace stop/start cycles as long as your home directory is on a persistent volume (standard for Coder K8s workspaces with PVCs).

**Headless/SSH tip:** If the workspace has no browser, the `/login` flow gives you a URL to open on any machine. If it needs localhost, use SSH port forwarding:

```bash
ssh -L 8080:localhost:8080 coder.my-workspace
```

### BigQuery

BigQuery auth uses Google Cloud Application Default Credentials. Run once per workspace:

```bash
gcloud auth application-default login
```

### Graphite

Graphite auth is separate from Claude. Run once per workspace:

```bash
gt auth
```

## API Keys

Create `~/.env.claude` from the template (this file is gitignored):

```bash
cp env.claude.example ~/.env.claude
```

Then fill in the values:

| Variable | Where to get it |
|----------|----------------|
| `FIGMA_API_KEY` | https://www.figma.com/developers/api#access-tokens |
| `CONTEXT7_API_KEY` | Your Context7 account |
| `STATSIG_API_KEY` | Statsig console (project-level, used in found/ repo) |
| `BIGQUERY_PROJECT` | GCP project ID (defaults to `bustling-syntax-229500`) |

After editing, re-run the installer to apply:

```bash
bash ~/dotfiles/install.sh
```

## Hooks

Three pre-tool-use hooks intercept Claude Code's bash commands:

### git-to-graphite-interceptor.py
Blocks `git commit`, `git push`, and `git checkout -b` — suggests the Graphite equivalent (`gt create`, `gt modify`, `gt submit`). This enforces the PR stacking workflow.

### npx-to-yarn-interceptor.py
Blocks `npx jest`, `npx eslint`, `npx tsc` and suggests `yarn jest`, `yarn lint`, `yarn tsc` instead. Also catches `yarn test` (which runs in watch mode) and suggests `yarn jest` directly.

### rspec-docker-interceptor.py
Blocks bare `rspec` / `bundle exec rspec` commands and suggests the `docker compose exec` equivalent. The Rails API backend runs in Docker, so specs must run there.

## Settings

Key settings in `.claude/settings.json`:

- **Denied commands**: `git add -A`, `git add .`, production console/RC commands, BigQuery SQL execution
- **Always-on thinking**: `alwaysThinkingEnabled: true`
- **Plugins**: feature-dev, code-documentation, debugging-toolkit, code-simplifier
- **Agent teams**: Experimental teams feature enabled via env var

## Customizing

### Adding a new MCP server

Edit the `MCP_JSON` block in `install.sh` and re-run it. Or add it interactively:

```bash
# User-level (available in all projects)
claude mcp add --scope user --transport http my-server https://my-server.example.com/mcp

# Project-level (shared with team, committed to repo)
claude mcp add --scope project --transport http my-server https://my-server.example.com/mcp
```

### Adding a new hook

1. Create a Python script in `.claude/hooks/`
2. Add a matcher entry in `.claude/settings.json` under `hooks.PreToolUse`
3. Re-run `install.sh` (or it auto-applies since files are symlinked)

### Updating CLAUDE.md

Since `~/.claude/CLAUDE.md` is a symlink back to this repo, just edit it anywhere — the change applies everywhere. Commit from the dotfiles repo when you're happy with the change.

## Running Multiple Claude Code Instances

Each Coder workspace can run multiple concurrent `claude` processes (~300-400MB RAM each):

```bash
# Use tmux for multiple interactive sessions
tmux new -s agent1 -d 'cd ~/found && claude'
tmux new -s agent2 -d 'cd ~/found && claude'

# Or headless mode for fire-and-forget tasks
claude -p "refactor the auth module" --output-format stream-json &
claude -p "write tests for payments" --output-format stream-json &
```

To avoid file conflicts between concurrent agents, use git worktrees:

```bash
git worktree add ~/found-agent2 -b agent2-branch
cd ~/found-agent2 && claude
```

## Prerequisites

The Coder workspace Docker image should have:

- `curl`, `git`, `jq`
- Node.js 18+ and npm (for Graphite CLI and npx-based MCP servers)
- Python 3 (for hooks)
- `gcloud` CLI (for BigQuery auth)

## Troubleshooting

**MCP servers not showing up:** Run `/mcp` inside Claude Code to check status. Re-run `install.sh` if needed.

**OAuth token expired:** Run `/login` again inside Claude Code.

**BigQuery not working:** Make sure you've run `gcloud auth application-default login` and that `~/.local/bin/toolbox` exists.

**Hooks not firing:** Check that `~/.claude/settings.json` is a symlink (`ls -la ~/.claude/settings.json`) and that hook scripts are executable.

**Re-running the installer:** Safe to run any number of times. Symlinks are updated in place, existing regular files are backed up, installed tools are skipped, and MCP config is merged (requires `jq`).
