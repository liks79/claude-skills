#!/usr/bin/env python3
"""
build_index.py — Generate the markdown research index from the metadata cache.

Output structure:
  - YAML front-matter (updated, total, generated_by)
  - Summary: year × month matrix table with clickable monthly counts
  - Tags cloud: all unique tags as Obsidian inline #tag notation
  - Documents grouped by year → month (newest first), tagged only
  - Undated files section (if any)

Tag links use Obsidian-native #tag inline notation.
Quartz's ObsidianFlavoredMarkdown transformer automatically converts
#tag to <a href="/tags/tag"> — no hardcoded base URL required.

Usage:
  python3 build_index.py --cache FILE --output FILE --repo-root ROOT
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


# ── Cache loader ──────────────────────────────────────────────────────────────

def load_cache(cache_file: str) -> dict:
    with open(cache_file, encoding="utf-8") as fh:
        return json.load(fh)


# ── Link helpers ──────────────────────────────────────────────────────────────

def parse_ym(created: str) -> tuple[str, str] | None:
    """Extract (year, month) from a date string, or None."""
    if not created:
        return None
    m = re.match(r"^(\d{4})-(\d{2})", created)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^(\d{4})$", created)
    if m:
        return m.group(1), "01"
    return None


def make_doc_link(vault_rel_path: str, output_path: str, repo_root: str, title: str) -> str:
    """Create a markdown table-safe link to a document.

    Root cause of previous breakage: [[path|title]] wikilinks contain '|' which
    Quartz v5's remark table parser splits into separate cells BEFORE the OFM
    wikilink textTransform runs, corrupting the table structure.

    Fix: use standard [title](path) links — no '|' in table cells.

    Path encoding strategy (CommonMark compatible):
      - ASCII-only path          → [title](../path/to/file)
      - Path with spaces/Korean  → [title](<../path with spaces>)  (angle-bracket URL)
      - Path with < or > chars   → encode only those as %3C / %3E, then angle-bracket
    """
    abs_target = os.path.normpath(os.path.join(repo_root, vault_rel_path))
    output_dir = os.path.dirname(os.path.abspath(output_path))
    rel = os.path.relpath(abs_target, output_dir)
    path = re.sub(r"\.md$", "", rel).replace("\\", "/")

    # Escape < and > first (they break angle-bracket URL syntax)
    path_safe = path.replace("<", "%3C").replace(">", "%3E")

    # Escape | in title (table cell separator)
    title_safe = title.replace("|", "∣")

    # Use angle brackets if path has spaces or non-ASCII characters
    if re.search(r"[ \t]|[^\x00-\x7F]", path_safe):
        return f"[{title_safe}](<{path_safe}>)"
    return f"[{title_safe}]({path_safe})"


def _ofm_v5_tag_safe(tag: str) -> bool:
    """Check if tag matches Quartz v5 OFM community plugin tag regex.

    v4 built-in:  /(?<=^| )#((?:[-_\\p{L}\\p{Emoji}\\p{M}\\d])+)/gu  ← emoji OK
    v5 community: /(?<=^|\\s)#((?:[-_\\p{L}\\d])+)/gu                 ← NO emoji

    Python str.isalpha() returns True for Unicode letters (a-z, Korean, etc.)
    but False for emoji (📥, etc.), matching the \\p{L} vs \\p{Emoji} split.
    """
    return bool(tag) and all(c.isalpha() or c.isdigit() or c in "-_/" for c in tag)


def make_tag_link(tag: str) -> str:
    """Return a tag as #tag (OFM-linkable) or `tag` (code span fallback).

    Uses #tag notation when the tag is compatible with Quartz v5 OFM regex.
    Falls back to a plain code span for emoji-prefixed tags (e.g. '📥-inbox')
    since the v5 community OFM plugin tag regex excludes \\p{Emoji}.
    """
    if not tag:
        return ""
    if _ofm_v5_tag_safe(tag):
        return f"#{tag}"
    # Emoji or other non-letter-digit chars: show as code span, no broken link
    return f"`{tag}`"


def safe_title(title: str) -> str:
    return title.replace("|", "\\|")


# ── Summary matrix table ──────────────────────────────────────────────────────

_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_MONTH_KEYS = [f"{m:02d}" for m in range(1, 13)]


def build_summary_table(
    year_counts: Counter,
    month_counts: Counter,
) -> list[str]:
    """Build the year × month matrix table with anchor links per cell."""
    lines: list[str] = []

    # Header
    lines.append("| 연도 | " + " | ".join(_MONTH_ABBR) + " | 합계 |")
    lines.append("|:----:|" + "|".join([":---:"] * 12) + "|:----:|")

    # Per-year rows
    col_totals: list[int] = [0] * 12
    grand_total = 0

    for year in sorted(year_counts.keys(), reverse=True):
        cells = [year]
        for i, m in enumerate(_MONTH_KEYS):
            cnt = month_counts.get((year, m), 0)
            col_totals[i] += cnt
            grand_total += cnt
            # Anchor matches the heading "### {year}-{m}" → #year-mm
            cells.append(f"[{cnt}](#{year}-{m})" if cnt else "—")
        cells.append(f"**{year_counts[year]}**")
        lines.append("| " + " | ".join(cells) + " |")

    # Total row
    total_cells = ["**합계**"]
    for cnt in col_totals:
        total_cells.append(f"**{cnt}**" if cnt else "—")
    total_cells.append(f"**{grand_total}**")
    lines.append("| " + " | ".join(total_cells) + " |")

    return lines


# ── Tags cloud ────────────────────────────────────────────────────────────────

def build_tags_cloud(all_tags: Counter, max_tags: int = 60) -> list[str]:
    """Render a compact tag cloud sorted by frequency using #tag notation."""
    lines: list[str] = []
    parts: list[str] = []

    for tag, cnt in all_tags.most_common(max_tags):
        parts.append(f"{make_tag_link(tag)}&nbsp;`×{cnt}`")

    if parts:
        # Break into lines of ~8 tags each for readability
        chunk = 8
        for i in range(0, len(parts), chunk):
            lines.append(" &nbsp; ".join(parts[i:i + chunk]) + "  ")
    else:
        lines.append("*(태그 없음)*")

    return lines


