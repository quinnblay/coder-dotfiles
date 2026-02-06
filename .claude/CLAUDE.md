# CLAUDE.md User Memory

This file provides personal guidance to Claude Code (claude.ai/code) when working with Quinn's repositories.

## Code search tools

### When to use ast-grep

Use **ast-grep** for structural code searches when you need to:

- Find code patterns based on syntax (e.g., all function calls, class definitions, specific argument patterns)
- Search for semantic patterns that span multiple lines
- Avoid false positives from comments or strings
- Find similar code structures with variations
- Perform refactoring operations

### When to use fd

Use `fd` instead of `find` when finding files. `fd` is much quicker than `find`.

### ast-grep Examples

```bash
# Find all React components using a specific hook
ast-grep --pattern 'const $VAR = useCustomHook($$$)' --lang tsx

# Find all RSpec tests without proper cleanup
ast-grep --pattern 'it "$_" do
  $$$
end' --lang ruby | grep -v "clean_up"

# Find all service classes with a specific method pattern
ast-grep --pattern 'class $CLASS
  $$$
  def perform($ARGS)
    $$$
  end
  $$$
end' --lang ruby

# Find all useState calls with specific initial values
ast-grep --pattern 'const [$STATE, $SETTER] = useState($INITIAL)' --lang tsx
```

Rule: Prefer ast-grep for complex code searches. When searching for code patterns (not just text), try ast-grep first before falling back to other tools.

## Git Workflow

- Quinn prefers using Graphite MCP instead of standard `git` commands. Use Graphite MCP when it can handle the request, as opposed to the `gh` CLI tool.
- Never do `git add -A`, always be specific with the files we're adding so we don't inadvertently commit files we didn't intend to.
- When you want to set a Pull Requests description, use `gh pr edit` because we have a default template that applies on initial PR creation. So we need to wait for this to be created before we can update it.

## General React Testing

- Match text with exact string for critical elements: expect(screen.getByText('Exact match')).toBeInTheDocument()
- Use regex for partial/flexible matching: expect(screen.getByText(/Partial match/)).toBeInTheDocument()
- For UI elements that shouldn't exist, use expect(screen.queryByText(/text/)).not.toBeInTheDocument()
- Use data-testid attributes for targeting UI elements that don't have reliable text content
- Use Time.zone.now to get the current time
- Always use setTestGate to mock Statsig feature gates

## Puppeteer MCP

### Text-Based Selection in Puppeteer MCP

When working with Puppeteer MCP in Claude Code, use these patterns to select elements by their visible text content:

#### Best Methods for Text Selection

1. **XPath with text matching**:

   ```javascript
   puppeteer_evaluate({
     script: `
       const element = document.evaluate(
         '//*[text()="Exact Match"]',
         document,
         null,
         XPathResult.FIRST_ORDERED_NODE_TYPE,
         null
       ).singleNodeValue;
       if (element) element.click();
     `
   });
   ```

2. **XPath with partial text matching**:

   ```javascript
   puppeteer_evaluate({
     script: `
       const element = document.evaluate(
         '//*[contains(text(), "Partial Match")]',
         document,
         null,
         XPathResult.FIRST_ORDERED_NODE_TYPE,
         null
       ).singleNodeValue;
       if (element) element.click();
     `
   });
   ```

3. **Find element by text with querySelectorAll**:

   ```javascript
   puppeteer_evaluate({
     script: `
       const elements = Array.from(document.querySelectorAll('*'));
       const element = elements.find(el => el.textContent.includes('Text to find'));
       if (element) element.click();
     `
   });
   ```

4. **Find specific element types with text**:

   ```javascript
   puppeteer_evaluate({
     script: `
       const buttons = Array.from(document.querySelectorAll('button'));
       const targetButton = buttons.find(btn => btn.textContent.includes('Submit'));
       if (targetButton) targetButton.click();
     `
   });
   ```

#### Example Usages

- **Click a button with specific text**:

   ```javascript
   puppeteer_evaluate({
     script: `
       const buttons = Array.from(document.querySelectorAll('button'));
       const loginButton = buttons.find(btn => btn.textContent.trim() === 'Login');
       if (loginButton) loginButton.click();
     `
   });
   ```

- **Fill form based on label text**:

   ```javascript
   puppeteer_evaluate({
     script: `
       const labels = Array.from(document.querySelectorAll('label'));
       const usernameLabel = labels.find(label => label.textContent.includes('Username'));
       if (usernameLabel && usernameLabel.htmlFor) {
         const input = document.getElementById(usernameLabel.htmlFor);
         if (input) input.value = 'myusername';
       }
     `
   });
   ```

