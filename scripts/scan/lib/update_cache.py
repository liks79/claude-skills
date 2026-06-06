#!/usr/bin/env python3
"""
update_cache.py — Incrementally update the metadata cache.

On first run: full scan of all markdown files in the configured directories.
On subsequent runs: only re-parses files whose mtime has changed, making
repeated /scan calls fast even on large vaults.

Cache file format (JSON):
{
  "version": "1.1",
  "last_scan": "2026-06-05T10:00:00",
  "files": {
    "20_AREAS/ai-ml/foo.md": {
      "path": "20_AREAS/ai-ml/foo.md",
      "title": "...",
      "created": "2026-06-02",
      "category": "ai-ml",
      "tags": ["pytorch", "mlflow"],
      "classification": "TECHNOLOGY ANALYSIS",
      "type": "research",
      "mtime": "2026-06-02T22:35:00"
    },
    ...
  }
}

Usage:
  python3 update_cache.py --repo-root ROOT --dirs DIRS --cache FILE \\
                          [--exclude PATTERNS] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Allow import when run directly or as module
sys.path.insert(0, str(Path(__file__).parent))
from extract_meta import extract_meta

CACHE_VERSION = "1.2"

# Always-excluded path patterns (Python regex applied to repo-relative paths).
# These protect internal/generated directories regardless of user config.
_BUILTIN_EXCLUDES: list[str] = [
    r"(^|/)\.git/",
    r"(^|/)\.obsidian/",
    r"(^|/)\.claude/",          # slash-command definitions and scripts
    r"(^|/)TEMPLATES/",
    r"(^|/)WIKI/",
    r"(^|/)Clippings/",
    r"(^|/)Excalidraw/",
    r"(^|/)\.smart-env/",
    r"(^|/)\.smtcmp_json_db/",
    r"(^|/)node_modules/",
    r"(^|/)40_ARCHIVES/",
]


# ── Cache I/O ─────────────────────────────────────────────────────────────────

def load_cache(cache_file: str) -> dict:
    """Load existing cache or return a fresh empty cache dict."""
    if os.path.exists(cache_file):
        try:
            with open(cache_file, encoding="utf-8") as fh:
                data = json.load(fh)
            if data.get("version") == CACHE_VERSION and isinstance(data.get("files"), dict):
                return data
        except (json.JSONDecodeError, OSError, KeyError):
            print(f"  [warn] cache corrupted or version mismatch — starting fresh", file=sys.stderr)
    return {"version": CACHE_VERSION, "last_scan": None, "files": {}}


def save_cache(cache: dict, cache_file: str) -> None:
    """Atomically write the cache to disk (write-then-rename)."""
    cache["last_scan"] = datetime.now().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(os.path.abspath(cache_file)), exist_ok=True)
    tmp_path = cache_file + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2)
    os.replace(tmp_path, cache_file)  # atomic on POSIX


# ── Pattern helpers ───────────────────────────────────────────────────────────

def _compile(patterns: list[str]) -> list[re.Pattern]:
    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error as exc:
            print(f"  [warn] invalid exclude pattern '{p}': {exc}", file=sys.stderr)
    return compiled


def is_excluded(rel_path: str, patterns: list[re.Pattern]) -> bool:
    norm = rel_path.replace(os.sep, "/")
    return any(pat.search(norm) for pat in patterns)


# ── Extension filter ─────────────────────────────────────────────────────────

def _ext_filter(
    filename: str,
    include_exts: set[str],
    exclude_exts: set[str],
) -> bool:
    """Return True if filename passes the extension include/exclude rules.

    Rules (applied in order):
      1. If exclude_exts is non-empty and ext is in it → reject.
      2. If include_exts is non-empty and ext is NOT in it → reject.
      3. Otherwise → accept.

    Extensions are normalized to lowercase, with no leading dot.
    An empty include_exts means "accept all extensions not excluded."
    """
    ext = Path(filename).suffix.lstrip(".").lower()
    if exclude_exts and ext in exclude_exts:
        return False
    if include_exts and ext not in include_exts:
        return False
    return True


# ── File discovery ────────────────────────────────────────────────────────────

def discover_files(
    repo_root: str,
    scan_dirs: list[str],
    include_exts: set[str],
    exclude_exts: set[str],
) -> list[tuple[str, str]]:
    """Walk scan_dirs and return (abs_path, rel_path) for files matching the extension filter."""
    results: list[tuple[str, str]] = []
    for scan_dir in scan_dirs:
        abs_dir = os.path.normpath(os.path.join(repo_root, scan_dir.strip()))
        if not os.path.isdir(abs_dir):
            print(f"  [warn] directory not found: {abs_dir}", file=sys.stderr)
            continue
        for dirpath, dirnames, filenames in os.walk(abs_dir, topdown=True):
            # Skip hidden directories in-place to avoid descending into them
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for fn in sorted(filenames):
                if _ext_filter(fn, include_exts, exclude_exts):
                    abs_path = os.path.join(dirpath, fn)
                    rel_path = os.path.relpath(abs_path, repo_root)
                    results.append((abs_path, rel_path))
    return results


# ── Main update logic ─────────────────────────────────────────────────────────

def update_cache(
    repo_root: str,
    scan_dirs: list[str],
    cache_file: str,
    user_excludes: list[str],
    include_exts: set[str],
    exclude_exts: set[str],
    force: bool = False,
) -> dict[str, int]:
    """Scan for changed files, update cache, return statistics dict."""

    all_patterns = _compile(_BUILTIN_EXCLUDES + user_excludes)
    cache = (
        {"version": CACHE_VERSION, "last_scan": None, "files": {}}
        if force
        else load_cache(cache_file)
    )

    stats = {"added": 0, "updated": 0, "removed": 0, "unchanged": 0, "excluded": 0}
    found_rel_paths: set[str] = set()

    for abs_path, rel_path in discover_files(repo_root, scan_dirs, include_exts, exclude_exts):
        if is_excluded(rel_path, all_patterns):
            stats["excluded"] += 1
            continue

        found_rel_paths.add(rel_path)

        current_mtime = datetime.fromtimestamp(
            os.path.getmtime(abs_path)
        ).isoformat(timespec="seconds")

        cached = cache["files"].get(rel_path)
        if not force and cached and cached.get("mtime") == current_mtime:
            stats["unchanged"] += 1
            continue

        meta = extract_meta(abs_path, repo_root)
        if "error" in meta:
            print(f"  [warn] skipping {rel_path}: {meta['error']}", file=sys.stderr)
            stats["excluded"] += 1
            continue

        is_new = rel_path not in cache["files"]
        cache["files"][rel_path] = meta
        stats["added" if is_new else "updated"] += 1

    # Remove entries for files that no longer exist
    stale = set(cache["files"].keys()) - found_rel_paths
    for key in stale:
        del cache["files"][key]
        stats["removed"] += 1

    save_cache(cache, cache_file)
    return stats


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_exts(raw: str) -> set[str]:
    """Parse comma-separated extension string into a normalized set (lowercase, no dot)."""
    return {e.strip().lstrip(".").lower() for e in raw.split(",") if e.strip()}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Incrementally update the /scan metadata cache"
    )
    parser.add_argument("--repo-root", required=True, help="Repository root path")
    parser.add_argument(
        "--dirs",
        default=".",
        help="Comma-separated scan directories (relative to repo-root)",
    )
    parser.add_argument("--cache", required=True, help="Cache file path")
    parser.add_argument(
        "--exclude",
        default="",
        help="Comma-separated additional path exclude patterns (Python regex)",
    )
    parser.add_argument(
        "--file-include",
        default="md",
        metavar="EXTS",
        help="Comma-separated extensions to include, e.g. 'md' or 'md,mdx' (empty = all)",
    )
    parser.add_argument(
        "--file-exclude",
        default="",
        metavar="EXTS",
        help="Comma-separated extensions to exclude, e.g. 'pdf,png'",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore existing cache and do a full rescan",
    )
    args = parser.parse_args()

    scan_dirs = [d.strip() for d in args.dirs.split(",") if d.strip()]
    user_excludes = [p.strip() for p in args.exclude.split(",") if p.strip()]
    include_exts = _parse_exts(args.file_include)
    exclude_exts = _parse_exts(args.file_exclude)

    stats = update_cache(
        repo_root=args.repo_root,
        scan_dirs=scan_dirs,
        cache_file=args.cache,
        user_excludes=user_excludes,
        include_exts=include_exts,
        exclude_exts=exclude_exts,
        force=args.force,
    )

    total_active = stats["added"] + stats["updated"] + stats["unchanged"]
    print(
        f"  Cache: {total_active} files tracked  "
        f"[+{stats['added']} new  "
        f"~{stats['updated']} changed  "
        f"-{stats['removed']} removed  "
        f"={stats['unchanged']} unchanged  "
        f"/{stats['excluded']} excluded]"
    )


if __name__ == "__main__":
    main()
