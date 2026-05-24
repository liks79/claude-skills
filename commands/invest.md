# /invest — Generate an investment portfolio analysis report: $ARGUMENTS

Reads a Google Sheets portfolio via GWS CLI, combines it with the latest market
news and events, and produces a premium financial report based on the
**T6 Investment Report template**.
Output is saved to `reports/finance/investment-report-YYYY-MM-DD.md`.

## Usage

```
/invest                → uses INVEST_DEFAULT_SHEET_URL from settings.local.json
/invest <sheet_url>    → uses the specified Google Sheets URL
```

---

## Procedure

### Step 1 — Resolve Sheet URL

If `$ARGUMENTS` starts with `https://docs.google.com/spreadsheets/`, use that URL.
Otherwise use the `INVEST_DEFAULT_SHEET_URL` environment variable.

```bash
SHEET_ID=$(echo "$SHEET_URL" | sed 's|.*spreadsheets/d/||' | sed 's|[/?].*||')
```

---

### Step 2 — Collect Portfolio Data + Load Template (parallel)

**Run both tasks concurrently**:

1. **Load the `invest` skill via the `Read` tool** — execute Procedure Steps 1–7:
   - Read all sheets via GWS CLI
   - Compute aggregates (by owner, by asset class, performance rankings, concentration flags)
   - Pre-compute Mermaid chart numeric arrays

   Resolve the skill path:
   ```bash
   _SK=$(find "$HOME/.claude/plugins/cache" -name "SKILL.md" -path "*/claude-skills/*/skills/invest/*" 2>/dev/null | sort -rV | head -1)
   [ -z "$_SK" ] && _SK="skills/invest/SKILL.md"
   ```

2. **Load the T6 template via the `Read` tool**:

   ```bash
   _TPL=$(find "$HOME/.claude/plugins/cache" -path "*/claude-skills/*/templates/research" -type d 2>/dev/null | sort -rV | head -1)
   [ -z "$_TPL" ] && _TPL="templates/research"
   # file: $_TPL/T6-investment-report.md
   ```

---

### Step 3 — Fetch Latest Market Data (WebSearch — 4 parallel queries)

| Topic | Query |
|-------|-------|
| USD/KRW exchange rate outlook | `"USD KRW exchange rate forecast" [current_year] H2 institutional forecast` |
| U.S. economic event calendar | `FOMC CPI PCE "Fed rate" [current_year] [current_month+1] [current_month+2] calendar` |
| Big Tech / AI / semiconductor outlook | `"big tech" OR "AI stocks" OR "semiconductors" stock outlook [current_year] H2` |
| Korea economy / KOSPI / BTC | `"KOSPI outlook" OR "bitcoin" [current_year] H2 forecast` |

From each search, extract:
- **FX**: current rate, monthly forecast values (for Mermaid xychart line array), direction, portfolio impact
- **Events**: FOMC/CPI/NFP dates → convert to Mermaid gantt milestone dates
- **Big Tech**: outlook rating and risk per holding (AMZN, GOOGL, VGT, QQQM, SCHD)
- **BTC**: current trend, direction, portfolio handling recommendation

---

### Step 4 — Write Report Based on T6 Template

Fill in **all sections** of the T6 template. Replace every `[...]` placeholder with
real data, following these principles:

#### Writing Principles

**Data Integrity**
- All figures must cite actual values read from the GWS sheet
- Return %, P&L, and current value must be calculated accurately per row
- Aggregate totals must match the sum of individual items

**Mermaid Diagrams (follow SKILL.md Step 7 guidelines)**
- Labels must be **English only** (Korean text causes rendering failures)
- `pie`: insert integer values for asset class weights
- `xychart-beta`: numeric arrays only; y-axis range should be 10–20% wider than data
- `gantt`: `dateFormat YYYY-MM`, include economic event milestones
- `quadrantChart`: coordinates 0.0–1.0, English labels, max 6 items
- `graph LR`: Big Tech strategy flowchart

**Market-Linked Analysis**
- Connect news/events directly to specific holdings
  - e.g., "FOMC rate hold → SCHD/dividend stocks benefit"
  - e.g., "AMZN AWS growth acceleration → additional upside beyond current return"
- Analyze BTC independently in Section 4.4

**Action Specificity**
- State sell/buy quantities, amounts, and estimated tax figures explicitly
- Maintain context per owner
- Include target dates in Immediate actions

**Visual Quality**
- Keep `---` separators before each major section
- Bold key figures
- Use ★★★★☆ for ratings; 🔴/🟡/🟢 for risk levels
- Maintain section numbers (1–8) matching template structure

---

### Step 5 — Save File

```
path: ${BASE_DIR:+$BASE_DIR/}reports/finance/investment-report-YYYY-MM-DD.md
```

`YYYY-MM-DD` is today's date. If run twice on the same day, append `-2`, `-3` suffixes.

---

### Step 6 — Report Completion

Provide the user with:

- **Output path**
- **Portfolio summary**: total value / total P&L / return %
- **Top 3 key findings** (bullets)
- **Top 3 immediate actions** (bullets)
