#!/usr/bin/env python3
"""
extract_meta.py — Extract metadata from a single markdown file.

Parses YAML frontmatter and body content to extract:
  - title       (frontmatter > first H1 heading > filename stem)
  - created     (YYYY-MM-DD, normalized from common date formats)
  - category    (derived from relative path structure)
  - tags        (normalized list, # prefix stripped)
  - classification, type

This module is imported by update_cache.py and can also be run standalone.

Usage:
  python3 extract_meta.py <filepath> [--repo-root ROOT]
  → prints JSON to stdout
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


# ── Frontmatter parser ────────────────────────────────────────────────────────

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body. Returns (fm_dict, body_text)."""
    if not content.startswith("---"):
        return {}, content

    end_idx = content.find("\n---", 3)
    if end_idx == -1:
        return {}, content

    fm_raw = content[3:end_idx].strip()
    body = content[end_idx + 4:].strip()
    return _parse_yaml_simple(fm_raw), body


def _parse_yaml_simple(text: str) -> dict:
    """Minimal YAML parser — handles the patterns found in Obsidian frontmatter.

    Supported value types:
      key: plain value
      key: "quoted value"
      key: [inline, list]
      key: #tag1 #tag2
      key:
        - block list item
    """
    result: dict = {}
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, raw = line.partition(":")
            key = key.strip()
            raw = raw.strip()

            # Block list: key:\n  - item\n  - item
            if raw == "" and i + 1 < len(lines) and lines[i + 1].lstrip().startswith("-"):
                items: list[str] = []
                i += 1
                while i < len(lines) and lines[i].lstrip().startswith("-"):
                    items.append(lines[i].strip().lstrip("- ").strip())
                    i += 1
                result[key] = items
                continue

            result[key] = _parse_scalar(raw)

        i += 1

    return result


def _parse_scalar(raw: str) -> object:
    """Parse a single YAML scalar value into Python type."""
    if not raw:
        return raw

    # Quoted string
    if len(raw) >= 2 and raw[0] in ('"', "'") and raw[-1] == raw[0]:
        return raw[1:-1]

    # Inline list: [a, b, c]
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1]
        return [t.strip().strip("\"'") for t in inner.split(",") if t.strip()]

    # Space-separated hashtag list: #tag1 #tag2 #tag3
    parts = raw.split()
    if parts and all(p.startswith("#") for p in parts):
        return [p.lstrip("#") for p in parts]

    return raw


# ── Field extractors ──────────────────────────────────────────────────────────

def extract_title(fm: dict, body: str, filepath: str) -> str:
    """Title priority: frontmatter 'title' → first H1 → filename stem."""
    if fm.get("title"):
        return str(fm["title"])
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("# ") and len(s) > 2:
            return s[2:].strip()
    return Path(filepath).stem


def normalize_tags(raw: object) -> list[str]:
    """Normalize tags to a flat list of strings with # prefix stripped.

    Also replaces internal spaces with hyphens: Obsidian/Quartz OFM tag regex
    matches only [\\-_\\p{L}\\p{Emoji}\\d]+ (no spaces), so '📥 inbox' would
    break the link. Normalizing to '📥-inbox' keeps the tag linkable.
    """
    if not raw:
        return []
    if isinstance(raw, list):
        tags = [str(t).strip().lstrip("#") for t in raw if t]
    elif isinstance(raw, str):
        # Handle both "tag1, tag2" and "#tag1 #tag2" formats
        parts = re.split(r"[\s,]+", raw.strip())
        tags = [p.lstrip("#") for p in parts if p and p != "#"]
    else:
        return []
    normalized = []
    for t in tags:
        t = re.sub(r"\s+", "-", t)                 # spaces → hyphens
        t = re.sub(r"[^\w가-힣/\-]+$", "", t)       # strip trailing punctuation (e.g. comma)
        if t:
            normalized.append(t)
    return normalized


def derive_category(rel_path: str) -> str:
    """Derive a category label from the file's relative path.

    Examples:
      20_AREAS/ai-ml/foo.md              → ai-ml
      20_AREAS/career/interview/foo.md   → career/interview
      20_AREAS/career/job-search/foo.md  → career/job-search
    """
    parts = Path(rel_path).parts
    # parts[0] = scan root (e.g. "20_AREAS"), parts[1] = area, parts[2] = subdir
    if len(parts) < 2:
        return "root"
    area = parts[1]
    if len(parts) >= 4:
        return f"{area}/{parts[2]}"
    return area


def normalize_date(raw: object) -> str:
    """Normalize various date formats to YYYY-MM-DD string."""
    if not raw:
        return ""
    s = str(raw).strip().strip("\"'")

    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    for fmt in ("%Y/%m/%d", "%d.%m.%Y", "%Y.%m.%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    if re.match(r"^\d{4}-\d{2}$", s):
        return s + "-01"
    if re.match(r"^\d{4}$", s):
        return s + "-01-01"
    return s  # return as-is if unrecognized


# ── Public API ────────────────────────────────────────────────────────────────

def extract_meta(filepath: str, repo_root: str | None = None) -> dict:
    """Extract metadata from a markdown file.

    Args:
        filepath:  Absolute or relative path to the .md file.
        repo_root: Repository root for computing relative path in output.

    Returns:
        dict with keys: path, title, created, category, tags,
                        classification, type, mtime.
        On read error, returns {'path': ..., 'error': '...'}.
    """
    abs_path = os.path.abspath(filepath)
    rel_path = os.path.relpath(abs_path, repo_root) if repo_root else abs_path

    try:
        with open(abs_path, encoding="utf-8") as fh:
            content = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        return {"path": rel_path, "error": str(exc)}

    fm, body = parse_frontmatter(content)

    return {
        "path": rel_path,
        "title": extract_title(fm, body, abs_path),
        "created": normalize_date(fm.get("created") or fm.get("date") or ""),
        "category": derive_category(rel_path),
        "tags": normalize_tags(fm.get("tags") or fm.get("tag") or ""),
        "classification": str(fm.get("classification", "") or ""),
        "type": str(fm.get("type", "") or ""),
        "generated_by": str(fm.get("generated_by", "") or ""),
        "mtime": datetime.fromtimestamp(
            os.path.getmtime(abs_path)
        ).isoformat(timespec="seconds"),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract metadata from a single markdown file (outputs JSON)"
    )
    parser.add_argument("filepath", help="Path to the .md file")
    parser.add_argument("--repo-root", default=None, help="Repo root for relative path")
    args = parser.parse_args()

    result = extract_meta(args.filepath, args.repo_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
