# presign — Upload a file to cloud storage and return a Presigned URL

Upload a file to Cloudflare R2 or AWS S3 and generate a signed URL valid for the specified duration.
If a CLI is configured, it is preferred; otherwise falls back to the boto3 Python API.

**Execution Priority**

| Provider | Bucket Creation | Upload | Presign |
|----------|----------------|--------|---------|
| **R2** | aws CLI → wrangler → boto3 | aws CLI → wrangler → boto3 | aws CLI (R2 endpoint) → boto3 |
| **S3** | aws CLI → boto3 | aws CLI → boto3 | aws CLI → boto3 |

> **Cloudflare CLI Limitations**
> - `wrangler`: Only supports upload (`r2 object put`), no presign command → presign handled by boto3
> - `flarectl`: Zone/DNS/WAF-only tool with no R2 Object Storage commands → cannot presign

## Usage

```
/presign <file_path> [hours=24]
```

- `file_path` — Path to the file to upload (required)
- `hours` — URL validity duration in hours (optional, default: 24)

## Examples

```
/presign business/readin-business-analysis.md
/presign career/resume-portfolio/palantir_fdse/Resume-sungshik_palantir-fdse_v1.md 48
/presign ai-ml/some-report.md 6
```

---

## Procedure

### Step 1 — Parse Arguments

Extract the file path and expiration time from `$ARGUMENTS`.

```
file_path = first token of $ARGUMENTS
hours     = second token of $ARGUMENTS (default: 24 if not provided)
```

### Step 2 — Verify File Exists

```bash
test -f "<file_path>" && echo "exists" || echo "NOT FOUND"
```

If the file does not exist, notify the user and abort.

### Step 3 — Run Script

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "presign.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S=".claude/scripts/presign.py"
uv run --no-active python "$_S" "<file_path>" <hours>
```

### Step 4 — Return Result

Extract the URL following `✅ Presigned URL` from the script output and display it to the user in this format:

```
File      : <file_name>
Provider  : <Cloudflare R2 | AWS S3>
Bucket    : <bucket_name>
Valid for : <hours> hours

🔗 Presigned URL:
<URL>
```

### Step 5 — Error Handling

| Error Condition | Response |
|----------------|----------|
| File not found | Ask user to recheck the path |
| Credentials not configured | Display the configuration guide below |
| boto3 not installed | Run `uv add boto3` and retry |
| Bucket creation/upload failed | Ask user to verify token permissions (Bucket Create, Object Write) |

---

## Provider Auto-Detection Order

1. `STORAGE_PROVIDER=r2` or `=s3` explicitly set → use that provider
2. `R2_ACCOUNT_ID` is set → Cloudflare R2
3. `AWS_ACCESS_KEY_ID` is set → AWS S3
4. Nothing set → error + display configuration guide

---

## Environment Variable Setup

### Cloudflare R2

```bash
export STORAGE_PROVIDER="r2"               # optional (auto-detected)
export R2_ACCOUNT_ID="your-account-id"     # Cloudflare Dashboard right sidebar
export R2_ACCESS_KEY_ID="your-key-id"      # R2 API token
export R2_SECRET_ACCESS_KEY="your-secret"
export R2_BUCKET_NAME="presign-shared"     # auto-created if not exists
```

**R2 API Token**: Cloudflare Dashboard → R2 → Manage R2 API Tokens → Create API Token
Permissions: `Object Read & Write` (`Admin Read & Write` required for automatic bucket creation)

### AWS S3

```bash
export STORAGE_PROVIDER="s3"              # optional (auto-detected)
export AWS_ACCESS_KEY_ID="your-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="ap-northeast-2"
export S3_BUCKET_NAME="presign-shared"    # auto-created if not exists
```

### Save to settings.local.json (excluded from git)

```json
{
  "env": {
    "STORAGE_PROVIDER": "r2",
    "R2_ACCOUNT_ID": "your-account-id",
    "R2_ACCESS_KEY_ID": "your-access-key-id",
    "R2_SECRET_ACCESS_KEY": "your-secret-access-key",
    "R2_BUCKET_NAME": "presign-shared"
  }
}
```
