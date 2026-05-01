List the most recently created or updated files in the repository. $ARGUMENTS

---

## Usage

```
/recent        → 10 most recent files (default)
/recent 5      → 5 most recent files
/recent 20     → 20 most recent files
```

The parameter is the number of files to retrieve. If omitted, displays 10.

## Procedure

Run the following script and show its output to the user as-is:

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "recent.sh" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S=".claude/scripts/recent.sh"
bash "$_S" $ARGUMENTS
```

- Output the script results **exactly as-is**. Do not modify or reinterpret the content.
- If the script fails, pass the error message to the user.
