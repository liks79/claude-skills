# /findjob — Job Opening Finder

Scans target company career sites for open positions matching your preferences,
tracks changes over time via SQLite, and generates a ranked Markdown report.

No personal identifiable information in this file — safe to commit to public repos.

---

## FindJob Configuration

Edit the `findjob-config` YAML block below to update your preferences.
This block is machine-parsed by the `findjob/config.py` script.

```yaml
# findjob-config  ← DO NOT remove or rename this tag

wanted_locations:
  - "Seoul"
  - "South Korea"
  - "Seoul, South Korea"
  - "Korea"

wanted_positions:
  - "Solutions Architect"
  - "Senior Engineer"
  - "Software Development Manager"
  - "Director"
  - "DevOps Engineer"
  - "Platform Engineer"
  - "Engineering Manager"
  - "Technical Project Manager"
  - "Forward Deployed Engineer"
  - "FDE"
  - "Staff Engineer"
  - "Principal Engineer"

# Minimum relevance score to include a job in the report.
# 0.0 = include everything | 0.4 = filter weak single-keyword overlaps (recommended)
# 0.7 = strict matching only | 1.0 = exact phrase match only
min_match_score: 0.40

companies:
  - name: "Amazon Web Services"
    url: "https://www.amazon.jobs/en/search?base_query=&loc_query=Seoul%2C+South+Korea%2C+South+Korea&city=Seoul&county=South+Korea&country=KOR&latitude=37.55886&longitude=126.99989&radius=24km"
    parser: "aws"

  - name: "Google"
    url: "https://www.google.com/about/careers/applications/jobs/results/?q=&location=Seoul%2C+South+Korea&hl=en"
    parser: "google"

  - name: "Microsoft"
    url: "https://apply.careers.microsoft.com/careers?query=&location=Korea%2C%20Seoul%2C%20Seoul&start=0"
    parser: "microsoft"

  - name: "Redis"
    url: "https://redis.io/company/careers/current-job-openings/?location=South+Korea"
    parser: "redis_io"

  - name: "Datadog"
    url: "https://careers.datadoghq.com/all-jobs/?s=seoul"
    parser: "datadog"
    greenhouse_board: "datadog"

  - name: "Databricks"
    url: "https://www.databricks.com/company/careers/open-positions?department=all&location=Seoul,%20South%20Korea"
    parser: "databricks"
    greenhouse_board: "databricks"

  - name: "Palantir"
    url: "https://www.palantir.com/careers/open-positions/?location=Asia+%26+Pacific%7C%7CSeoul%2C+South+Korea"
    parser: "palantir"
    smartrecruiters_company: "palantir"

  - name: "Cloudflare"
    url: "https://www.cloudflare.com/careers/jobs/"
    parser: "cloudflare"
    greenhouse_board: "cloudflare"

  - name: "Anthropic"
    url: "https://www.anthropic.com/careers/jobs?office=4043781008"
    parser: "anthropic"
    greenhouse_board: "anthropic"

  - name: "OpenAI"
    url: "https://openai.com/careers/search/?l=983d6a39-c75b-4849-9330-857452cae20a"
    parser: "openai"
    ashby_company: "openai"

  - name: "Coupang"
    url: "https://www.coupang.jobs/kr/jobs/?search=&location=Seoul%2C+South+Korea&pagesize=20#results"
    parser: "coupang"
    greenhouse_board: "coupang"
```

---

## Procedure

### Step 1 — Parse arguments and resolve paths

Parse `$ARGUMENTS` for optional overrides:
- `--output-dir <path>` → override output directory
- `--db-path <path>` → override SQLite DB path

Path resolution priority (highest to lowest):
1. CLI argument (`--output-dir` / `--db-path`)
2. Environment variable: `FINDJOB_OUTPUT_DIR` / `FINDJOB_DB_PATH`
3. `BASE_DIR` env var prefix + `career/job-search/findjob/`
4. Default: `career/job-search/findjob/`

### Step 2 — Resolve script path and run

```bash
# Script resolution
_S=$(find "$HOME/.claude/plugins/cache" -name "findjob_run.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/findjob_run.py"

uv run --with requests --with pyyaml --with beautifulsoup4 python "$_S" \
  ${OUTPUT_DIR:+--output-dir "$OUTPUT_DIR"} \
  ${DB_PATH:+--db-path "$DB_PATH"}
```

The script will:
1. Load the YAML config block from this command file
2. Run each company parser (Greenhouse / Ashby / SmartRecruiters / custom)
3. Score jobs by keyword overlap with `wanted_positions`
4. Upsert results into SQLite (tracks first_seen / last_seen / status)
5. Mark jobs absent from current scan as `removed`
6. Write a Markdown report and print its path to stdout

Capture stdout (report file path) and show stderr progress to the user.

### Step 3 — Present the report

Read the generated report file (printed to stdout by the script) and display it.

**Always highlight:**
- 🏆 Top 3 recommended companies
- 🆕 Count of new positions since last scan
- 🗑️ Count of positions removed since last scan
- 📊 Total active positions across all companies

If any companies failed to fetch, note them and suggest checking the careers page manually.

### Notes on parser coverage

| Company | ATS System | Notes |
|---------|-----------|-------|
| Amazon Web Services | Custom JSON API | ✅ Post-filters by KOR location |
| Google | HTML scraping | ⚠️ SPA — may return 0 |
| Microsoft | Eightfold AI + fallback | ⚠️ SPA — may return 0 |
| Redis | Greenhouse → HTML fallback | ✅ |
| Datadog | Greenhouse | ✅ |
| Databricks | Greenhouse | ✅ |
| Palantir | SmartRecruiters | ✅ |
| Cloudflare | Greenhouse | ✅ |
| Anthropic | Greenhouse | ✅ |
| OpenAI | Ashby HQ | ✅ |
| Coupang | Greenhouse | ✅ |
