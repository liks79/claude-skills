Classify Gmail emails by importance and summarize them by period. $ARGUMENTS

---

## Usage

```
/email-summary        → Summary for the last 7 days (default)
/email-summary 1      → Today only
/email-summary 3      → Last 3 days
/email-summary 30     → Last 30 days (grouped by week)
```

The parameter is a number between 1 and 30.

## Classification Criteria

| Category | Criteria |
|----------|----------|
| 🔴 Requires immediate attention | Action keywords: invitation, approval, payment, interview, warning, etc. |
| 🟡 Important | Key senders: GitHub, AWS, government agencies, etc. |
| 🔵 Informational / Notification | General notifications, service announcements |
| ⚪ Ads / Newsletter | Ad keywords, marketing senders |

## Procedure

1. Parse the number from `$ARGUMENTS`. If not provided, use the default value of 7.
   - Clamp to the range 1–30.

2. Run the following command:

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "email_summary.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S=".claude/scripts/email_summary.py"
uv run python "$_S" --days <N>
```

3. Show the script output to the user as-is.

4. If needed, add additional explanation for specific emails.
