#!/usr/bin/env python3
"""
presign.py — Upload a file to Cloudflare R2 or AWS S3 and return a presigned URL.

Usage:
    python presign.py <file_path> [hours=24]

Execution method priority:
  R2:  aws CLI (R2 endpoint)  →  wrangler (upload) + boto3 (presign)  →  boto3
  S3:  aws CLI                →  boto3

  * wrangler has no presign command; when selected for upload, boto3 handles presign.
  * aws CLI for R2 requires R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY in env.
  * aws CLI for S3 uses ~/.aws/credentials or AWS_* env vars (validated via sts).

--- Cloudflare R2 environment variables ---
    R2_ACCOUNT_ID        Cloudflare account ID             (required)
    R2_ACCESS_KEY_ID     R2 API token access key ID        (required)
    R2_SECRET_ACCESS_KEY R2 API token secret access key    (required)
    R2_BUCKET_NAME       Target bucket (default: presign-shared)

--- AWS S3 environment variables ---
    AWS_ACCESS_KEY_ID     AWS access key ID                (required for boto3/env-auth)
    AWS_SECRET_ACCESS_KEY AWS secret access key            (required for boto3/env-auth)
    AWS_DEFAULT_REGION    AWS region (default: ap-northeast-2)
    S3_BUCKET_NAME        Target bucket (default: presign-shared)

Optional:
    STORAGE_PROVIDER     Force provider: "r2" or "s3"
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

# boto3 is a soft dependency — only required when CLI path is unavailable
try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError

    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Method(Enum):
    AWSCLI = "awscli"
    WRANGLER = "wrangler"   # upload only; presign falls back to boto3
    BOTO3 = "boto3"


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def sanitize_key(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9.\-_/]", "_", name)


def content_type(path: Path) -> str:
    mapping = {
        ".md":   "text/markdown; charset=utf-8",
        ".txt":  "text/plain; charset=utf-8",
        ".pdf":  "application/pdf",
        ".png":  "image/png",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".json": "application/json",
        ".html": "text/html; charset=utf-8",
        ".csv":  "text/csv; charset=utf-8",
        ".zip":  "application/zip",
    }
    return mapping.get(path.suffix.lower(), "application/octet-stream")


def _sh(args: list[str], env: dict | None = None, check: bool = False,
         capture: bool = True, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        env=env or os.environ,
        capture_output=capture,
        text=True,
        timeout=timeout,
        check=check,
    )


# ---------------------------------------------------------------------------
# Provider detection
# ---------------------------------------------------------------------------


def detect_provider() -> str:
    explicit = os.environ.get("STORAGE_PROVIDER", "").lower()
    if explicit in ("r2", "s3"):
        return explicit
    if os.environ.get("R2_ACCOUNT_ID"):
        return "r2"
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        return "s3"
    return ""


# ---------------------------------------------------------------------------
# CLI availability / auth checks
# ---------------------------------------------------------------------------


def _has_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _r2_env_creds_set() -> bool:
    return all(os.environ.get(k) for k in
               ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"))


def _awscli_s3_configured() -> bool:
    """Verify aws CLI has usable S3 credentials (profile or env)."""
    if not _has_cmd("aws"):
        return False
    try:
        return _sh(["aws", "sts", "get-caller-identity"], timeout=10).returncode == 0
    except Exception:
        return False


def _wrangler_authenticated() -> bool:
    """Verify wrangler is logged in."""
    if not _has_cmd("wrangler"):
        return False
    try:
        return _sh(["wrangler", "whoami"], timeout=15).returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Method selection
# ---------------------------------------------------------------------------


def select_method(provider: str) -> Method:
    """
    R2:  aws CLI (has env creds)  →  wrangler (authed)  →  boto3
    S3:  aws CLI (sts ok)         →  boto3
    """
    if provider == "r2":
        if _has_cmd("aws") and _r2_env_creds_set():
            return Method.AWSCLI
        if _wrangler_authenticated():
            return Method.WRANGLER
        return Method.BOTO3
    else:
        if _awscli_s3_configured():
            return Method.AWSCLI
        return Method.BOTO3


# ---------------------------------------------------------------------------
# R2 helpers  (aws CLI path)
# ---------------------------------------------------------------------------


def _r2_cli_env() -> dict:
    """Map R2_* creds → AWS_* env vars so aws CLI can use them."""
    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"]     = os.environ["R2_ACCESS_KEY_ID"]
    env["AWS_SECRET_ACCESS_KEY"] = os.environ["R2_SECRET_ACCESS_KEY"]
    env["AWS_DEFAULT_REGION"]    = "auto"
    return env


def _r2_endpoint() -> str:
    return f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"


def _awscli_ensure_bucket_r2(bucket: str) -> None:
    env, ep = _r2_cli_env(), _r2_endpoint()
    if _sh(["aws", "s3", "ls", f"s3://{bucket}", "--endpoint-url", ep], env=env).returncode != 0:
        print(f"[presign] Creating bucket '{bucket}'  via aws CLI (R2)...")
        _sh(["aws", "s3", "mb", f"s3://{bucket}", "--endpoint-url", ep], env=env, check=True)


def _awscli_upload_r2(file_path: Path, bucket: str, key: str) -> None:
    _sh([
        "aws", "s3", "cp", str(file_path), f"s3://{bucket}/{key}",
        "--endpoint-url", _r2_endpoint(),
        "--content-type", content_type(file_path),
    ], env=_r2_cli_env(), check=True, capture=False)


def _awscli_presign_r2(bucket: str, key: str, expires_in: int) -> str:
    result = _sh([
        "aws", "s3", "presign", f"s3://{bucket}/{key}",
        "--expires-in", str(expires_in),
        "--endpoint-url", _r2_endpoint(),
    ], env=_r2_cli_env(), check=True)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# S3 helpers  (aws CLI path)
# ---------------------------------------------------------------------------


def _awscli_ensure_bucket_s3(bucket: str, region: str) -> None:
    if _sh(["aws", "s3", "ls", f"s3://{bucket}"]).returncode != 0:
        print(f"[presign] Creating bucket '{bucket}'  via aws CLI (S3)...")
        args = ["aws", "s3", "mb", f"s3://{bucket}"]
        if region and region != "us-east-1":
            args += ["--region", region]
        _sh(args, check=True)


def _awscli_upload_s3(file_path: Path, bucket: str, key: str) -> None:
    _sh([
        "aws", "s3", "cp", str(file_path), f"s3://{bucket}/{key}",
        "--content-type", content_type(file_path),
    ], check=True, capture=False)


def _awscli_presign_s3(bucket: str, key: str, expires_in: int) -> str:
    result = _sh([
        "aws", "s3", "presign", f"s3://{bucket}/{key}",
        "--expires-in", str(expires_in),
    ], check=True)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Wrangler helpers  (R2 upload only — no presign support in wrangler CLI)
# ---------------------------------------------------------------------------


def _wrangler_ensure_bucket(bucket: str) -> None:
    result = _sh(["wrangler", "r2", "bucket", "list"])
    if bucket not in result.stdout:
        print(f"[presign] Creating bucket '{bucket}'  via wrangler...")
        _sh(["wrangler", "r2", "bucket", "create", bucket], check=True, capture=False)


def _wrangler_upload(file_path: Path, bucket: str, key: str) -> None:
    _sh([
        "wrangler", "r2", "object", "put",
        f"{bucket}/{key}",
        "--file", str(file_path),
        "--content-type", content_type(file_path),
    ], check=True, capture=False)


# ---------------------------------------------------------------------------
# boto3 helpers  (fallback / presign-only for wrangler path)
# ---------------------------------------------------------------------------


def _require_boto3() -> None:
    if not HAS_BOTO3:
        print("ERROR: boto3 is required but not installed.")
        print("Run:  uv add boto3")
        sys.exit(1)


def _boto3_r2_client():
    _require_boto3()
    acct   = os.environ.get("R2_ACCOUNT_ID")
    key_id = os.environ.get("R2_ACCESS_KEY_ID")
    secret = os.environ.get("R2_SECRET_ACCESS_KEY")
    missing = [k for k, v in {
        "R2_ACCOUNT_ID": acct, "R2_ACCESS_KEY_ID": key_id,
        "R2_SECRET_ACCESS_KEY": secret,
    }.items() if not v]
    if missing:
        print(f"ERROR: Missing R2 credentials: {', '.join(missing)}")
        print("  export R2_ACCOUNT_ID=...  R2_ACCESS_KEY_ID=...  R2_SECRET_ACCESS_KEY=...")
        sys.exit(1)
    return boto3.client(
        "s3",
        endpoint_url=f"https://{acct}.r2.cloudflarestorage.com",
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _boto3_s3_client():
    _require_boto3()
    key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
    missing = [k for k, v in {
        "AWS_ACCESS_KEY_ID": key_id, "AWS_SECRET_ACCESS_KEY": secret,
    }.items() if not v]
    if missing:
        print(f"ERROR: Missing S3 credentials: {', '.join(missing)}")
        print("  export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...")
        sys.exit(1)
    return boto3.client(
        "s3",
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2"),
        config=Config(signature_version="s3v4"),
    )


def _boto3_ensure_bucket(client, bucket: str, region: str = "") -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            print(f"[presign] Creating bucket '{bucket}'  via boto3...")
            kwargs: dict = {"Bucket": bucket}
            if region and region != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
            client.create_bucket(**kwargs)
        else:
            raise


def _boto3_presign(client, bucket: str, key: str, expires_in: int) -> str:
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


# ---------------------------------------------------------------------------
# No-provider error
# ---------------------------------------------------------------------------


def _die_no_provider() -> None:
    print("ERROR: No storage provider detected.\n")
    print("Option A — Cloudflare R2:")
    print("  export R2_ACCOUNT_ID=...  R2_ACCESS_KEY_ID=...  R2_SECRET_ACCESS_KEY=...\n")
    print("Option B — AWS S3:")
    print("  export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...\n")
    print("Or force:  export STORAGE_PROVIDER=r2  (or s3)")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Core orchestration
# ---------------------------------------------------------------------------


def run(file_path: Path, hours: int) -> str:
    provider = detect_provider()
    if not provider:
        _die_no_provider()

    expires_in  = hours * 3600
    timestamp   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    object_key  = sanitize_key(f"shared/{timestamp}/{file_path.name}")
    method      = select_method(provider)

    print(f"[presign] Provider : {'Cloudflare R2' if provider == 'r2' else 'AWS S3'}  [{method.value}]")
    print(f"[presign] Uploading: {file_path.name}  →  {object_key}")

    url: str

    # ── Cloudflare R2 ─────────────────────────────────────────────────────
    if provider == "r2":
        bucket = os.environ.get("R2_BUCKET_NAME", "presign-shared")

        if method == Method.AWSCLI:
            _awscli_ensure_bucket_r2(bucket)
            _awscli_upload_r2(file_path, bucket, object_key)
            url = _awscli_presign_r2(bucket, object_key, expires_in)

        elif method == Method.WRANGLER:
            # wrangler: bucket + upload  |  boto3: presign (wrangler has no presign)
            _wrangler_ensure_bucket(bucket)
            _wrangler_upload(file_path, bucket, object_key)
            print("[presign] (wrangler has no presign — falling back to boto3 for URL signing)")
            client = _boto3_r2_client()
            url = _boto3_presign(client, bucket, object_key, expires_in)

        else:  # boto3
            client = _boto3_r2_client()
            _boto3_ensure_bucket(client, bucket)
            client.upload_file(str(file_path), bucket, object_key,
                               ExtraArgs={"ContentType": content_type(file_path)})
            url = _boto3_presign(client, bucket, object_key, expires_in)

    # ── AWS S3 ────────────────────────────────────────────────────────────
    else:
        bucket = os.environ.get("S3_BUCKET_NAME", "presign-shared")
        region = os.environ.get("AWS_DEFAULT_REGION", "ap-northeast-2")

        if method == Method.AWSCLI:
            _awscli_ensure_bucket_s3(bucket, region)
            _awscli_upload_s3(file_path, bucket, object_key)
            url = _awscli_presign_s3(bucket, object_key, expires_in)

        else:  # boto3
            client = _boto3_s3_client()
            _boto3_ensure_bucket(client, bucket, region)
            client.upload_file(str(file_path), bucket, object_key,
                               ExtraArgs={"ContentType": content_type(file_path)})
            url = _boto3_presign(client, bucket, object_key, expires_in)

    print("[presign] Upload complete.")
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    print(f"\n✅ Presigned URL  (expires in {hours}h · {expires_at.strftime('%Y-%m-%d %H:%M UTC')})")
    print(url)

    # Copy URL to clipboard (no newline)
    # Priority: wl-copy (Wayland) → xclip → xsel → OSC 52 (works over SSH / Alacritty)
    copied = False
    for cmd in (
        ["wl-copy", "--trim-newline"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=url, text=True, check=True,
                               env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
                               capture_output=True)
                print("[presign] URL copied to clipboard ✓")
                copied = True
                break
            except Exception:
                pass

    if not copied:
        # OSC 52: terminal-level clipboard copy — works in Alacritty, WezTerm, iTerm2, tmux, SSH
        import base64
        osc52 = f"\033]52;c;{base64.b64encode(url.encode()).decode()}\a"
        sys.stdout.write(osc52)
        sys.stdout.flush()
        print("[presign] URL copied to clipboard via OSC 52 ✓")

    return url


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    file_path = Path(sys.argv[1]).expanduser().resolve()
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    hours = 24
    if len(sys.argv) >= 3:
        try:
            hours = int(sys.argv[2])
            if hours <= 0:
                raise ValueError
        except ValueError:
            print(f"ERROR: hours must be a positive integer, got: {sys.argv[2]}")
            sys.exit(1)

    run(file_path, hours)


if __name__ == "__main__":
    main()
