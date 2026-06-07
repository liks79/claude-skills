Scan an Obsidian vault, build a Tag Dictionary, and assign tags to untagged markdown files.

> **API 키 불필요** — Claude Code가 Read/Edit 툴로 태그를 직접 처리합니다.
> **Quartz v5 compatible**: All links use `[title](path)` standard Markdown (not wikilinks).
> Tag format: `tags: #tag1 #tag2` (Obsidian OFM inline, space-separated).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ADD_TAGS_OUTPUT_DIR` | `00_INBOX` | Output directory for `Tag_Dictionary.md` |
| `ADD_TAGS_FILENAME` | `Tag_Dictionary.md` | Output filename |
| `ADD_TAGS_CACHE_DIR` | `<script_dir>/.cache` | Cache directory |

## Arguments

`$ARGUMENTS` may include:

| Flag | Description |
|------|-------------|
| `--force` | Full rescan, ignore cache |
| `--delta` | Fast scan: only files newer than the cache (via `find -newer`) |
| `--paths "f1,f2"` | Surgical: rescan only listed files (comma-separated, relative paths) |
| `--no-assign` | Only scan + build dictionary; skip tag assignment |
| `--output-dir DIR` | Override output directory |
| `--filename NAME` | Override output filename |
| `--max-files N` | Max untagged files to process per run (default: 50) |
| `--include-dirs DIRS` | Comma-separated directories to scan (default: `.`) |

## Scan Mode Reference

| Mode | When to use | Speed |
|------|-------------|-------|
| `--paths "f1,f2"` | After tagging N files — rescan exactly those N files | ⚡ Fastest |
| *(auto, cache exists)* | Default — uses `find -newer cache` to skip unchanged files | 🚀 Fast |
| `--force` | Clean rebuild, or purge stale entries for deleted files | 🐢 Slow |
| *(auto, no cache)* | First run — full walk to initialize the cache | 🐢 Slow |

## Procedure

### Step 0 — Resolve script path

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "add_tags.sh" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/add-tags/add_tags.sh"

_LU=$(find "$HOME/.claude/plugins/cache" -name "list_untagged.py" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_LU" ] && _LU="scripts/add-tags/list_untagged.py"
```

---

### Step 1 — Phase 1: Scan vault

```bash
bash "$_S" --phase 1 $ARGUMENTS
```

Note the **Untagged** count. If `Untagged: 0`, skip to Step 4.

---

### Step 2 — Get untagged files list

If `--no-assign` is in `$ARGUMENTS`, skip this step and go to Step 4.

```bash
uv run python "$_LU" --max-files 50
```

Parse the JSON output to get `vocab` (existing tags) and `untagged` (files to tag).

---

### Step 3 — Assign tags to each untagged file

**Track the tagged file paths** — collect them as you process each file (you will need them in Step 4).

For every `{"path": "...", "title": "...", "preview": "..."}` entry:

1. **Read** the full file (Read tool, path relative to repo root)
2. **Analyze** content + `vocab` from Step 2
3. **Select 3–7 tags** (prefer existing vocab tags; create new kebab-case tags only when needed)
4. **Edit** the frontmatter:

| Situation | Action |
|-----------|--------|
| `tags:` field exists | Replace: `tags: #tag1 #tag2 ...` |
| No `tags:` field, frontmatter exists | Insert after first field: `tags: #tag1 #tag2 ...` |
| No frontmatter at all | Prepend `---\ntags: #tag1 #tag2\n---\n\n` |

Format: `tags: #tag1 #tag2 #tag3` — space-separated, no quotes, one line.

Print after each: `[tagged] <path> → #tag1 #tag2 ...`

---

### Step 4 — Update cache and rebuild Tag Dictionary

After Step 3, **use `--paths` for surgical rescan** of only the files you just tagged.
Build the comma-separated list of tagged paths from Step 3, then run:

```bash
# Example: if you tagged file_a.md and file_b.md:
bash "$_S" \
  --paths "tagged_file1.md,tagged_file2.md,..." \
  --phase 1

bash "$_S" --phase 3
```

If `--no-assign` was set (no files tagged), use `--delta` for a fast check:

```bash
bash "$_S" --delta
```

> **Why `--paths` instead of `--force`?**
> `--paths` re-reads only the N tagged files → O(N). `--force` re-reads all files → O(total).
> For typical runs (5–50 tagged files), `--paths` is 10–70× faster.

---

### Step 5 — Summary

```
════════════════════════════════════════════════
  ✅ Done
════════════════════════════════════════════════
  스캔한 파일 수     : <total>
  태그 추가한 파일   : <tagged_count>
  남은 태그 없는 파일: <remaining_untagged>
  Tag Dictionary     : 00_INBOX/Tag_Dictionary.md
```
