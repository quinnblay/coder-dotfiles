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
    
    # Check for yarn test commands that run in watch mode
    watch_mode_patterns = [
        r'\byarn\s+(?:workspace\s+\S+\s+)?test\b',  # yarn test or yarn workspace X test
        r'\byarn\s+(?:workspace\s+\S+\s+)?test:no-deps\b',  # yarn test:no-deps
        r'\byarn\s+(?:workspace\s+\S+\s+)?test:changed\b',  # yarn test:changed  
    ]
    
    for pattern in watch_mode_patterns:
        if re.search(pattern, command):
            # Extract the file path if present
            file_match = re.search(r'(src/[^\s]+\.(?:test|spec)\.(?:tsx?|jsx?))', command)
            file_path = file_match.group(1) if file_match else ''
            
            # Build suggestion based on what was detected
            if 'workspace web-app-frontend' in command:
                suggestion = f'yarn workspace web-app-frontend jest {file_path}'.strip()
            else:
                suggestion = f'yarn jest {file_path}'.strip()
            
            response = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"""yarn test command intercepted - this runs in watch mode.

The test:no-deps, test, and test:changed scripts all run scripts/test.js which defaults to watch mode.

Instead, use Jest directly:
  {suggestion}

Add flags as needed:
  --watchAll=false (explicitly disable watch)
  --coverage (for coverage reports)
  --verbose (for detailed output)

For CI mode without watch: yarn test:ci"""
                }
            }
            
            print(json.dumps(response))
            sys.exit(0)
    
    # Define npx commands that should always be replaced with yarn
    # Based on web-app-frontend's actual package.json scripts
    npx_patterns = [
        (r'\bnpx jest\b', 'yarn jest'),  # Use yarn jest directly, NOT yarn test (which runs in watch mode)
        (r'\bnpx eslint\b', 'yarn lint'),
        (r'\bnpx esprint\b', 'yarn esprint'),
        (r'\bnpx tsc\b', 'yarn tsc'),
        (r'\bnpx storybook\b', 'yarn storybook'),
        (r'\bnpx http-server\b', 'yarn http-server'),
    ]
    
    # Special case: Check for common patterns that match specific yarn scripts
    test_pattern_suggestions = {
        r'npx jest.*--coverage': 'Consider using: yarn test:ci (runs without watch mode)',
        r'npx eslint.*--fix': 'Consider using: yarn lint:fix or yarn eslint:fix',
        r'npx eslint.*--quiet': 'Consider using: yarn lint:quiet',
        r'npx eslint.*\$\(git diff': 'Consider using: yarn lint:changed or yarn lint:fix-changed',
        r'npx tsc --build': 'Consider using: yarn tsc or yarn tsc:no-deps',
    }
    
    # Check if command contains any npx commands to replace
    modified_command = command
    replacements_made = []
    special_suggestions = []
    
    # Check for special pattern suggestions first
    for pattern, suggestion in test_pattern_suggestions.items():
        if re.search(pattern, command, re.IGNORECASE):
            special_suggestions.append(suggestion)
    
    # Then check for direct replacements
    for pattern, replacement in npx_patterns:
        if re.search(pattern, command):
            # Extract what command is being replaced for the message
            match = re.search(pattern, command)
            if match:
                replacements_made.append((match.group(), replacement))
                modified_command = re.sub(pattern, replacement, modified_command)
    
    # If we found npx commands to replace, deny and suggest yarn version
    if replacements_made or special_suggestions:
        message_parts = []
        
        if replacements_made:
            replacement_list = '\n'.join([f"  • {old} → {new}" for old, new in replacements_made])
            message_parts.append(f"Replacing npx with yarn for project consistency:\n{replacement_list}")
            message_parts.append(f"Suggested command:\n  {modified_command}")
        
        if special_suggestions:
            suggestions_list = '\n'.join(special_suggestions)
            message_parts.append(f"\n{suggestions_list}")
        
        response = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"""npx command intercepted - using yarn instead.

{chr(10).join(message_parts)}

Available yarn scripts in web-app-frontend:
• yarn jest (runs jest directly without watch mode)
• yarn test:ci (runs tests in CI mode without watch)
• yarn lint (or lint:fix, lint:quiet, lint:changed, lint:fix-changed)
• yarn tsc (or tsc:no-deps)
• yarn build (or build:dev)
• yarn start
• yarn storybook (or build-storybook)

Note: Avoid 'yarn test' as it runs in watch mode"""
            }
        }
        
        print(json.dumps(response))
        sys.exit(0)
    
    # Allow all other commands
    sys.exit(0)

if __name__ == "__main__":
    main()