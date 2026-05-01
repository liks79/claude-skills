Fetch the current listing status of a specific apartment complex from Naver Real Estate and generate a report: $ARGUMENTS

## Usage

```
/apt-watch <complex_number or URL> [--name complex_name] [--location region] [--type sale|lease|all] [--no-db] [--pdf]
```

| Argument | Description | Default |
|----------|-------------|---------|
| `complex_number or URL` | Naver Real Estate complex ID or complex URL | Required |
| `--name TEXT` | Complex name (displayed as "Complex Number" if omitted) | — |
| `--location TEXT` | Region label for display (e.g., Seoul Gangnam-gu) | — |
| `--type` | sale \| lease \| all | all |
| `--no-db` | Snapshot only, without saving to the change-tracking DB | — |
| `--pdf` | Also convert to PDF | — |

**How to find the complex number**: Paste the Naver Real Estate complex URL directly, or enter just the number.
- URL: `https://fin.land.naver.com/complexes/25937` → automatically extracts `25937`
- Number: entering `25937` directly also works

Examples:
```
/apt-watch 25937
/apt-watch https://fin.land.naver.com/complexes/25937
/apt-watch 25937 --name e편한세상센트레빌 --location 경기 광명시
/apt-watch 10000 --type 전세 --name 래미안대치팰리스
/apt-watch 25937 --type 매매 --pdf
```

---

## Data Sources

- **Naver Real Estate** (`fin.land.naver.com`) — listing prices (asking prices)
- Separate from MOLIT official transaction prices — **asking prices may differ from actual transaction prices**
- Change tracking (new/removed listings): SQLite snapshot accumulation (`reports/.apt-watch/<number>.db`)

---

## Procedure

### Step 1 — Parse Arguments

Extract from `$ARGUMENTS`:
- `complex_number`: first token (numeric)
- `name`: value from `--name`
- `location`: value from `--location`
- `trade_type`: value from `--type` (default: all)
- `no_db`: whether `--no-db` is present
- `pdf_flag`: whether `--pdf` is present

### Step 2 — Determine Output Path

Prepend `$BASE_DIR/` if the environment variable is set:

```
output_path = ${BASE_DIR:+$BASE_DIR/}reports/apt-watch-<complex_number>-<YYYYMMDD>.md
```

### Step 3 — Run Script

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "apt_watch.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S=".claude/scripts/apt_watch.py"
uv run --with "httpx[http2]" \
    python "$_S" <complex_number> \
    [--name <name>] \
    [--location <location>] \
    --type <trade_type> \
    [--no-db] \
    --output <output_path>
```

- stderr progress logs (e.g., `Page N: M listings`, `Collection complete`) are normal output
- HTTP 429 retry logs are also normal (up to 4 retries, with automatic backoff)
- stderr starting with `Error:` → explain the cause and stop

### Step 4 — PDF Conversion (only if --pdf flag is present)

Dynamically locate and execute the script path:

```bash
PDF_SCRIPT=$(find "$HOME/.claude/plugins/cache" -path "*/pdf-creator/*/md_to_pdf.py" 2>/dev/null | sort -rV | head -1)
if [ -z "$PDF_SCRIPT" ]; then
    echo "⚠️  pdf-creator skill is not installed. Please install pdf-creator from the Claude Marketplace."
    exit 1
fi
uv run --with weasyprint python "$PDF_SCRIPT" <output_path> --theme tech-modern
```

### Step 5 — Display Result Summary

Read the generated file using the Read tool and extract key figures:

```
Listing status lookup complete

Complex      : <complex_name> (ID: <complex_number>)
Fetched at   : YYYY-MM-DD HH:MM
File         : <output_path>
PDF          : <pdf_path> (if --pdf was used)

Sale listings: X | Low X.XB ~ High X.XB | Median X.XB
Lease listings: X | Low X.XB ~ High X.XB | Median X.XB (if lease data available)
New listings : X (past week)
Removed      : X (past week)
```

---

## Error Handling

| Error Message | Cause | Action |
|---------------|-------|--------|
| `Error: No listings found for ...` | Invalid complex number or no listings | Ask user to verify the complex number |
| `HTTP 429` (failed after retries) | Naver bot detection | Ask user to retry after a short wait |
| `Error: httpx is not installed.` | Library missing | Check `uv run --with "httpx[http2]"` |

---

## `/apt` vs `/apt-watch` Comparison

| | `/apt` | `/apt-watch` |
|-|--------|--------------|
| Data | MOLIT official transaction prices | Naver Real Estate asking prices |
| Unit | District-wide region | Individual apartment complex |
| Aggregation | Monthly median transaction amount | Current active listings |
| Forecast | 6-month linear regression | New/removed listing change tracking |
| Official | Official (legally disclosed transactions) | Unofficial (asking prices, ToS caution) |
