#!/usr/bin/env python3
"""
Phase 2 — Assign tags to untagged markdown files using Claude API.

Reads the tag cache, identifies untagged files, uses claude-haiku to suggest
tags from the existing vocabulary, then writes tags to the file's frontmatter.

Environment variables:
  ANTHROPIC_API_KEY   Required. Claude API key.
  ADD_TAGS_MODEL      Override LLM model (default: claude-haiku-4-5-20251001)
  ADD_TAGS_MAX_FILES  Max untagged files to process per run (default: 50)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_FILES = 50
CONTENT_PREVIEW_CHARS = 600
TOP_TAGS_CONTEXT = 40          # How many top tags to include in prompt


# ── Frontmatter manipulation ──────────────────────────────────────────────────

def has_frontmatter(content: str) -> bool:
    return bool(re.match(r"^---\s*\n", content))


def apply_tags_to_frontmatter(content: str, tags: list[str]) -> str:
    """
    Insert/replace tags in frontmatter.
    Preserves all other frontmatter fields exactly.
    Falls back to prepending a new frontmatter block if none exists.
    """
    tags_line = "tags: " + " ".join(tags)

    if has_frontmatter(content):
        # Find the frontmatter block
        m = re.match(r"^(---\s*\n)(.*?)(\n---)", content, re.DOTALL)
        if not m:
            # Malformed frontmatter — prepend new block
            return f"---\n{tags_line}\n---\n\n{content}"

        prefix, fm_body, suffix = m.group(1), m.group(2), m.group(3)
        rest = content[m.end():]

        if re.search(r"^tags\s*:", fm_body, re.MULTILINE):
            # Replace existing tags line(s) — handle both inline and block YAML list
            # Remove existing tags entry (could span multiple lines for list format)
            fm_body = re.sub(
                r"^tags\s*:.*?(?=\n\S|\Z)",
                tags_line,
                fm_body,
                flags=re.MULTILINE | re.DOTALL,
            )
        else:
            # Insert tags after type/title if present, otherwise at the end
            insert_after = re.search(r"^(type|title)\s*:.*$", fm_body, re.MULTILINE)
            if insert_after:
                pos = insert_after.end()
                fm_body = fm_body[:pos] + "\n" + tags_line + fm_body[pos:]
            else:
                fm_body = fm_body.rstrip("\n") + "\n" + tags_line

        return prefix + fm_body + suffix + rest

    else:
        # No frontmatter — prepend minimal block
        return f"---\n{tags_line}\n---\n\n{content}"


# ── LLM integration ───────────────────────────────────────────────────────────

def build_tag_vocab(tag_index: dict, top_n: int = TOP_TAGS_CONTEXT) -> str:
    """Return the most-used tags as a compact string for the prompt."""
    sorted_tags = sorted(tag_index.items(), key=lambda kv: len(kv[1]), reverse=True)
    top = [tag for tag, _ in sorted_tags[:top_n]]
    return ", ".join(top)


def call_llm(client, model: str, title: str, content_preview: str, vocab: str) -> list[str]:
    """Ask Claude to suggest tags. Returns list of '#tag' strings."""
    system = (
        "You are a document tagging assistant for an Obsidian knowledge base. "
        "Given a document title and content preview, suggest 3–7 appropriate tags. "
        "Prefer tags from the existing vocabulary. Use kebab-case for new tags. "
        "Respond ONLY with a JSON object: {\"tags\": [\"#tag1\", \"#tag2\"]}"
    )
    user = (
        f"EXISTING TAG VOCABULARY (prefer these):\n{vocab}\n\n"
        f"DOCUMENT TITLE: {title}\n\n"
        f"CONTENT PREVIEW:\n{content_preview}\n\n"
        "Respond with JSON only."
    )

    response = client.messages.create(
        model=model,
        max_tokens=200,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    raw = response.content[0].text.strip()

    # Parse JSON response
    json_match = re.search(r'\{.*?"tags"\s*:\s*\[.*?\]\s*\}', raw, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group())
        tags = data.get("tags", [])
        # Normalize
        result = []
        for t in tags:
            t = t.strip().strip("\"'")
            if t and not t.startswith("#"):
                t = "#" + t
            if t:
                result.append(t)
        return result[:7]  # cap at 7

    # Fallback: extract #tags from free text
    return re.findall(r"#[\w\-/À-￿]+", raw)[:7]


# ── Cache helpers ─────────────────────────────────────────────────────────────

def load_cache(cache_path: Path) -> dict:
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        print(f"[error] Cannot read cache: {cache_path}", file=sys.stderr)
        sys.exit(1)


def save_cache(cache: dict, cache_path: Path) -> None:
    tmp = cache_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(cache_path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Assign LLM tags to untagged markdown files.")
    parser.add_argument("--dry-run", action="store_true", help="Show proposed tags without writing")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--model", default=os.environ.get("ADD_TAGS_MODEL", DEFAULT_MODEL))
    parser.add_argument("--max-files", type=int,
                        default=int(os.environ.get("ADD_TAGS_MAX_FILES", DEFAULT_MAX_FILES)))
    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).parent.parent
    cache_dir = Path(args.cache_dir) if args.cache_dir else script_dir / ".cache"
    cache_path = cache_dir / "tag_cache.json"

    try:
        import subprocess
        repo_root = (
            Path(args.repo_root)
            if args.repo_root
            else Path(subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, check=True
            ).stdout.strip())
        )
    except Exception:
        print("[error] Could not determine repo root. Run from inside a git repo.", file=sys.stderr)
        sys.exit(1)

    # Load Anthropic client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[error] ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        print("[error] anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    # Load cache
    cache = load_cache(cache_path)
    files: dict = cache.get("files", {})
    tag_index: dict = cache.get("tag_index", {})

    # Build vocabulary from existing tags
    vocab = build_tag_vocab(tag_index)

    # Identify untagged files
    untagged = [
        (rel, meta)
        for rel, meta in files.items()
        if not meta.get("has_tags")
    ]
    untagged.sort(key=lambda x: x[0])

    if not untagged:
        print("  No untagged files found.")
        return

    to_process = untagged[: args.max_files]
    print(f"  Untagged: {len(untagged)} files  |  Processing: {len(to_process)}")

    tagged_count = 0
    updated_paths: list[str] = []

    for rel, meta in to_process:
        abs_path = repo_root / rel
        if not abs_path.exists():
            continue

        try:
            content = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        preview = content[:CONTENT_PREVIEW_CHARS].replace("\n", " ")
        title = meta.get("title", Path(rel).stem)

        try:
            tags = call_llm(client, args.model, title, preview, vocab)
        except Exception as e:
            print(f"  [warn] LLM error for {rel}: {e}", file=sys.stderr)
            time.sleep(1)
            continue

        if not tags:
            print(f"  [warn] No tags returned for: {rel}")
            continue

        tags_display = " ".join(tags)
        print(f"  {'[dry]' if args.dry_run else '[tag]'} {rel}")
        print(f"         → {tags_display}")

        if not args.dry_run:
            new_content = apply_tags_to_frontmatter(content, tags)
            abs_path.write_text(new_content, encoding="utf-8")

            # Update cache entry
            files[rel]["tags"] = tags
            files[rel]["has_tags"] = True
            files[rel]["tagged_by_llm"] = True
            files[rel]["llm_tagged_at"] = datetime.now(timezone.utc).isoformat()
            files[rel]["mtime"] = abs_path.stat().st_mtime

            # Update tag index
            for tag in tags:
                tag_index.setdefault(tag, [])
                if rel not in tag_index[tag]:
                    tag_index[tag].append(rel)
                    tag_index[tag].sort()

            updated_paths.append(rel)

        tagged_count += 1
        time.sleep(0.3)  # polite rate limiting

    if not args.dry_run and tagged_count > 0:
        # Update stats
        tagged_total = sum(1 for m in files.values() if m.get("has_tags"))
        cache["files"] = files
        cache["tag_index"] = tag_index
        cache["stats"]["tagged"] = tagged_total
        cache["stats"]["untagged"] = len(files) - tagged_total
        save_cache(cache, cache_path)

    print(f"\n  Tagged {tagged_count} files {'(dry run — no writes)' if args.dry_run else ''}")

    # Write updated paths to stdout for shell to capture
    if updated_paths:
        sep = "\n    "
        print(f"  Updated:{sep}{sep.join(updated_paths)}")


if __name__ == "__main__":
    main()
