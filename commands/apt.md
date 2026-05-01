Generate a Seoul/Metropolitan area apartment price report: $ARGUMENTS

## Usage

```
/apt <region> [--months N] [--type sale|lease|all] [--forecast N] [--pdf]
```

| Argument | Description | Default |
|----------|-------------|---------|
| `region` | One of Seoul's 25 districts or a metropolitan city/county/district (e.g., Gangnam-gu, Mapo-gu, Bundang-gu) | Required |
| `--months N` | Analysis period in months | 12 |
| `--type` | sale \| lease \| all | all |
| `--forecast N` | Forecast period in months (0 to skip) | 6 |
| `--pdf` | Also convert to PDF | — |

Examples:
```
/apt 강남구
/apt 마포구 --months 24 --type 전세
/apt 분당구 --type 매매 --forecast 3 --pdf
```

---

## Procedure

### Step 1 — Parse Arguments

Extract the following from `$ARGUMENTS`:
- `region`: first token (required)
- `months`: value from `--months N` (default 12)
- `trade_type`: value from `--type` (default `전체`)
- `forecast`: value from `--forecast N` (default 6)
- `pdf_flag`: whether `--pdf` is present (boolean)

### Step 2 — Determine Output Path

Prepend `$BASE_DIR/` if the environment variable is set:

```
output_path = ${BASE_DIR:+$BASE_DIR/}reports/apt-<region>-<YYYYMM>.md
```

Example (no BASE_DIR): `reports/apt-강남구-202604.md`
Example (BASE_DIR=/home/user/research): `/home/user/research/reports/apt-강남구-202604.md`

### Step 3 — Run Script

Execute the following command via Bash:

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "apt_report.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S=".claude/scripts/apt_report.py"
uv run --with PublicDataReader --with pandas --with numpy \
    python "$_S" <region> \
    --months <months> \
    --type <trade_type> \
    --forecast <forecast> \
    --output <output_path>
```

- stderr progress logs (e.g., `Fetching...`, `Aggregation complete`) are normal output
- stderr starting with `Error:` indicates an error — explain the cause to the user and stop
- If the region name was auto-matched, the script logs it to stderr — notify the user

### Step 4 — PDF Conversion (only if --pdf flag is present)

Use the pdf-creator skill to generate the PDF. Dynamically locate the script path:

```bash
PDF_SCRIPT=$(find "$HOME/.claude/plugins/cache" -path "*/pdf-creator/*/md_to_pdf.py" 2>/dev/null | sort -rV | head -1)
if [ -z "$PDF_SCRIPT" ]; then
    echo "⚠️  pdf-creator skill is not installed. Please install pdf-creator from the Claude Marketplace."
    exit 1
fi
uv run --with weasyprint python "$PDF_SCRIPT" <output_path> --theme tech-modern
```

PDF path: replace the extension of `output_path` with `.pdf`

### Step 5 — Display Result Summary

Show the following information to the user:

```
Report generation complete

Region  : <region>
Period  : <start_ym> ~ <end_ym>
File    : <output_path>
PDF     : <pdf_path> (if --pdf was used)

Key figures:
- Latest sale median price : X.XB KRW (YYYY-MM)
- Month-over-month         : ▲/▼ X.X%
- Year-over-year           : ▲/▼ X.X%
- Latest lease median price: X.XB KRW (YYYY-MM) (if lease data available)
- Lease-to-sale ratio      : X.X% (if both datasets available)
```

Read the generated file using the Read tool to extract key figures and display them in the format above.

---

## Supported Regions

### Seoul — 25 Districts
종로구, 중구, 용산구, 성동구, 광진구, 동대문구, 중랑구, 성북구, 강북구,
도봉구, 노원구, 은평구, 서대문구, 마포구, 양천구, 강서구, 구로구, 금천구,
영등포구, 동작구, 관악구, 서초구, 강남구, 송파구, 강동구

### Gyeonggi — Major Cities/Districts
분당구, 수지구, 일산동구, 일산서구, 부천시, 광명시, 하남시, 화성시,
남양주시, 고양시덕양구, 안양시동안구, 성남시수정구, 성남시중원구,
수원시영통구, 수원시장안구 … (see full list in the script)

### Incheon — Major Districts
연수구, 인천남동구, 인천부평구, 인천서구, 인천미추홀구

---

## Error Handling

| Error Message | Cause | Action |
|---------------|-------|--------|
| `Error: DATA_GO_KR_API_KEY environment variable is not set.` | API key not set | Check settings.local.json |
| `Error: Region '...' not found.` | Typo in region name | Show supported regions list |
| `Error: No data found for region ...` | No transactions in the given period | Suggest increasing `--months` value |
| `Error: PublicDataReader is not installed.` | Library missing | Check the `uv run --with` option |
