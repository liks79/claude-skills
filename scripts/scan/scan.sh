#!/usr/bin/env bash
# scan.sh — Main entry point for the /scan command.
#
# Usage:
#   bash scan.sh [options]
#
# Options:
#   -o, --output-dir DIR        Output directory      (env: SCAN_OUTPUT_DIR, default: 00_INBOX)
#   -f, --filename NAME         Output filename       (env: TARGET_FILENAME,  default: recent_index.md)
#       --dirs DIRS             Comma-separated scan dirs (env: SCAN_INCLUDE_DIRS, default: .)
#       --file-include EXTS     Extensions to include (env: SCAN_FILE_INCLUDE,  default: md)
#       --file-exclude EXTS     Extensions to exclude (env: SCAN_FILE_EXCLUDE,  default: "")
#       --force                 Ignore cache, full rescan
#
# EXTS format: comma-separated, no leading dot — e.g. "md,mdx" or "pdf,png"
# All options can also be set via environment variables (see lib/config.sh).
set -euo pipefail

# ── Resolve script directory (plugin cache-aware) ─────────────────────────────
# When installed as a plugin, this script lives in the plugin cache.
# BASH_SOURCE[0] always points to the actual script location, so dirname is reliable.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Load shared config (sets defaults) ───────────────────────────────────────
# shellcheck source=lib/config.sh
source "${SCRIPT_DIR}/lib/config.sh"

# ── Parse arguments (override config) ────────────────────────────────────────
FORCE_FLAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output-dir)    SCAN_OUTPUT_DIR="$2";    shift 2 ;;
    -f|--filename)      TARGET_FILENAME="$2";     shift 2 ;;
    --dirs)             SCAN_INCLUDE_DIRS="$2";   shift 2 ;;
    --file-include)     SCAN_FILE_INCLUDE="$2";   shift 2 ;;
    --file-exclude)     SCAN_FILE_EXCLUDE="$2";   shift 2 ;;
    --force)            FORCE_FLAG="--force";     shift   ;;
    -h|--help)
      grep '^#' "$0" | head -25 | sed 's/^# \?//'
      exit 0
      ;;
    *)
      echo "[warn] Unknown argument: $1" >&2
      shift
      ;;
  esac
done

# ── Resolve output path ───────────────────────────────────────────────────────
# Support absolute paths in SCAN_OUTPUT_DIR; otherwise relative to BASE_DIR.
if [[ "${SCAN_OUTPUT_DIR}" = /* ]]; then
  OUTPUT_DIR="${SCAN_OUTPUT_DIR}"
else
  OUTPUT_DIR="${BASE_DIR}/${SCAN_OUTPUT_DIR}"
fi
OUTPUT_FILE="${OUTPUT_DIR}/${TARGET_FILENAME}"

mkdir -p "${OUTPUT_DIR}" "${SCAN_CACHE_DIR}"

# ── Print run summary ─────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════╗"
echo "║  /scan — Research Index Builder              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
_file_filter_display="${SCAN_FILE_INCLUDE:-*}"
[[ -n "${SCAN_FILE_EXCLUDE:-}" ]] && _file_filter_display+=" (exclude: ${SCAN_FILE_EXCLUDE})"

echo "  Repo root    : ${BASE_DIR}"
echo "  Scan dirs    : ${SCAN_INCLUDE_DIRS}"
echo "  File include : ${SCAN_FILE_INCLUDE:-<all>}"
[[ -n "${SCAN_FILE_EXCLUDE:-}" ]] && echo "  File exclude : ${SCAN_FILE_EXCLUDE}"
echo "  Output       : ${OUTPUT_FILE}"
echo "  Cache        : ${SCAN_CACHE_FILE}"
[[ -n "${FORCE_FLAG}" ]] && echo "  Mode         : FORCE (full rescan)"
echo ""

# ── Phase 1: Update metadata cache ───────────────────────────────────────────
echo "▶ Phase 1 — Updating metadata cache…"
${PYTHON} "${SCRIPT_DIR}/lib/update_cache.py" \
  --repo-root    "${BASE_DIR}" \
  --dirs         "${SCAN_INCLUDE_DIRS}" \
  --cache        "${SCAN_CACHE_FILE}" \
  --exclude      "${SCAN_EXCLUDE_PATTERNS}" \
  --file-include "${SCAN_FILE_INCLUDE:-}" \
  --file-exclude "${SCAN_FILE_EXCLUDE:-}" \
  ${FORCE_FLAG}

# ── Phase 2: Build index ──────────────────────────────────────────────────────
echo ""
echo "▶ Phase 2 — Generating index…"
${PYTHON} "${SCRIPT_DIR}/lib/build_index.py" \
  --cache     "${SCAN_CACHE_FILE}" \
  --output    "${OUTPUT_FILE}" \
  --repo-root "${BASE_DIR}"

echo ""
echo "✅ Done → ${OUTPUT_FILE}"
