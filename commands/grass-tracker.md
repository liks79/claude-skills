Show GitHub contribution graph (commit streak) status. $ARGUMENTS

---

## Usage

```
/grass-tracker           → Look up the current git account by default
/grass-tracker <username> → Look up a different GitHub user
```

## Procedure

1. Determine username:
   - If `$ARGUMENTS` is provided, use that value
   - Otherwise, auto-detect in the following order:
     ```bash
     gh api user --jq '.login' 2>/dev/null \
       || git config --get github.user 2>/dev/null \
       || echo ""
     ```
   - If detection fails, ask the user to enter a username

2. Find and run the grass-tracker script in the following order:

```bash
# First priority: plugin cache
SCRIPT=$(find "$HOME/.claude/plugins/cache" -name "grass-tracker.sh" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
# Second priority: local repo
[ -z "$SCRIPT" ] && [ -f ".claude/scripts/grass-tracker.sh" ] && SCRIPT=".claude/scripts/grass-tracker.sh"
# Third priority: PATH
[ -z "$SCRIPT" ] && command -v grass-tracker.sh &>/dev/null && SCRIPT="grass-tracker.sh"
```

   If the script is not found, output basic contribution status using GitHub CLI:

```bash
gh api "users/<username>" --jq '"User: \(.login)\nFollowers: \(.followers)\nPublic Repos: \(.public_repos)"'
gh api "users/<username>/events" --paginate --jq '[.[] | select(.type=="PushEvent")] | length | "Recent push events: \(.)"'
```

3. Show the output to the user as-is.
4. If the script fails, pass the error message to the user.

> **Installation**: Installing grass-tracker enables a richer ASCII contribution chart.
> After installation, copy to `.claude/scripts/grass-tracker.sh` or add to PATH.
