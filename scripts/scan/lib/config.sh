#!/usr/bin/env bash
# config.sh — Shared configuration defaults for /scan scripts.
# All values can be overridden via environment variables.
# Never put personal paths, secrets, or API keys in this file.

# ── Repository root ──────────────────────────────────────────────────────────
# Auto-detected from git, or override with BASE_DIR env var.
_SCAN_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${BASE_DIR:-$(git -C "${_SCAN_LIB_DIR}" rev-parse --show-toplevel 2>/dev/null || echo "${PWD}")}"

# ── Output ───────────────────────────────────────────────────────────────────
SCAN_OUTPUT_DIR="${SCAN_OUTPUT_DIR:-00_INBOX}"
TARGET_FILENAME="${TARGET_FILENAME:-recent_index.md}"

# ── Scan scope ───────────────────────────────────────────────────────────────
# Comma-separated list of directories relative to BASE_DIR to scan.
# Default "." scans the entire repository (built-in excludes still apply).
SCAN_INCLUDE_DIRS="${SCAN_INCLUDE_DIRS:-.}"

# ── File format filters ───────────────────────────────────────────────────────
# Comma-separated file extensions to INCLUDE (no leading dot).
# Default "md" targets only Markdown files.
# Set to empty string "" to include all extensions found in scan dirs.
# Examples: "md", "md,mdx", "md,txt"
SCAN_FILE_INCLUDE="${SCAN_FILE_INCLUDE:-md}"

# Comma-separated file extensions to EXCLUDE (no leading dot).
# Applied after SCAN_FILE_INCLUDE; empty by default (no extra exclusions).
# Examples: "pdf,png", "pdf"
SCAN_FILE_EXCLUDE="${SCAN_FILE_EXCLUDE:-}"

# Additional user-defined path exclude patterns (comma-separated Python regex).
# Built-in excludes (.git/, TEMPLATES/, WIKI/, .claude/, etc.) are always
# applied in update_cache.py regardless of this setting.
SCAN_EXCLUDE_PATTERNS="${SCAN_EXCLUDE_PATTERNS:-}"

# ── Cache ────────────────────────────────────────────────────────────────────
SCAN_CACHE_DIR="${SCAN_CACHE_DIR:-${BASE_DIR}/.claude/scripts/scan/.cache}"
SCAN_CACHE_FILE="${SCAN_CACHE_DIR}/meta_cache.json"

# ── Python interpreter ────────────────────────────────────────────────────────
# Prefer uv-managed python, fall back to system python3 / python.
if command -v uv &>/dev/null && uv python find &>/dev/null 2>&1; then
  PYTHON="${PYTHON:-uv run python}"
elif command -v python3 &>/dev/null; then
  PYTHON="${PYTHON:-python3}"
else
  PYTHON="${PYTHON:-python}"
fi
