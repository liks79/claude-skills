Scan the vault and build/update the research index at `$SCAN_OUTPUT_DIR/$TARGET_FILENAME`.

> **Compatibility**: Tested and verified with **Quartz v5.0+** (Debian 13, Node.js v26).
> Link format uses standard Markdown `[title](path)` — not wikilinks — to avoid the
> `|` table-cell parsing issue in Quartz v5's remark pipeline.
> Tag links use `#tag` (OFM-processed) with a fallback to `` `code span` `` for
> emoji-prefixed tags incompatible with the v5 community OFM regex (`\p{L}` only, no `\p{Emoji}`).

## Environment Variables

Configure in `~/.claude/settings.local.json` → `"env"` block:

| Variable | Default | Description |
|---|---|---|
| `SCAN_OUTPUT_DIR` | `00_INBOX` | Output directory (relative to repo root) |
| `TARGET_FILENAME` | `index.md` | Output filename |
| `BASE_DIR` | *(auto-detected)* | Repository root override |
| `SCAN_INCLUDE_DIRS` | `.` | Comma-separated directories to scan (`.` = entire repo) |
| `SCAN_FILE_INCLUDE` | `md` | Comma-separated extensions to **include** (no dot; empty = all) |
| `SCAN_FILE_EXCLUDE` | *(empty)* | Comma-separated extensions to **exclude** (no dot) |
| `SCAN_EXCLUDE_PATTERNS` | *(built-in)* | Comma-separated additional path exclude patterns (Python regex) |
| `SCAN_CACHE_DIR` | `<repo>/.claude/scripts/scan/.cache` | Metadata cache directory |

> **Built-in path excludes** (always applied regardless of env): `.git/`, `.claude/`, `.obsidian/`, `TEMPLATES/`, `WIKI/`, `Clippings/`, `Excalidraw/`, `node_modules/`, `40_ARCHIVES/`

## Arguments

`$ARGUMENTS` may include:

| Flag | Short | Description |
|------|-------|-------------|
| `--output-dir DIR` | `-o` | Override output directory |
| `--filename NAME` | `-f` | Override output filename |
| `--dirs DIRS` | | Comma-separated scan directories |
| `--file-include EXTS` | | Extensions to include, e.g. `md` or `md,mdx` |
| `--file-exclude EXTS` | | Extensions to exclude, e.g. `pdf,png` |
| `--force` | | Ignore cache, do a full rescan |

## Examples

```
/scan                                    → 00_INBOX/index.md (all .md in repo)
/scan --force                            → Full rescan, ignore cache
/scan -o 20_AREAS/ai-ml                  → Output to 20_AREAS/ai-ml/index.md
/scan -f my_index.md                     → Custom filename
/scan --dirs 20_AREAS/ai-ml              → Scan only ai-ml subdirectory
/scan --file-include md,mdx              → Include .md and .mdx files
/scan --file-include md --file-exclude   → Only .md, no extra exclusions
```

## Procedure

```bash
# Script resolution (plugin cache-aware)
_S=$(find "$HOME/.claude/plugins/cache" -name "scan.sh" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/scan/scan.sh"
bash "$_S" $ARGUMENTS
```

- Output the script results **exactly as-is**. Do not modify or reinterpret the content.
- If the script fails, pass the error message to the user.
