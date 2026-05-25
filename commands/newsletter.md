# /newsletter — Gmail label-based newsletter curation report: $ARGUMENTS

Fetch messages from a Gmail label, classify them by topic with AI,
and generate a premium intelligence digest report using the T7 template.

## Usage

```
/newsletter --label "Read Later/Newsletter"   → last 7 days, newsletter label
/newsletter --label Label_39                   → specify label by ID directly
/newsletter --label "Newsletter" --days 14     → last 2 weeks
/newsletter --label Label_39 --days 3          → last 3 days
/newsletter --label "IITP" --days 30           → partial label name match
```

**Parameters**:
- `--label <name|id>` : Gmail label name (partial match) or ID (`Label_XXX`). **Required**.
- `--days N` : Lookback window in days. Default `7`, max `90`.

---

## Procedure

### Step 1 — Parse Arguments

From `$ARGUMENTS` extract:
- `--label <value>` → `LABEL_ARG`
- `--days <N>` → `DAYS` (default 7, max 90)
- If `--label` is missing, print usage and exit:
  `Usage: /newsletter --label <label name or ID> [--days N]`

### Step 2 — Resolve Script Path (parallel with Step 3)

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "gmail_fetch_newsletter.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/gmail_fetch_newsletter.py"
```

### Step 3 — Resolve Label ID (parallel with Step 2)

If `LABEL_ARG` starts with `Label_` or is a short numeric string, use it directly as `LABEL_ID`.

Otherwise, look up by name:

```bash
uv run python "$_S" \
  --label-id dummy --list-labels 2>/dev/null \
  | jq -r '[.[] | select(.type=="user") | {id, name}]'
```

Use the first entry whose `name` contains `LABEL_ARG` (case-insensitive) as `LABEL_ID`.
If not found, print available labels and exit.

### Step 4 — Load T7 Template (parallel with Steps 2 & 3)

Resolve template path:
```bash
_TPL=$(find "$HOME/.claude/plugins/cache" -path "*/claude-skills/*/templates/research" -type d 2>/dev/null | sort -rV | head -1)
[ -z "$_TPL" ] && _TPL="templates/research"
```

Load `$_TPL/T7-newsletter-curation.md` with the Read tool.

### Step 5 — Fetch Messages

```bash
uv run python "$_S" \
  --label-id "$LABEL_ID" \
  --days "$DAYS" \
  --max-results 40 \
  2>/dev/null
```

If the result is an empty array (`[]`), print "No messages found for this label in the specified time range." and exit.

### Step 6 — Curate Using Skill

Load `skills/newsletter/SKILL.md` with the Read tool and follow **Steps 4–9** to:

1. **Classify messages** — AI & Engineering / Big Tech & Investment / Startup & Product / Tools & Infrastructure / Other
2. **Extract keywords** — Top 5 keywords per category (for mindmap)
3. **Build Gantt milestones** — extract events with specific dates
4. **Format items** — convert each message to analytical summary + links block
5. **Compute aggregates** — category counts, top 3 senders, top 3 key insights
6. **Fill T7 template** — replace all `[[PLACEHOLDER]]` values

### Step 7 — Save File

Output path: `${BASE_DIR:+$BASE_DIR/}notes/newsletters/newsletter-{LABEL_SLUG}-YYYY-MM-DD.md`

- `LABEL_SLUG`: remove special chars/emoji/spaces from label name → lowercase → join with `-`
  - e.g., `Read Later/Newsletter` → `read-later-newsletter`
  - e.g., `Label_39` → `label-39`
- `YYYY-MM-DD`: today's date
- If the same file already exists today, append `-2`, `-3` suffix

Create directory if missing:
```bash
mkdir -p "${BASE_DIR:+$BASE_DIR/}notes/newsletters"
```

### Step 8 — Report Completion

```
## Newsletter Curation Complete

Saved to   : notes/newsletters/<filename>.md
Label      : <label_name>
Period     : <start_date> ~ <end_date> (<DAYS> days)
Analyzed   : <TOTAL> messages (AI: <N>, BigTech: <N>, Startup: <N>, Tools: <N>, Other: <N>)

Key Insights:
• <insight_1>
• <insight_2>
• <insight_3>
```