- **Click an anchor/link with specific text**:

   ```javascript
   puppeteer_evaluate({
     script: `
       const links = Array.from(document.querySelectorAll('a'));
       const settingsLink = links.find(link => link.textContent.includes('Settings'));
       if (settingsLink) settingsLink.click();
     `
   });
   ```

### Tips

- Add error handling to prevent script failures
- Use `.trim()` to ignore whitespace in text comparisons
- Consider case-insensitive matching with `.toLowerCase()`
- For complex UIs, narrow the search scope to a specific container first
- Use `.textContent` rather than `.innerText` for more reliable text extraction
- Always test your selectors in simple scenarios first before using them in more complex automation flows.
- Files should always have an empty newline at the end

## Component Design Patterns

### Component Organization

- Extract common UI elements into standalone components
- Keep styling with the component that owns it
- Use props to make components flexible rather than duplicating similar components
- Consider the "Single Responsibility Principle" when deciding component boundaries

### Sheet Components

- Keep sheet content in separate components from the triggering logic
- Use consistent patterns for action buttons (primary action, secondary/dismiss action)
- Extract repeated visual elements into reusable components

### Variable Naming

- Avoid prefixing variables with underscores unless they are truly private class members
- For state variables that aren't actively used, consider whether they're necessary at all
- Use descriptive names that indicate both type and purpose (e.g., 'showSuggestedAddressSheet' rather than just 'showSheet')

- After making changes to a test, run the entire files tests to ensure we didn't break anything else

## RSpec Testing Principles

- For queries (like .unmatched), calling subject multiple times is usually fine
  since it returns the same relation
- For commands that create/modify data (like .parse_from_isolated_icl_file!),
  we should store the result in a variable to avoid multiple executions
- RSpec's subject is lazily evaluated but NOT memoized by default
- We prefer NOT to mock behavior that doesn't need to be mocked.
  - Mocking API calls makes sense. Mocking a method that creates a model entry in the database does not.

## TypeScript and Linting Checks

### Always Check for TypeScript and Linting Issues

After making changes to TypeScript/JavaScript files, ALWAYS run these checks:

1. **Check TypeScript errors for modified files**:

```bash
# For specific files (faster)
npx tsc --noEmit path/to/file1.tsx path/to/file2.tsx

# Note: Running tsc on entire project is very slow, avoid unless necessary
```

2. **Specifically check for await in non-async functions (TS1308)**:

```bash
# Check for TS1308 errors specifically - await in non-async functions
npx tsc --noEmit path/to/file1.tsx path/to/file2.tsx 2>&1 | grep "TS1308"

# If any output appears, it means there are await expressions in non-async functions that need fixing
# Example error: "error TS1308: 'await' expressions are only allowed within async functions"
```

3. **Check and fix linting issues**:

```bash
# Check linting issues for specific files
npx eslint path/to/file1.tsx path/to/file2.tsx --ext .ts,.tsx

# Auto-fix linting issues (trailing spaces, formatting, etc.)
npx eslint path/to/file1.tsx path/to/file2.tsx --ext .ts,.tsx --fix
```

4. **Common issues to watch for**:

- Trailing spaces (auto-fixable with --fix)
- Missing trailing commas (auto-fixable with --fix)
- Missing newline at end of file (auto-fixable with --fix)
- Arrow function parentheses (auto-fixable with --fix)
- String concatenation vs template literals (prefer template literals)
- Unexpected `any` types (specify proper types)

**IMPORTANT**: Always run eslint with --fix after making changes to automatically fix formatting issues before committing.

## Local Development Testing

### Hardcoding Values for Testing

When temporarily hardcoding values for local development testing, follow this pattern:

```javascript
// TODO: Remove testing code and uncomment production line
// const shouldShowFeature = !user.hasFeature && otherCondition;
const shouldShowFeature = true && otherCondition;
```

**Style Guidelines:**

- Add a TODO comment on its own line explaining what needs to be done
- Comment out the production code directly below the TODO
- Add the temporary testing code on the next line
- Keep any conditions that should still be evaluated (like `&& otherCondition`)
- Never use explanatory comments on the same line as the testing code

**Good Example:**

