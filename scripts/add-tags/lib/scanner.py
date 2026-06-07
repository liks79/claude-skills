#!/usr/bin/env python3
"""
Phase 1 — Scan Obsidian vault markdown files and update tag cache.

Scan modes (fastest → slowest):
  --paths  Surgical: rescan only specified file paths (e.g. after tagging N files)
  --delta  Fast:     find files newer than cache file via OS-level `find -newer`
  default  Incremental: check all files but skip mtime-unchanged ones (O(N) stat calls)
  --force  Full:     ignore cache, re-read every file

Open-source: works with any Obsidian vault — no Claude Code required.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

# ── Constants ─────────────────────────────────────────────────────────────────
CACHE_VERSION = "1.2"

DEFAULT_EXCLUDES: frozenset[str] = frozenset({
    ".git", ".claude", ".obsidian", "TEMPLATES", "WIKI",
    "Clippings", "Excalidraw", "node_modules", "40_ARCHIVES",
    ".trash", ".cache", "__pycache__", ".venv", "venv",
    "dist-info", "site-packages",
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_repo_root() -> Path:
    r = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(r.stdout.strip())


def parse_frontmatter(content: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    fm_text = m.group(1)
    if _HAS_YAML:
        try:
            return yaml.safe_load(fm_text) or {}
        except Exception:
            pass
    result: dict = {}
    for line in fm_text.split("\n"):
        kv = re.match(r"^(\w[\w\-]*):\s*(.+)$", line)
        if kv:
            result[kv.group(1)] = kv.group(2).strip().strip("\"'")
    return result


def extract_raw_tags(content: str) -> list[str]:
    """
    Extract tags directly from raw frontmatter text, bypassing YAML parsing.
    Handles Obsidian-style 'tags: #tag1 #tag2' where YAML treats '#' as comment.
    """
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return []
    fm_text = m.group(1)

    tag_block = re.search(
        r"^tags\s*:(.*?)(?=^\w|\Z)",
        fm_text,
        re.MULTILINE | re.DOTALL,
    )
    if not tag_block:
        return []

    tag_text = tag_block.group(1)
    hash_tags = re.findall(r"#[\w\-/À-￿]+", tag_text)
    if hash_tags:
        return sorted(set(hash_tags))

    list_items = re.findall(r"^\s*-\s+[\"']?([^\s\"'\n#][^\s\"'\n]*)[\"']?", tag_text, re.MULTILINE)
    if list_items:
        return sorted({"#" + item for item in list_items if item})

    return []


def extract_title(content: str, path: Path) -> str:
    fm = parse_frontmatter(content)
    if fm.get("title"):
        return str(fm["title"])
    for line in content.split("\n")[:30]:
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").replace("_", " ")


def normalize_tags(raw) -> list[str]:
    if not raw:
        return []
    items: list[str] = []
    if isinstance(raw, (str, int, float)):
        items = re.split(r"[\s,]+", str(raw).strip())
    elif isinstance(raw, list):
        for item in raw:
            items.extend(re.split(r"[\s,]+", str(item).strip()))
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        item = item.strip().strip("\"'").strip()
        if not item or item in ("-", "null", "~"):
            continue
        if not item.startswith("#"):
            item = "#" + item
        if item not in seen:
            seen.add(item)
            result.append(item)
    return sorted(result)


def should_exclude(path: Path, repo_root: Path,
                   excludes: frozenset[str] = DEFAULT_EXCLUDES) -> bool:
    try:
        parts = path.relative_to(repo_root).parts
    except ValueError:
        return True
    return any(part in excludes for part in parts)


def scan_file(path: Path, repo_root: Path) -> dict | None:
    try:
        stat = path.stat()
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    fm = parse_frontmatter(content)
    raw_tags = extract_raw_tags(content)
    tags = raw_tags if raw_tags else normalize_tags(fm.get("tags"))

    return {
        "path": str(path.relative_to(repo_root)),
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "title": extract_title(content, path),
        "created": str(fm.get("created", fm.get("date", ""))),
        "tags": tags,
        "has_tags": len(tags) > 0,
        "tagged_by_llm": False,
        "llm_tagged_at": None,
    }


# ── Cache I/O ─────────────────────────────────────────────────────────────────

def load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            if data.get("version") == CACHE_VERSION:
                return data
        except Exception:
            pass
    return _empty_cache()


def _empty_cache() -> dict:
    return {
        "version": CACHE_VERSION,
        "last_scan": None,
        "files": {},
        "tag_index": {},
        "stats": {"total": 0, "tagged": 0, "untagged": 0},
    }


def save_cache(cache: dict, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(cache_path)


def rebuild_tag_index(files: dict) -> dict[str, list[str]]:
    """Full rebuild of tag → [sorted file paths] index. O(total_files)."""
    index: dict[str, list[str]] = {}
    for file_path, meta in files.items():
        for tag in meta.get("tags", []):
            index.setdefault(tag, []).append(file_path)
    for tag in index:
        index[tag].sort()
    return index


def update_tag_index_for_files(
    tag_index: dict,
    old_entries: dict,
    new_entries: dict,
) -> dict:
    """
    Incrementally update tag_index for a subset of changed files. O(changed_files).

    Removes old tag associations for updated/deleted files,
    then adds new tag associations. Avoids full O(total_files) rebuild.
    """
    # Remove old associations for changed files
    for rel, old_meta in old_entries.items():
        for tag in old_meta.get("tags", []):
            paths = tag_index.get(tag, [])
            if rel in paths:
                paths.remove(rel)
            if not paths:
                tag_index.pop(tag, None)

    # Add new associations
    for rel, new_meta in new_entries.items():
        for tag in new_meta.get("tags", []):
            tag_index.setdefault(tag, [])
            if rel not in tag_index[tag]:
                tag_index[tag].append(rel)
                tag_index[tag].sort()

    return tag_index


# ── Delta discovery via OS find -newer ───────────────────────────────────────

def find_delta_files(repo_root: Path, cache_path: Path,
                     include_dirs: list[Path]) -> list[Path]:
    """
    Use OS-level `find -newer cache_file` to quickly locate only
    files modified/created since the last scan. O(changed_files) reads.
    Falls back to empty list if find fails.
    """
    if not cache_path.exists():
        return []  # No cache → caller should do full scan

    found: list[Path] = []
    for sd in include_dirs:
        if not sd.is_dir():
            continue
        try:
            result = subprocess.run(
                ["find", str(sd), "-name", "*.md", "-newer", str(cache_path)],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.splitlines():
                p = Path(line.strip())
                if p.is_file() and not p.name.startswith("._") and not should_exclude(p, repo_root):
                    found.append(p)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # find not available → caller falls back to incremental

    return found


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan vault and update tag cache.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scan modes (fastest → slowest):
  --paths  Surgical: rescan only the listed files (best after tagging)
  --delta  Fast:     find only files newer than the cache via `find -newer`
  default  Incremental: check all file mtimes, skip unchanged
  --force  Full:     re-read every file, ignore cache entirely
""",
    )
    parser.add_argument("--force", action="store_true",
                        help="Full rescan, ignore cache entirely")
    parser.add_argument("--delta", action="store_true",
                        help="Fast: scan only files newer than the cache file")
    parser.add_argument("--paths", default=None,
                        help="Surgical: comma-separated file paths to rescan (relative to repo root)")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--include-dirs", default=".",
                        help="Comma-separated dirs relative to repo root")
    args = parser.parse_args()

    # ── Resolve paths ──────────────────────────────────────────────────────────
    repo_root = Path(args.repo_root) if args.repo_root else get_repo_root()
    script_dir = Path(__file__).parent.parent
    cache_dir = Path(args.cache_dir) if args.cache_dir else script_dir / ".cache"
    cache_path = cache_dir / "tag_cache.json"

    # ── Select scan mode ───────────────────────────────────────────────────────
    #
    # Auto-selection (no explicit flag needed):
    #   cache exists  → delta   (fast: only changed files via find -newer)
    #   no cache yet  → incremental (full walk to initialize)
    #
    # Explicit overrides:
    #   --paths  → surgical rescan of N specific files
    #   --force  → full rescan, ignore cache
    #   --delta  → accepted for backward compat (same as auto when cache exists)
    #
    _cache_exists = cache_path.exists() and not args.force
    scan_mode = "full" if args.force else (
        "paths" if args.paths else (
            "delta" if _cache_exists else "incremental"
        )
    )

    cache = _empty_cache() if args.force else load_cache(cache_path)
    files_cache: dict = cache.get("files", {})
    tag_index: dict = cache.get("tag_index", {})

    scan_dirs = [
        repo_root / d.strip()
        for d in args.include_dirs.split(",")
        if d.strip()
    ]

    # ── Build file list based on mode ─────────────────────────────────────────
    if scan_mode == "paths":
        # Surgical: caller knows exactly which files changed (e.g. after tagging)
        target_rels = [p.strip() for p in args.paths.split(",") if p.strip()]
        all_md = [repo_root / r for r in target_rels if (repo_root / r).exists()]
        print(f"  Mode: surgical ({len(all_md)} specific files)")

    elif scan_mode == "delta":
        # Fast delta: OS-level find -newer cache_file
        delta_files = find_delta_files(repo_root, cache_path, scan_dirs)
        if delta_files:
            all_md = delta_files
            print(f"  Mode: delta ({len(all_md)} files changed since last scan)")
        else:
            # No changed files found (or find failed) → nothing to do
            all_md = []
            print("  Mode: delta — no changes detected")

    else:
        # Incremental or full: walk all directories
        all_md = []
        for sd in scan_dirs:
            if sd.is_dir():
                all_md.extend(
                    p for p in sd.rglob("*.md")
                    if not should_exclude(p, repo_root)
                )
        if scan_mode == "full":
            print(f"  Mode: full rescan ({len(all_md)} files)")
        else:
            print(f"  Mode: incremental ({len(all_md)} files to check)")

    # ── Process files ──────────────────────────────────────────────────────────
    new_count = changed_count = unchanged_count = 0
    current_paths: set[str] = set()
    changed_old: dict = {}  # old cache entries for changed files (for incremental index update)
    changed_new: dict = {}  # new cache entries for changed files

    for path in sorted(all_md):
        if path.name.startswith("._"):
            continue
        rel = str(path.relative_to(repo_root))
        current_paths.add(rel)
        current_mtime = path.stat().st_mtime
        cached = files_cache.get(rel)

        # In incremental mode, skip mtime-unchanged files
        if scan_mode == "incremental" and cached and abs(cached.get("mtime", 0) - current_mtime) < 0.01:
            unchanged_count += 1
            continue

        meta = scan_file(path, repo_root)
        if meta is None:
            continue

        if cached:
            meta["tagged_by_llm"] = cached.get("tagged_by_llm", False)
            meta["llm_tagged_at"] = cached.get("llm_tagged_at")
            changed_old[rel] = cached
            changed_count += 1
        else:
            new_count += 1

        changed_new[rel] = meta
        files_cache[rel] = meta

    # ── Handle deletions (only in full/incremental modes) ─────────────────────
    deleted: set[str] = set()
    if scan_mode in ("full", "incremental"):
        deleted = set(files_cache.keys()) - current_paths - set(changed_new.keys())
        # In incremental mode, current_paths only has scanned files, so we need
        # all currently existing paths to detect deletions properly
        if scan_mode == "incremental":
            # Re-check: current_paths includes all rglob results, so this is correct
            deleted = set(files_cache.keys()) - {
                str(p.relative_to(repo_root))
                for p in all_md
                if not p.name.startswith("._")
            }
        for p in deleted:
            old_meta = files_cache.pop(p, {})
            if old_meta:
                changed_old[p] = old_meta  # so index update removes it

    # ── Update tag index ───────────────────────────────────────────────────────
    if scan_mode in ("paths", "delta") and (changed_old or changed_new):
        # Incremental index update — O(changed_files) instead of O(total_files)
        tag_index = update_tag_index_for_files(tag_index, changed_old, changed_new)
    elif changed_old or changed_new or deleted:
        # Full rebuild (force/incremental with many changes)
        tag_index = rebuild_tag_index(files_cache)

    # ── Recompute stats ────────────────────────────────────────────────────────
    tagged = sum(1 for m in files_cache.values() if m.get("has_tags"))
    untagged = len(files_cache) - tagged

    updated_cache = {
        "version": CACHE_VERSION,
        "last_scan": datetime.now(timezone.utc).isoformat(),
        "files": files_cache,
        "tag_index": tag_index,
        "stats": {
            "total": len(files_cache),
            "tagged": tagged,
            "untagged": untagged,
        },
    }
    save_cache(updated_cache, cache_path)

    print(
        f"  Cache: {len(files_cache)} files tracked  "
        f"[+{new_count} new  ~{changed_count} changed  "
        f"-{len(deleted)} removed  ={unchanged_count} unchanged]"
    )
    print(f"  Tagged: {tagged}  Untagged: {untagged}")


if __name__ == "__main__":
    main()
