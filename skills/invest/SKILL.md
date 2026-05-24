---
name: invest
description: "Read investment portfolio from Google Sheets via GWS CLI, parse holdings, compute aggregates, load T6 template, and return structured data ready for report generation. Used by /invest command."
---

# Invest Portfolio Reader Skill

Reads a Google Sheets investment portfolio using GWS CLI, computes portfolio analytics,
loads the T6 investment report template, and produces structured data for the `/invest`
command to generate a premium-quality investment report.

## Prerequisites

- `gws` CLI authenticated (`gws auth login`)
- `INVEST_DEFAULT_SHEET_URL` set in `~/.claude/settings.local.json` env block
- `jq` available in PATH

---

## Procedure

### Step 1 — Resolve Spreadsheet ID

Extract the spreadsheet ID from the URL (segment between `/d/` and `/edit` or `?`):

```bash
SHEET_URL="<resolved URL>"
SHEET_ID=$(echo "$SHEET_URL" | sed 's|.*spreadsheets/d/||' | sed 's|[/?].*||')
echo "Spreadsheet ID: $SHEET_ID"
```

### Step 2 — Fetch Sheet Names

```bash
gws sheets spreadsheets get \
  --params "{\"spreadsheetId\": \"$SHEET_ID\"}" 2>/dev/null \
  | jq '.sheets[].properties | {title, sheetId}'
```

Identify data-bearing sheets (Holdings, Log, TransactionHistory, summary sheets).
Skip empty or layout-only sheets.

### Step 3 — Read All Sheets (run in parallel)

For each data sheet found:

```bash
gws sheets +read --spreadsheet "$SHEET_ID" --range "<SheetName>" 2>/dev/null
```

Priority: `Holdings` first (primary source), then summary sheets (Sheet6, Dashboard, etc.).

### Step 4 — Parse Holdings Data

From the Holdings sheet, extract per-row:

| Field | Column | Notes |
|-------|--------|-------|
| Owner | C | Owner name |
| Asset Class (L1) | D | Stocks, Pension, Gold, Crypto, Cash |
| Asset Class (L2) | E | Korean stocks, US stocks, Bitcoin, Lease deposit, etc. |
| Account | F | Brokerage / account name |
| Asset Name | G | Asset or stock name |
| Ticker / Symbol | H | Ticker |
| Avg Cost (KRW) | I | Average cost in KRW |
| Avg Cost (USD) | J | Average cost in USD (if applicable) |
| Current Price | K | Current price |
| Quantity | L | Number of units |
| USD/KRW Rate | M | Exchange rate applied |
| Total Invested (KRW) | N | Total cost basis in KRW |
| Current Value (KRW) | O | Current market value in KRW |
| Return % | P | Percentage return |
| P&L (KRW) | Q | Profit / loss in KRW |

### Step 5 — Compute Portfolio Aggregates

Calculate and produce structured data for the T6 template:

**A. Portfolio Summary**
- Total invested, total current value, total P&L, total return %
- USD/KRW rate (as applied in the sheet)
- Number of holdings (row count in Holdings sheet)

**B. Owner-level Aggregates** — for each owner:
- Invested, current value, P&L, return %

**C. Asset Class Composition** — by L1 asset class:
- Sum of current value and share of total (%)
- Pre-computed as integers for Mermaid `pie` chart

**D. Performance Rankings**
- TOP 5: descending by return %
- Loss positions: all rows where return % < 0

**E. Concentration Risk Flags**
- Single asset > 20% of portfolio → 🚨 flag with name and weight
- Single asset class > 40% of portfolio → ⚠️ flag

**F. Mermaid Numeric Values** — pre-compute for chart injection:
- `pie`: asset class weights (integer, no decimals)
- `xychart-beta` P&L bar: P&L by asset class (KRW millions, 1 decimal)
- `xychart-beta` FX line: rate forecast array (from search results)
- `xychart-beta` allocation bar/line: current vs. target allocation arrays
- `quadrantChart` risk coordinates: (x, y) per risk item in [0, 1]
- `quadrantChart` action coordinates: (x, y) per action item in [0, 1]

### Step 6 — Load T6 Template

Load `templates/research/T6-investment-report.md` via the `Read` tool using the
plugin-cache path:

```bash
_TPL=$(find "$HOME/.claude/plugins/cache" -path "*/claude-skills/*/templates/research" -type d 2>/dev/null | sort -rV | head -1)
[ -z "$_TPL" ] && _TPL="templates/research"
# Read: $_TPL/T6-investment-report.md
```

This template defines the common structure and table of contents for all `/invest` reports.

### Step 7 — Mermaid Rendering Guidelines

When filling in Mermaid diagrams from the T6 template, strictly follow:

**1. English-only labels in all Mermaid diagrams**
- No Korean text in diagram labels, axis names, or node text
- Use English abbreviations or translations where needed
- Plain markdown text (tables, paragraphs) may use any language

**2. Supported diagram types (WeasyPrint PDF safe)**
- `pie` ✅ — asset allocation
- `gantt` ✅ — roadmap (use `YYYY-MM` dateFormat)
- `xychart-beta` ✅ — bar/line charts (numeric arrays only)
- `graph LR` / `graph TD` ✅ — strategy flow diagrams
- `quadrantChart` ✅ — risk/action matrix (coordinates 0.0–1.0)

**3. xychart-beta numeric constraints**
- y-axis range must span actual data: set min 10–20% below lowest value
- bar/line arrays must have same length as x-axis labels
- Use integer or 1-decimal values only

**4. quadrantChart coordinate format**
- Each item: `Label Name : [x, y]` where x, y ∈ [0.0, 1.0]
- Spaces in labels are fine; no Korean characters
- Quadrant labels must be short (≤ 20 chars)

**5. gantt date ranges**
- Always use `dateFormat YYYY-MM` for month-level granularity
- Task format: `Task Name : start-YYYY-MM, end-YYYY-MM`
- Milestone format: `Event Name : milestone, YYYY-MM-DD, 0d`

Output the computed data and the loaded T6 template structure to the `/invest` command
for report generation in the next steps.
