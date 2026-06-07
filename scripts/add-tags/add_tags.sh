#!/usr/bin/env bash
# add_tags.sh — Phases 1 and 3 for the /add-tags command.
#
# Phase 1: Scan vault, update tag cache.
# Phase 3: Read cache, write Tag_Dictionary.md.
#
# Phase 2 (tag assignment) is handled directly by Claude Code via
# Read/Edit tools — no API key required.
#
# Usage:
#   bash add_tags.sh [options]
#
# Scan modes (fastest → slowest):
#   --paths "f1.md,f2.md"  Surgical: rescan only listed files (after tagging)
#   --delta                 Fast: find files newer than cache via `find -newer`
#   (default)               Incremental: check all mtimes, skip unchanged
#   --force                 Full: ignore cache, re-read every file
#
# Options:
#       --phase N            Run only phase 1 or 3 (default: both)
#       --paths "f1,f2"      Surgical rescan of specific files (comma-separated)
#       --delta              Fast delta scan (files newer than cache)
#       --force              Full rescan, ignore cache
#       --output-dir DIR     Override output directory (env: ADD_TAGS_OUTPUT_DIR)
#       --filename NAME      Override output filename  (env: ADD_TAGS_FILENAME)
#       --include-dirs DIRS  Comma-separated dirs to scan (default: .)
#
# Environment variables:
#   ADD_TAGS_OUTPUT_DIR   Output directory (default: 00_INBOX)
#   ADD_TAGS_FILENAME     Output filename  (default: Tag_Dictionary.md)
#   ADD_TAGS_CACHE_DIR    Cache directory  (default: <script_dir>/.cache)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCANNER="${SCRIPT_DIR}/lib/scanner.py"
PYTHON_BUILDER="${SCRIPT_DIR}/lib/builder.py"

# ── Defaults ────────────────────────────────────────────────────────────────
ADD_TAGS_OUTPUT_DIR="${ADD_TAGS_OUTPUT_DIR:-00_INBOX}"
ADD_TAGS_FILENAME="${ADD_TAGS_FILENAME:-Tag_Dictionary.md}"
ADD_TAGS_CACHE_DIR="${ADD_TAGS_CACHE_DIR:-${SCRIPT_DIR}/.cache}"
INCLUDE_DIRS="."

FORCE_FLAG=""
DELTA_FLAG=""
PATHS_FLAG=""
RUN_PHASE=""   # empty = run all phases

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --phase)        RUN_PHASE="$2";             shift 2 ;;
    --force)        FORCE_FLAG="--force";        shift ;;
    --delta)        DELTA_FLAG="--delta";        shift ;;
    --paths)        PATHS_FLAG="--paths $2";     shift 2 ;;
    --output-dir)   ADD_TAGS_OUTPUT_DIR="$2";   shift 2 ;;
    --filename)     ADD_TAGS_FILENAME="$2";      shift 2 ;;
    --include-dirs) INCLUDE_DIRS="$2";           shift 2 ;;
    --no-assign)    shift ;;   # legacy compat: ignored
    -h|--help)
      grep "^#" "$0" | head -40 | sed 's/^# \?//'
      exit 0
      ;;
    *) shift ;;
  esac
done

# ── Resolve repo root ────────────────────────────────────────────────────────
BASE_DIR="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null || pwd)"
mkdir -p "${ADD_TAGS_CACHE_DIR}"

# ── Phase 1: Scan vault ──────────────────────────────────────────────────────
if [[ -z "${RUN_PHASE}" || "${RUN_PHASE}" == "1" ]]; then
  echo "▶ Phase 1 — Updating tag cache…"
  uv run python "${PYTHON_SCANNER}" \
    ${FORCE_FLAG} \
    ${DELTA_FLAG} \
    ${PATHS_FLAG} \
    --cache-dir "${ADD_TAGS_CACHE_DIR}" \
    --repo-root "${BASE_DIR}" \
    --include-dirs "${INCLUDE_DIRS}"
fi

# ── Phase 3: Build Tag Dictionary ───────────────────────────────────────────
if [[ -z "${RUN_PHASE}" || "${RUN_PHASE}" == "3" ]]; then
  echo "▶ Phase 3 — Building Tag Dictionary…"
  uv run python "${PYTHON_BUILDER}" \
    --output-dir "${ADD_TAGS_OUTPUT_DIR}" \
    --filename "${ADD_TAGS_FILENAME}" \
    --cache-dir "${ADD_TAGS_CACHE_DIR}" \
    --repo-root "${BASE_DIR}"
fi
