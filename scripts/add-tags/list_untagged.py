#!/usr/bin/env python3
"""
Helper — Output untagged files as JSON for Claude Code to process directly.

Reads tag_cache.json and emits:
  {
    "vocab": ["#tag1", ...],          # Top tags sorted by frequency
    "untagged": [                      # Files without tags
      {"path": "...", "title": "...", "preview": "..."},
      ...
    ],
    "total_untagged": N
  }

Claude Code reads this JSON, then uses Read/Edit tools to assign tags natively.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def get_repo_root() -> Path:
    import subprocess
    r = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    return Path(r.stdout.strip())


def get_body_preview(path: Path, chars: int = 400) -> str:
    """Return first N chars of body (after frontmatter)."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
        body = content[m.end():] if m else content
        return " ".join(body[:chars].split())
    except OSError:
        return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Output untagged files as JSON for Claude Code tagging."
    )
    parser.add_argument(
        "--max-files", type=int,
        default=50,
        help="Max untagged files to include (default: 50)",
    )
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument(
        "--vocab-size", type=int, default=60,
        help="Number of top tags to include as vocabulary context",
    )
    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent
    cache_dir = Path(args.cache_dir) if args.cache_dir else script_dir / ".cache"
    cache_path = cache_dir / "tag_cache.json"

    try:
        repo_root = (
            Path(args.repo_root) if args.repo_root else get_repo_root()
        )
    except Exception:
        print("[error] Not inside a git repository.", file=sys.stderr)
        sys.exit(1)

    if not cache_path.exists():
        print("[error] Cache not found. Run Phase 1 first.", file=sys.stderr)
        sys.exit(1)

    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    files: dict = cache.get("files", {})
    tag_index: dict = cache.get("tag_index", {})

    # Vocabulary: sorted by frequency
    vocab = sorted(tag_index.keys(), key=lambda t: -len(tag_index[t]))

    # Untagged files with content preview
    untagged_raw = [
        (rel, meta)
        for rel, meta in sorted(files.items())
        if not meta.get("has_tags")
    ]
    total_untagged = len(untagged_raw)

    untagged = []
    for rel, meta in untagged_raw[: args.max_files]:
        untagged.append({
            "path": rel,
            "title": meta.get("title", Path(rel).stem),
            "created": meta.get("created", ""),
            "preview": get_body_preview(repo_root / rel),
        })

    result = {
        "vocab": vocab[: args.vocab_size],
        "untagged": untagged,
        "total_untagged": total_untagged,
        "showing": len(untagged),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
