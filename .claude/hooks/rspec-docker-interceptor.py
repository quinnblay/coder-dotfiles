#!/usr/bin/env python3
"""
Pre-tool hook to intercept RSpec commands and ensure they run in Docker.

This hook catches direct rspec/bundle exec rspec commands and blocks them,
providing the correct docker compose exec command instead.
"""
import json
import sys
import re


def main():
    # Read input from stdin
    try:
        data = json.load(sys.stdin)
    except:
        # If can't parse, allow the command
        sys.exit(0)

    # Check if this is a Bash tool call
    if data.get('hook_event_name') != 'PreToolUse' or data.get('tool_name') != 'Bash':
        sys.exit(0)

    # Get the command from tool input
    command = data.get('tool_input', {}).get('command', '')

    # If the command already uses docker compose exec, allow it
    if re.search(r'docker\s+compose\s+exec', command, re.IGNORECASE):
        sys.exit(0)

    # Also allow if using docker exec (for running containers)
    if re.search(r'docker\s+exec', command, re.IGNORECASE):
        sys.exit(0)

    # Patterns to match direct RSpec commands (not in docker)
    rspec_patterns = [
        r'^\s*bin/rspec\b',                    # bin/rspec
        r'^\s*bundle\s+exec\s+rspec\b',        # bundle exec rspec
        r'^\s*rspec\b',                        # bare rspec
        r';\s*bin/rspec\b',                    # ; bin/rspec
        r'&&\s*bin/rspec\b',                   # && bin/rspec
        r';\s*bundle\s+exec\s+rspec\b',        # ; bundle exec rspec
        r'&&\s*bundle\s+exec\s+rspec\b',       # && bundle exec rspec
        r'cd\s+[^;]+;\s*bin/rspec\b',          # cd ...; bin/rspec
        r'cd\s+[^&]+&&\s*bin/rspec\b',         # cd ... && bin/rspec
        r'cd\s+[^;]+;\s*bundle\s+exec\s+rspec', # cd ...; bundle exec rspec
        r'cd\s+[^&]+&&\s*bundle\s+exec\s+rspec', # cd ... && bundle exec rspec
    ]

    # Check if command matches any direct rspec pattern
    for pattern in rspec_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            # Try to extract the spec path from the command
            spec_path_match = re.search(
                r'(?:rspec|bin/rspec)\s+([^\s]+\.rb(?::\d+)?)',
                command
            )
            spec_path = spec_path_match.group(1) if spec_path_match else './spec/path/to/spec.rb'

            # Convert absolute path to relative path for docker
            # /Users/.../found/api-backend/site/packs/... -> ./site/packs/...
            if '/api-backend/site/' in spec_path:
                spec_path = './' + spec_path.split('/api-backend/site/')[-1]
                if spec_path.startswith('./site/'):
                    spec_path = './' + spec_path[7:]  # Remove 'site/' prefix
            elif '/api-backend/' in spec_path:
                spec_path = './' + spec_path.split('/api-backend/')[-1]

            # Check for format option
            format_opt = ''
            if '--format' in command or '-f ' in command:
                format_match = re.search(r'(?:--format|-f)\s+(\w+)', command)
                if format_match:
                    format_opt = f' --format {format_match.group(1)}'

            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"""RSpec command intercepted - must run inside Docker container.

The api-backend Rails app runs in Docker. Run RSpec tests with:

  docker compose exec api-backend bundle exec rspec {spec_path}{format_opt}

Common patterns:
• Single file: docker compose exec api-backend bundle exec rspec ./packs/merchant_cash_advance/spec/...
• With line number: docker compose exec api-backend bundle exec rspec ./spec/models/user_spec.rb:42
• Entire pack: docker compose exec api-backend bundle exec rspec ./packs/merchant_cash_advance

Note: Paths inside docker start from /app (api-backend/site), so use relative paths like ./packs/... or ./spec/..."""
                }
            }

            print(json.dumps(response))
            sys.exit(0)

    # Also catch other Rails commands that should run in docker
    rails_patterns = [
        r'^\s*bundle\s+exec\s+rails\b',        # bundle exec rails
        r'^\s*bin/rails\b',                    # bin/rails
        r'^\s*rails\s+(?:db:|console|server|generate|g\s)', # rails db:, console, etc.
        r'cd\s+[^;]+;\s*bundle\s+exec\s+rails', # cd ...; bundle exec rails
        r'cd\s+[^&]+&&\s*bundle\s+exec\s+rails', # cd ... && bundle exec rails
    ]

    for pattern in rails_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            # Extract the rails subcommand
            rails_cmd_match = re.search(r'(?:rails|bin/rails)\s+(.+?)(?:\s*$|\s*;|\s*&&)', command)
            rails_cmd = rails_cmd_match.group(1) if rails_cmd_match else '[command]'

            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"""Rails command intercepted - must run inside Docker container.

The api-backend Rails app runs in Docker. Run Rails commands with:

  docker compose exec api-backend bundle exec rails {rails_cmd}

Common commands:
• Migrations: docker compose exec api-backend bundle exec rails db:migrate
• Console: docker compose exec api-backend bundle exec rails console
• Generate: docker compose exec api-backend bundle exec rails generate ..."""
                }
            }

            print(json.dumps(response))
            sys.exit(0)

    # Allow all other commands
    sys.exit(0)


if __name__ == "__main__":
    main()
