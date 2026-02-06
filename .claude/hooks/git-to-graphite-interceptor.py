#!/usr/bin/env python3
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
    
    # Patterns to match git branch creation commands
    git_branch_create_patterns = [
        r'^\s*git\s+checkout\s+-b\b',     # git checkout -b
        r'^\s*git\s+switch\s+-c\b',       # git switch -c (newer git)
        r';\s*git\s+checkout\s+-b\b',     # ; git checkout -b (in command chains)
        r'&&\s*git\s+checkout\s+-b\b',    # && git checkout -b (in command chains)
        r';\s*git\s+switch\s+-c\b',       # ; git switch -c (in command chains)
        r'&&\s*git\s+switch\s+-c\b',      # && git switch -c (in command chains)
    ]
    
    # Check if command matches any branch creation pattern
    for pattern in git_branch_create_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            # Extract branch name if present
            branch_match = re.search(r'(?:checkout\s+-b|switch\s+-c)\s+([^\s]+)', command)
            branch_name = branch_match.group(1) if branch_match else None
            
            # Build Graphite suggestion
            if branch_name:
                suggestion = f'gt create -m "feat: {branch_name}"  # Customize commit message as needed'
            else:
                suggestion = 'gt create -m "feat: description"  # Creates new branch with commit'
            
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"""Git branch creation intercepted - using Graphite workflow instead.

To create a new branch and start a new PR stack, use:
  {suggestion}

Graphite's 'gt create' command:
• Creates a new branch from current position
• Makes an initial commit on that branch
• Sets up the branch for PR stacking

This ensures proper stack management from the start."""
                }
            }
            
            print(json.dumps(response))
            sys.exit(0)
    
    # Patterns to match git commit commands
    git_commit_patterns = [
        r'^\s*git\s+commit\b',           # git commit
        r'^\s*git\s+commit\s+-m\b',      # git commit -m
        r'^\s*git\s+commit\s+--amend\b', # git commit --amend
        r';\s*git\s+commit\b',           # ; git commit (in command chains)
        r'&&\s*git\s+commit\b',          # && git commit (in command chains)
    ]
    
    # Check if command matches any git commit pattern
    for pattern in git_commit_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            # Determine if this is an amend
            is_amend = '--amend' in command
            
            # Extract commit message if present
            message_match = re.search(r'-m\s+["\']([^"\']+)["\']', command)
            message = message_match.group(1) if message_match else None
            
            # Build appropriate Graphite suggestion
            if is_amend:
                suggestion = "gt modify"
                if message:
                    suggestion += f' -m "{message}"'
                explanation = "To amend the last commit on current branch"
            else:
                suggestion = "gt modify --commit"
                if message:
                    suggestion += f' -m "{message}"'
                else:
                    suggestion += " # to add a new commit to current branch"
                explanation = "To add a new commit to the current branch"
            
            # Build helpful response
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"""Git commit intercepted - using Graphite workflow instead.

{explanation}, use:
  {suggestion}

Graphite command guide:
• gt modify --commit -m "message" - Add new commit to current branch
• gt modify -m "message" - Amend last commit and restack
• gt create -m "message" - Create NEW branch with commit (for starting new PR)

If you're starting NEW work/PR, use 'gt create' instead.
If you're continuing work on current branch, use 'gt modify --commit' or 'gt modify'."""
                }
            }
            
            print(json.dumps(response))
            sys.exit(0)
    
    # Also intercept git push to suggest gt submit
    git_push_patterns = [
        r'^\s*git\s+push\b',
        r';\s*git\s+push\b',
        r'&&\s*git\s+push\b',
    ]
    
    for pattern in git_push_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": """Git push intercepted - using Graphite workflow instead.

To push and create/update PRs, use:
  gt submit                # Submit current branch
  gt submit --stack        # Submit entire stack
  gt submit --no-interactive  # Skip prompts

This ensures proper PR stacking and dependencies."""
                }
            }
            print(json.dumps(response))
            sys.exit(0)
    
    # Allow all other commands
    sys.exit(0)

if __name__ == "__main__":
    main()