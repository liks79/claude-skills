# share — Convert to PDF, upload to R2, and return a shareable URL

Converts the most recent research `.md` file to PDF and uploads it to Cloudflare R2,
returning a presigned URL. Optionally also returns a Quartz URL if `QUARTZ_BASE_URL`
is configured.

## Usage

```
/share                          → auto-selects the most recently modified .md in notes/ or reports/
/share <md_path>                → uses the specified file (relative to repo root)
/share <hours>                  → number-only: sets URL validity duration (default: 24)
/share <md_path> <hours>
```

Examples:

```
/share
/share 48
/share notes/finance/some-report-2026.md
/share reports/finance/investment-report-2026-05-24.md 72
```

---

## Procedure

### Step 1 — Parse Arguments

Parse `$ARGUMENTS`:

- No tokens → `md_path=auto`, `hours=24`
- First token is a pure integer → `md_path=auto`, `hours=<integer>`
- First token is a path → `md_path=<path>`, second token (if integer) → `hours=<integer>` (default: 24)

### Step 2 — Resolve Target File

**When `md_path=auto`**, find the most recently modified tracked `.md` file under
`notes/` or `reports/`:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
git -C "$REPO_ROOT" ls-files \
  | grep -E '^(notes|reports)/.*\.md$' \
  | xargs -I{} stat --format="%Y {}" "$REPO_ROOT/{}" 2>/dev/null \
  | sort -rn \
  | awk 'NR==1 {print $2}'
```

Set the result as `md_path`. If no file is found, notify the user and abort.

**When `md_path` is specified**, verify the file exists:
```bash
test -f "$REPO_ROOT/<md_path>"
```
If not found, ask the user to re-check the path and abort.

### Step 3 — Compute Paths

```
repo_root   = git rev-parse --show-toplevel
abs_md_path = repo_root + "/" + md_path      # absolute path
pdf_path    = abs_md_path with .md → .pdf
slug        = md_path with .md extension removed
quartz_url  = $QUARTZ_BASE_URL + "/" + slug  (only if QUARTZ_BASE_URL is set)
```

### Step 4 — Convert to PDF

Locate the `pdf-creator` plugin script and run it:

```bash
PDF_SCRIPT=$(find "$HOME/.claude/plugins/cache" -path "*/pdf-creator/*/md_to_pdf.py" 2>/dev/null | sort -rV | head -1)
if [ -z "$PDF_SCRIPT" ]; then
    echo "pdf-creator skill not installed. Install it from the Claude Marketplace."
    exit 1
fi
uv run --with weasyprint python "$PDF_SCRIPT" "<abs_md_path>"
```

- Default theme is used (no extra parameters).
- The generated PDF is at `pdf_path`.
- On failure, show stderr to the user and abort.

### Step 5 — Upload and Generate Presigned URL

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "presign.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/presign.py"
uv run --with boto3 python "$_S" "<pdf_path>" <hours>
```

Extract the URL that follows `✅ Presigned URL` in the script output.

### Step 6 — Display Results

```
## Share Complete

File      : <md_path>
PDF       : <pdf_path>
Valid for : <hours> hours

🔗 Presigned URL (PDF):
<presigned_url>

🌐 Quartz URL:          (omit this block if QUARTZ_BASE_URL is not set)
<quartz_url>
```

### Step 7 — Error Handling

| Error | Response |
|-------|----------|
| No `.md` files found in `notes/` or `reports/` | Notify user and abort |
| Specified file not found | Ask user to re-check the path |
| `pdf-creator` not installed | Guide user to install from Claude Marketplace |
| PDF conversion failed | Show stderr and abort |
| R2 credentials not configured | Point user to the `/presign` command configuration guide |
| Upload failed | Ask user to verify token permissions (Object Write) |