```javascript
// TODO: Remove testing code and uncomment production line
// const shouldShowUpsell = !newBankAccount.supports_rtp && !linkedDebitCard;
const shouldShowUpsell = true && !linkedDebitCard;
```

**Bad Example:**

```javascript
const shouldShowUpsell = !false && !linkedDebitCard; // Temporarily forcing supports_rtp to false for testing
```

This makes it immediately clear what's temporary testing code and what the production code should be.

## Development Guidelines

### Philosophy

#### Core Beliefs

- **Incremental progress over big bangs** - Small changes that compile and pass tests
- **Learning from existing code** - Study and plan before implementing
- **Pragmatic over dogmatic** - Adapt to project reality
- **Clear intent over clever code** - Be boring and obvious

#### Simplicity Means

- Single responsibility per function/class
- Avoid premature abstractions
- No clever tricks - choose the boring solution
- If you need to explain it, it's too complex

### Process

#### 1. Planning & Staging

Break complex work into 3-5 stages. Document in `IMPLEMENTATION_PLAN.md`:

```markdown
### Stage N: [Name]
**Goal**: [Specific deliverable]
**Success Criteria**: [Testable outcomes]
**Tests**: [Specific test cases]
**Status**: [Not Started|In Progress|Complete]
```

- Update status as you progress
- Remove file when all stages are done

#### 2. Implementation Flow

1. **Understand** - Study existing patterns in codebase
2. **Test** - Write test first (red)
3. **Implement** - Minimal code to pass (green)
4. **Refactor** - Clean up with tests passing
5. **Commit** - With clear message linking to plan

#### 3. When Stuck (After 3 Attempts)

**CRITICAL**: Maximum 3 attempts per issue, then STOP.

1. **Document what failed**:
   - What you tried
   - Specific error messages
   - Why you think it failed

2. **Research alternatives**:
   - Find 2-3 similar implementations
   - Note different approaches used

3. **Question fundamentals**:
   - Is this the right abstraction level?
   - Can this be split into smaller problems?
   - Is there a simpler approach entirely?

4. **Try different angle**:
   - Different library/framework feature?
   - Different architectural pattern?
   - Remove abstraction instead of adding?

### Technical Standards

#### Architecture Principles

- **Composition over inheritance** - Use dependency injection
- **Interfaces over singletons** - Enable testing and flexibility
- **Explicit over implicit** - Clear data flow and dependencies
- **Test-driven when possible** - Never disable tests, fix them

#### Code Quality

- **Every commit must**:
  - Compile successfully
  - Pass all existing tests
  - Include tests for new functionality
  - Follow project formatting/linting

- **Before committing**:
  - Run formatters/linters
  - Self-review changes
  - Ensure commit message explains "why"

#### Error Handling

- Fail fast with descriptive messages
- Include context for debugging
- Handle errors at appropriate level
- Never silently swallow exceptions

### Decision Framework

When multiple valid approaches exist, choose based on:

1. **Testability** - Can I easily test this?
2. **Readability** - Will someone understand this in 6 months?
3. **Consistency** - Does this match project patterns?
4. **Simplicity** - Is this the simplest solution that works?
5. **Reversibility** - How hard to change later?

### Project Integration

#### Learning the Codebase

- Find 3 similar features/components
- Identify common patterns and conventions
- Use same libraries/utilities when possible
- Follow existing test patterns

#### Tooling

- Use project's existing build system
- Use project's test framework
- Use project's formatter/linter settings
- Don't introduce new tools without strong justification

### Quality Gates

#### Definition of Done

- [ ] Tests written and passing
- [ ] Code follows project conventions
- [ ] No linter/formatter warnings
- [ ] Commit messages are clear
- [ ] Implementation matches plan
- [ ] No TODOs without issue numbers

#### Test Guidelines

- Test behavior, not implementation
- Clear test names describing scenario
- Use existing test utilities/helpers
- Tests should be deterministic
- Where possible, combine test assertions into the same test, especially if there's no change in the context / input data for the test

### Important Reminders

**NEVER**:

- Use `--no-verify` to bypass commit hooks
- Disable tests instead of fixing them
- Commit code that doesn't compile
- Make assumptions - verify with existing code

**ALWAYS**:

- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess

- Always use Conventional Commits naming standards

## Project Working Context

Working documents for current tasks are stored in `~/scratch/`. Create a subdirectory for each task or feature you're working on (e.g., `~/scratch/bank-723-repayment/`).

Reference these files in conversations with `@~/scratch/<task-name>/filename.md`.
