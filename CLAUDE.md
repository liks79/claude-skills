# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A Claude Code plugin published at `github:liks79/claude-skills`. It ships **28 slash commands, 4 skills, 1 agent, scripts, and 7 research templates** as a self-contained installable package.

The plugin manifest is at `.claude-plugin/plugin.json`. The marketplace entry is `.claude-plugin/marketplace.json`. Both must have matching `version` strings when releasing.

---

## Component Conventions

### Commands (`commands/*.md`)

- **First line** is the one-sentence description shown by `/cmds` — keep it concise and end it with `: $ARGUMENTS` or a short summary of what the command does.
- `$ARGUMENTS` is the raw string the user passes after the command name. Parse it in the first step of the procedure.
- Standard section order: `## Usage`, `## Procedure` (numbered steps), `## Error Handling`.
- Commands that call shell scripts **must** use the plugin-cache resolution pattern (see below).

### Skills (`skills/<name>/SKILL.md`)

Required YAML frontmatter:
```yaml
---
name: <name>
description: "<full trigger description — this drives auto-loading>"
---
```
The `description` field is what Claude Code matches against context. Make it exhaustive: list all user phrasings and file types that should trigger the skill. A vague description means the skill won't fire when it should.

Multi-file skills (like `pptx`) keep supporting docs (`editing.md`, `pptxgenjs.md`) alongside `SKILL.md` and reference them with relative links.

### Agents (`agents/<name>.md`)

Required YAML frontmatter:
```yaml
---
name: <name>
description: <one-line trigger description>
tools: Read, Write, Grep, Glob, Bash, WebFetch, WebSearch
model: inherit
---
```
Agents enforce their own scope in their procedure text — Claude Code does not technically restrict them. Write the scope constraint explicitly (e.g. "All output is limited to `career/`").

### Scripts (`scripts/*.py`, `scripts/*.sh`)

- Python scripts use `argparse` and accept `--output PATH` (write to stdout when omitted).
- Errors go to **stderr** prefixed with `Error:` — commands key off this prefix to detect failures.
- All dependencies are injected at runtime via `uv run --with <dep>`. No venv or `requirements.txt`.
- Scripts read secrets from environment variables, never from arguments.

Two scripts have non-flat layouts:

| Script | Layout | Notes |
|--------|--------|-------|
| `scripts/findjob/` | Python package | `findjob_run.py` at root is the launcher wrapper that imports it |
| `scripts/scan/` | `scan.sh` + `lib/` subdirectory | `lib/config.sh`, `lib/extract_meta.py`, `lib/update_cache.py`, `lib/build_index.py` |

`scan.sh` uses `BASH_SOURCE[0]`-based `SCRIPT_DIR` so it resolves `lib/` correctly from the plugin cache. New multi-file scripts should follow the same pattern.

### Templates (`templates/research/T<N>-*.md`)

- Frontmatter must include `classification:` and `depth: standard`.
- Sections marked `<!-- depth: quick → ... / standard → ... -->` guide Claude on verbosity. Strip these comments from final output.
- `_registry.md` is the authoritative mapping of template ID → file and command → default template. `apply-research-template.md` reads it at runtime; other commands have the logic inlined.

---

## Plugin-Cache Path Resolution

Commands cannot hardcode `scripts/` because when installed as a plugin the files live at `~/.claude/plugins/cache/claude-skills/<version>/scripts/`. Use this pattern in every command that calls a script:

```bash
# Script resolution
_S=$(find "$HOME/.claude/plugins/cache" -name "<script-file>" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/<script-file>"
```

For scripts with subdirectory layout (e.g. `scan.sh`), find by filename — `BASH_SOURCE[0]` inside the script handles the rest:

```bash
_S=$(find "$HOME/.claude/plugins/cache" -name "scan.sh" -path "*/claude-skills/*" 2>/dev/null | sort -rV | head -1)
[ -z "$_S" ] && _S="scripts/scan/scan.sh"
```

For templates:
```bash
# Template directory resolution
_TPL=$(find "$HOME/.claude/plugins/cache" -path "*/claude-skills/*/templates/research" -type d 2>/dev/null | sort -rV | head -1)
[ -z "$_TPL" ] && _TPL="templates/research"
```

The `sort -rV | head -1` picks the highest installed version when multiple versions coexist.

---

## Output Paths (Project-Relative)

Commands write files relative to the user's working directory, unless `$BASE_DIR` is set:

| Command group | Output path |
|---------------|-------------|
| `/new-research` | `notes/<domain>/` |
| `/career-*` | `career/<subfolder>/` |
| `/findjob` | `career/job-search/findjob/findjob-YYYY-MM-DD.md` + `jobs.db` |
| `/wiki-*` | `wiki/compiled/` |
| `/apt`, `/apt-watch` | `reports/` |
| `/invest` | `reports/finance/investment-report-YYYY-MM-DD.md` |
| `/newsletter` | `notes/newsletters/newsletter-{label-slug}-YYYY-MM-DD.md` |
| `/scan` | `$SCAN_OUTPUT_DIR/$TARGET_FILENAME` (default: `00_INBOX/index.md`) |
| `/image-gen` | `notes/image-gen/` (or `--output`) |

### BASE_DIR Support

If the `BASE_DIR` environment variable is set, all output paths above are prefixed with `$BASE_DIR/`. Commands use this pattern:

```
output_path = ${BASE_DIR:+$BASE_DIR/}reports/apt-<region>-<YYYYMM>.md
```

Users configure this in `~/.claude/settings.local.json`:
```json
{ "env": { "BASE_DIR": "/home/user/my-research" } }
```

When adding a new file-generating command, apply the same `${BASE_DIR:+$BASE_DIR/}` prefix to all output paths.

Do not introduce `20_AREAS/`, `TEMPLATES/`, or `WIKI/` (old PARA paths) — they were removed intentionally.

---

## Adding a New Command

1. Create `commands/<name>.md`. First line = description.
2. If the command needs a script, add `scripts/<name>.py` or `.sh` and use the plugin-cache resolution pattern.
3. Add the command to the category table in `commands/cmds.md`.
4. If the command produces files, document the output path in this file.

## Adding a New Skill

1. Create `skills/<name>/SKILL.md` with the required frontmatter.
2. Write a comprehensive `description:` — list every trigger phrase and file extension.
3. Supporting scripts go in `skills/<name>/scripts/`. Reference them with relative paths from within the skill instructions.

## Releasing a New Version

1. Bump `version` in `.claude-plugin/plugin.json`.
2. Bump the same version string in `.claude-plugin/marketplace.json` (under `plugins[0].version`).
3. Update the version badge and command/skill counts in `README.md`.
4. Add a `## [X.Y.Z] — YYYY-MM-DD` entry to `CHANGELOG.md`.
5. Commit, tag, and push. GitHub release tags are used for pinned installs.
