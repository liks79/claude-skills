---
name: newsletter
description: "Fetch Gmail messages by label via gmail_fetch_newsletter.py, classify by topic (AI/BigTech/Startup/Tools/Other), extract key links and insights, and return structured data ready for T7 report generation. Used by /newsletter command. Triggers when: /newsletter command is invoked, user asks to curate newsletters from Gmail, user wants to generate a newsletter intelligence digest."
---

# Newsletter Curation Skill

Fetches and curates Gmail newsletter content by label using the gws CLI Python script,
classifies messages by topic, and produces structured data for the `/newsletter` command
to generate a premium intelligence digest report.

## Prerequisites

- `gws` CLI authenticated (`gws auth login`)
- `uv` available in PATH
- `gmail_fetch_newsletter.py` script available via plugin-cache path resolution

---

## Procedure

### Step 1 — Resolve Script Path

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "gmail_fetch_newsletter.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/gmail_fetch_newsletter.py"
```

### Step 2 — Resolve Label

If the user passes a label name (not an ID starting with `Label_`), resolve it:

```bash
uv run python "$_S" --label-id dummy --list-labels 2>/dev/null \
  | jq '[.[] | select(.type=="user") | {id, name}]'
```

Match the user-supplied string against `name` (case-insensitive, partial match OK).
If no match, abort with a message listing available user labels.

If the argument already looks like a label ID (`Label_\d+` or `Label_[a-f0-9]+`),
use it directly.

### Step 3 — Fetch Messages

```bash
uv run python "$_S" \
  --label-id "$LABEL_ID" \
  --days "$DAYS" \
  --max-results 40 \
  2>/dev/null
```

Output: JSON array of `{id, from, subject, date, snippet, body_text, links}`.

If empty array → report "No messages found for this label in the specified time range." and stop.

### Step 4 — Classify Messages by Topic

For each message, analyze `from + subject + snippet + body_text` and assign one of:

| Category | Key Signals |
|----------|-------------|
| **AI & Engineering** | LLM, GPT, Claude, Gemini, Copilot, AI, ML, model, coding, developer, deep learning, RAG, agent, vibe coding, ChatGPT, Anthropic, OpenAI, inference, reasoning |
| **Big Tech & Investment** | Google, Apple, Microsoft, Meta, Amazon, NVIDIA, big tech, stock price, investment, M&A, market cap, earnings, funding, valuation |
| **Startup & Product** | startup, launch, funding, Series A/B/C, ProductHunt, new service, beta, Kickstarter |
| **Tools & Infrastructure** | Railway, Docker, K8s, AWS, GCP, Azure, Slack, GitHub, DevOps, infrastructure, CI/CD, SDK |
| **Other** | everything else |

Each message gets exactly one category (best match wins; AI > BigTech > Startup > Tools > Other).

### Step 5 — Extract Keywords for Word Cloud

From all `subject` + `snippet` text, extract:
- Top 20 significant nouns/terms (exclude stopwords: the, a, an, is, in, of, to, for, and, or, with, your, our, this, that)
- Group by category
- Output as nested list for Mermaid mindmap

Format for mindmap:
```
      AI_KEYWORD_1
      AI_KEYWORD_2
```
(8 spaces + term, under the parent category branch)

### Step 6 — Build Gantt Milestones

For messages with specific event dates (e.g., "May 27", deadline mentions):
- Extract the date
- Create gantt task: `    Task_Name : milestone, YYYY-MM-DD, 0d`
- Group under appropriate category section

For non-event messages, use `dateOnly` as a 1-day task span.

### Step 7 — Format Each Item for T7 Template

For each classified message, produce a markdown block:

```markdown
### N.M [Subject — cleaned up, no emoji spam]
**Source** · [Sender Name] · [Date dd MMM YYYY]

[2~3 sentence analytical summary — synthesize body_text + snippet.
Focus on what this means for the reader, not just what it says.
Use analyst voice: "what this signals is", "the key takeaway is", "from an engineer's perspective"...]

**Why it matters**: [1 sentence takeaway in bold]

**Links**:
- [Link 1 Label](URL)
- [Link 2 Label](URL)   ← include only meaningful links (2~3 max per item)

---
```

**Quality rules**:
- Never just copy the snippet verbatim — synthesize
- For AI items: connect to practical developer use
- For BigTech: connect to market/investment implications
- For Startups: note the "so what" for engineers or investors
- Skip links that look like tracking pixels or unsubscribe URLs

### Step 8 — Compute Aggregates

- `TOTAL_MESSAGES`: total count
- Category counts: AI_COUNT, BIGTECH_COUNT, STARTUP_COUNT, TOOLS_COUNT, OTHER_COUNT
- `TOP_SENDERS`: top 3 sender domains (e.g., "Railway, Substack, IITP")
- `WEEK_LABEL`: e.g., "Week of May 19"
- `START_DATE`, `END_DATE`: actual date range of fetched messages
- `KEY_INSIGHT_1~3`: one-sentence summary of the most important finding per top category

### Step 9 — Load T7 Template

Resolve template path:
```bash
_TPL=$(find "$HOME/.claude/plugins/cache" -path "*/claude-skills/*/templates/research" -type d 2>/dev/null | sort -rV | head -1)
[ -z "$_TPL" ] && _TPL="templates/research"
```

Read `$_TPL/T7-newsletter-curation.md` and replace all `[[PLACEHOLDER]]` values
with computed data from Steps 4–8.

Output the filled report string to the `/newsletter` command for file saving.

---

## Section Placement Priority

1. **🤖 AI & Engineering** — highest priority for AI-focused engineers. Each item includes "engineer's perspective" insight.
2. **📈 Big Tech & Investment** — big tech strategic shifts and market-moving events. Add investor-angle commentary.
3. **🚀 Startup & Product** — notable new products and funding. Add "why you should try this" one-liner.
4. **🔧 Tools & Infrastructure** — dev tools and infra updates.
5. **📋 Other**

## Empty Section Handling

If a section has 0 items: `> No relevant content in this period.` — one line only.

## Link Filtering Rules

- Exclude tracking/unsubscribe URLs (track., pixel., unsubscribe, etc.)
- Max 3 links per item
- Use meaningful labels for link text, not raw URLs

---

## Mermaid Guidelines

English labels only in diagrams — no non-ASCII characters in node labels.
For the mindmap, use short English/abbreviated terms only.

Example mindmap leaf expansion:
```
    🤖 AI & Dev
      LLM
      Claude
      Vibe-Coding
      n8n
```

For the gantt, use `dateFormat YYYY-MM-DD` and `axisFormat %m/%d`.
For pie chart, use integer values only.
