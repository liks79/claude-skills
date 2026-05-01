Show GitHub URLs for files changed in the last 7 days (default) or a specified period. $ARGUMENTS

---

## Usage

```
/github-urls          → 5 most recently changed files (default)
/github-urls 10       → 10 most recently changed files
/github-urls --pr 42  → Files changed in a specific PR
/github-urls <sha>    → Files changed in a specific commit
```

## Procedure

Run the following script and show its output to the user as-is:

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "github-urls.sh" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S=".claude/scripts/github-urls.sh"
bash "$_S" $ARGUMENTS
```

- Output the script results **exactly as-is**. Do not modify or reinterpret the content.
- If the script fails, pass the error message to the user.