# ── Index builder ─────────────────────────────────────────────────────────────

def build_index(cache: dict, output_path: str, repo_root: str) -> str:
    """Build and return the full markdown content for the index file."""
    files: dict[str, dict] = cache.get("files", {})
    today = datetime.now().strftime("%Y-%m-%d")
    last_scan = (cache.get("last_scan") or today)[:10]

    # ── Collect valid entries ──────────────────────────────────────────────────
    dated: list[tuple[tuple[str, str], dict]] = []
    undated: list[dict] = []

    for meta in files.values():
        if "error" in meta:
            continue
        if meta.get("generated_by"):   # skip auto-generated index files
            continue
        ym = parse_ym(meta.get("created", ""))
        if ym:
            dated.append((ym, meta))
        else:
            undated.append(meta)

    dated.sort(
        key=lambda x: (x[0][0], x[0][1], x[1].get("created", "")),
        reverse=True,
    )
    total = len(dated) + len(undated)

    # ── Aggregate statistics ───────────────────────────────────────────────────
    year_counts: Counter[str] = Counter()
    month_counts: Counter[tuple[str, str]] = Counter()
    all_tags: Counter[str] = Counter()

    for (year, month), meta in dated:
        year_counts[year] += 1
        month_counts[(year, month)] += 1
        for tag in (meta.get("tags") or []):
            if tag:
                all_tags[tag] += 1

    # ── Compose markdown ───────────────────────────────────────────────────────
    lines: list[str] = []

    # Front-matter
    lines += [
        "---",
        f"updated: {today}",
        f"total_files: {total}",
        "generated_by: /scan",
        "---",
        "",
        "# Research Index",
        "",
        (
            f"> **업데이트**: {today}"
            f" &nbsp;|&nbsp; **스캔 기준**: {last_scan}"
            f" &nbsp;|&nbsp; **총 {total}건**"
        ),
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    # ── Year × Month matrix table ──────────────────────────────────────────────
    lines += build_summary_table(year_counts, month_counts)
    lines.append("")

    # ── Tags cloud ─────────────────────────────────────────────────────────────
    lines += ["### Tags", ""]
    lines += build_tags_cloud(all_tags)
    lines += ["", "---", ""]

    # ── Document list grouped by year → month ──────────────────────────────────
    current_year: str | None = None
    current_month: str | None = None

    for (year, month), meta in dated:
        # Year heading
        if year != current_year:
            current_year = year
            current_month = None
            lines += [f"## {year}", ""]

        # Month heading — plain "YYYY-MM" so anchor is predictably #yyyy-mm
        if month != current_month:
            current_month = month
            cnt = month_counts[(year, month)]
            lines += [
                "",
                f"### {year}-{month}",
                f"> {cnt}건",
                "",
                "| 날짜 | 제목 | 태그 |",
                "|------|------|------|",
            ]

        # Row
        title = meta.get("title") or Path(meta["path"]).stem
        link = make_doc_link(meta["path"], output_path, repo_root, title)
        created = (meta.get("created") or "")[:10]
        tags = meta.get("tags") or []
        tag_str = " ".join(make_tag_link(t) for t in tags[:7] if t)

        lines.append(f"| {created} | {link} | {tag_str} |")

    lines.append("")

    # ── Undated files ──────────────────────────────────────────────────────────
    if undated:
        lines += [
            "---",
            "",
            "## 날짜 미상",
            "",
            "| 파일 | 태그 |",
            "|------|------|",
        ]
        for meta in sorted(undated, key=lambda m: m.get("path", "")):
            title = meta.get("title") or Path(meta["path"]).stem
            link = make_doc_link(meta["path"], output_path, repo_root, title)
            tags = meta.get("tags") or []
            tag_str = " ".join(make_tag_link(t) for t in tags[:7] if t)
            lines.append(f"| {link} | {tag_str} |")
        lines.append("")

    lines += [
        "---",
        "",
        "*이 파일은 `/scan` 커맨드로 자동 생성됩니다. 직접 편집하지 마세요.*",
        "",
    ]

    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate markdown research index from the /scan metadata cache"
    )
    parser.add_argument("--cache", required=True, help="Path to meta_cache.json")
    parser.add_argument("--output", required=True, help="Output markdown file path")
    parser.add_argument("--repo-root", required=True, help="Repository root path")
    args = parser.parse_args()

    cache = load_cache(args.cache)
    content = build_index(cache, args.output, args.repo_root)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(content)

    total = sum(1 for m in cache.get("files", {}).values() if "error" not in m)
    print(f"  Index: {total} entries → {args.output}")


if __name__ == "__main__":
    main()
