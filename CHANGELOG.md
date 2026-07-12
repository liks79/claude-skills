# Changelog

All notable changes to this project will be documented in this file.

---

## [1.5.9] — 2026-07-11

### Changed
- **`gemini` skill/command**: Migrated from the legacy `gemini` CLI to [Antigravity CLI (`agy`)](https://github.com/nicholasgasior/antigravity-cli), a multi-model assistant supporting Gemini, Claude, and GPT models via a unified interface. `-p`/`-m` flags replaced with `--print`/`--model`; model names are now quoted strings (e.g. `"Gemini 3.1 Pro (High)"`) instead of IDs. Authentication is handled by `agy` itself — no `GEMINI_API_KEY` needed for `/gemini` (still required for `/image-gen`). Synced from `staytuned-research-mono` commit `87130b7` (#192).
- **`README.md`**: Updated the `gemini` skill section, command table, and required-tools table to reflect the `agy` migration; clarified that `GEMINI_API_KEY` is only needed for `/image-gen`.

## [1.5.8] — 2026-06-14

### Fixed
- **`templates/research/T2-tech-deep-dive.md`**: Replaced `\n` with `<br/>` in a Mermaid flowchart node label. `\n` renders as the literal two-character sequence `\n` in Quartz v5 and Obsidian instead of a line break. Synced from `staytuned-research-mono` commit `ba55723` (#178).

### Changed
- **`/new-research`**: Added explicit Mermaid line-break rule to Step 4 — always use `<br/>` inside node labels, never `\n`.
- **`README.md`**: Added Mermaid Rendering Rules section to the Research Templates documentation.

---

## [1.5.7] — 2026-06-14

### Changed
- **Templates T1–T5**: Replaced image-based agent profile with emoji byline `🧭 Researched by StayTuned-CC Agent @liveloop.app` (HTML div, no external image dependency). Synced from `staytuned-research-mono` commits `2dc19bc` (#175) and `c9cc213` (#176).
- **`/new-research`**: Updated Step 4 "Byline" note to document the new emoji-based `<div>` format.
- **`README.md`**: Added byline documentation to Research Templates section.

---

## [1.5.6] — 2026-06-12

### Changed
- **`/new-research`**: Added Markdown table formatting rule to Step 4 — always use standard `| col |` tables; never use ASCII box-drawing characters (┌ ├ └ etc.) outside fenced code blocks. Synced from `staytuned-research-mono` commit `0ba73aa`.
- **`templates/research/_registry.md`**: Added `/invest` → T6 and `/newsletter` → T7 command mappings to the Command × Template table. Updated T6/T7 classification labels to match upstream (INVESTMENT PORTFOLIO REPORT, NEWSLETTER INTELLIGENCE DIGEST).
- **`README.md`**: Added dedicated `/share` section with pdf-creator plugin install instructions, environment variable table, and error handling reference. Added `daymade-skills/pdf-creator` to External CLI Requirements.

---

## [1.5.5] — 2026-06-08

### Fixed
- **Installation docs**: Clarified two-step install requirement in README to prevent `Plugin not found in any configured marketplace` error. Added a Note block explaining that `liks79/claude-skills` is a GitHub repo path (used for `marketplace add`), not a plugin identifier — users must run `marketplace add` before `plugin install claude-skills@liks79-skills`. Added inline comments to the CLI code block marking each step.

---

## [1.5.4] — 2026-06-08

### Fixed
- **Installation**: Option 2 in README used `claude plugin install liks79/claude-skills --scope user` which fails with `Plugin not found in any configured marketplace` because `liks79` is not a built-in marketplace alias. Replaced with the correct two-step CLI flow: `claude plugin marketplace add liks79/claude-skills` → `claude plugin install claude-skills@liks79-skills --scope user`.

---

## [1.5.3] — 2026-06-07

### Added (`/add-tags`)
- New command `/add-tags` — Obsidian vault tag manager synced from `staytuned-research-mono`
- `scripts/add-tags/add_tags.sh`: Phase 1 (scan) and Phase 3 (build Tag Dictionary) shell orchestrator; uses `BASH_SOURCE[0]`-based `SCRIPT_DIR` for plugin-cache compatibility
- `scripts/add-tags/lib/scanner.py`: Phase 1 vault scanner with four scan modes (paths/delta/incremental/full) and incremental tag index update (O(changed_files))
- `scripts/add-tags/lib/builder.py`: Phase 3 Tag_Dictionary.md builder; Quartz v5 compatible `[tag](tags/tagname)` links
- `scripts/add-tags/lib/tagger.py`: standalone Claude API tagger (Phase 2 via Anthropic SDK, optional)
- `scripts/add-tags/list_untagged.py`: JSON helper that outputs untagged files + existing vocab for Claude Code native tagging (no API key required)
- `commands/add-tags.md`: command procedure with plugin-cache path resolution (`find ~/.claude/plugins/cache`)
- `README.md`: `/add-tags` section with usage examples, scan mode table, environment variables, plugin config example
- `CLAUDE.md`: output path entry for `/add-tags`

---

## [1.5.2] — 2026-06-06

### Changed (`/scan`)
- `build_index.py`: frontmatter `title:` now uses the **output directory name** (e.g. `00_INBOX`) instead of hardcoded "Research Index" — Quartz v5 explorer sorts pages by frontmatter title, so the folder name keeps the index file grouped with its siblings rather than appearing under "R"
- `build_index.py`: remove the `# Research Index` H1 heading from the output (redundant now that the title is in frontmatter)
- `config.sh`: add default `SCAN_EXCLUDE_PATTERNS` — skips files generated by other claude-skills commands (`findjob/`, `invest-report-`, `investment-report-`, `apt-watch-`, `newsletter-`, `resume-portfolio/`); overridable via env var
- `commands/scan.md`: update Quartz v5 compatibility note — remove "Obsidian and" from header, update emoji tag description to reference OFM regex (`\p{L}` only, no `\p{Emoji}`)
- `commands/scan.md`: fix `TARGET_FILENAME` default in env var table (`recent_index.md` → `index.md`)
- `README.md`: sync all `/scan` documentation — compatibility note, `SCAN_EXCLUDE_PATTERNS` default, frontmatter title behavior, plugin config example

---

## [1.5.1] — 2026-06-06

### Changed (`/scan`)
- `config.sh`: default output filename changed from `recent_index.md` → `index.md` (matches Quartz page slug convention)
- `build_index.py`: add `title: Research Index` to YAML frontmatter (required by Quartz v5 article-title component)
- `build_index.py`: revert emoji tag handling — always emit `#tag` notation (Obsidian renders emoji tags correctly; Quartz v5 shows them as plain text, which is acceptable)
- `build_index.py`: remove `&nbsp;` HTML entities from tag cloud — use `·` separator and plain spaces (Obsidian does not render HTML entities in regular markdown paragraphs)
- `extract_meta.py`: strip trailing punctuation from tags (e.g. a comma left by `"tag1, tag2"` YAML) to prevent malformed tag links

---

## [1.5.0] — 2026-06-06

### Added
- `/scan` command — vault research index builder ported from `staytuned-research-mono`
  - `scripts/scan/scan.sh` — main entry point with plugin cache-aware `SCRIPT_DIR` resolution
  - `scripts/scan/lib/config.sh` — shared defaults (all overridable via env vars)
  - `scripts/scan/lib/extract_meta.py` — YAML frontmatter + H1 title + tag parser (stdlib only)
  - `scripts/scan/lib/update_cache.py` — incremental metadata cache (only re-parses changed files)
  - `scripts/scan/lib/build_index.py` — Markdown index generator with year×month matrix, tag cloud, and document list
- `commands/scan.md` — command definition with plugin-cache path resolution pattern
- README: `/scan` full documentation section (usage, env vars, plugin config, Quartz v5.0 compatibility notes)

### Notes
- `/scan` was developed and tested with **Quartz v5.0+**. Link format uses standard `[title](path)` Markdown links (not `[[wikilinks]]`) to avoid the `|` table-cell parsing issue in Quartz v5's remark pipeline. Tag links fall back to `` `code span` `` for emoji-prefixed tags that Quartz v5 OFM regex (`\p{L}` only, no `\p{Emoji}`) cannot handle.

---

## [1.4.0] — 2026-05-31

### Added
- `scripts/findjob/link_validator.py` — parallel HTTP link validator (20 workers, 12 s timeout); removes 404/410 responses and jobs with "position closed" phrases; transient errors (429, 5xx, timeouts) treated as valid to avoid false removals
- `scripts/findjob/parsers/linkedin.py` — LinkedIn guest API supplemental search (undocumented public endpoint, no auth required); deduplicates against primary career-page results, prefixes job IDs with `li_`
- `scripts/findjob/run.py` — 4-phase orchestration: Phase 1 (primary parsers) → Phase 2 (link validation) → Phase 3 (LinkedIn supplemental) → Phase 4 (DB upsert)
- `commands/findjob.md` — `enable_link_validation` and `enable_linkedin_search` YAML config flags
- `--skip-validation` CLI flag for faster dry-run scans

### Changed
- Google parser: rewrote from JSON-LD to AF_initDataCallback JS data block extraction — now reliably returns results where the SPA-rendered JSON-LD approach returned 0
- Microsoft parser: replaced GCS API + HTML scrape with Eightfold PCSX `/api/pcsx/search` API (session cookie obtained by visiting homepage first) — now reliably returns Korea results
- AWS parser: use `id_icims` (stable numeric ID) and `job_path` (slug URL) instead of UUID-style `id` — UUID-based URLs returned 404 on link validation
- `db_manager.py` — added `mark_removed_force()` for intentional empty-list removal (link validation case); `mark_removed()` retains its empty-list safety guard

---

## [1.3.1] — 2026-05-28

### Added
- `/findjob list` subcommand — display current configuration (locations, positions, score threshold, company table with URL-decoded location filters) without running any network scan
- README: Plugin configuration guide for `FINDJOB_CONFIG_FILE` — how to customize config when installed as a plugin

---

## [1.3.0] — 2026-05-28

### Added
- `/findjob` command — scan 11 company career sites (AWS, Google, Microsoft, Anthropic, OpenAI, Databricks, Datadog, Cloudflare, Palantir, Redis, Coupang) for matching job openings
- `scripts/findjob/` Python package with 11 company-specific parsers (Greenhouse, Ashby HQ, SmartRecruiters, custom APIs, HTML scraping)
- `scripts/findjob_run.py` — launcher wrapper for the findjob package
- SQLite-backed history tracking: first_seen / last_seen / active / removed job lifecycle
- Relevance scoring engine with stemming, role alias patterns, and abbreviation expansion

### Fixed
- AWS parser: `normalized_location` returned as `str` not `list` — was rendering as individual characters (e.g. `S, e, o, u, l`)
- Report date truncation: non-ISO dates (e.g. `May 21, 2026`) were incorrectly sliced to 10 chars

---

## [1.2.0] — 2026-05-25

### Added
- `/newsletter` command — fetch Gmail messages by label, classify by topic (AI/BigTech/Startup/Tools/Other), and generate a premium intelligence digest report
- `newsletter` skill — AI curation logic for Gmail newsletter content, powers `/newsletter`
- `scripts/gmail_fetch_newsletter.py` — fetch Gmail messages via gws CLI with body decoding and link extraction
- `templates/research/T7-newsletter-curation.md` — T7 Newsletter Intelligence Digest template (Mermaid mindmap, pie chart, Gantt timeline, source index)

### Changed
- `plugin.json` / `marketplace.json` — added keywords: `finance`, `investment`, `newsletter`, `gmail`

---

## [1.1.1] — 2026-05-25

### Changed
- Version bump to align plugin.json and marketplace.json

---

## [1.1.0] — 2026-05-25

### Added
- `/email-archive` command — fetch unread Gmail inbox messages, assign labels via AI, and archive in bulk
- `/invest` command — read Google Sheets portfolio via gws CLI, fetch live market data, generate T6 investment report
- `/share` command — convert research markdown to PDF and upload to Cloudflare R2 with presigned URL
- `invest` skill — portfolio analytics: parse holdings, compute aggregates, pre-render Mermaid chart data
- `templates/research/T6-investment-report.md` — T6 Investment Report template

---

## [1.0.0] — 2026-05-24

### Added
- Initial release with 22 slash commands and 2 skills
- Commands: `new-research`, `apply-research-template`, `wiki-ingest`, `wiki-query`, `wiki-lint`, `career-company-analysis`, `career-job-analysis`, `career-interview-prep`, `career-salary-research`, `career-to-pptx`, `ship`, `github-urls`, `grass-tracker`, `gemini`, `image-gen`, `email-summary`, `cal`, `presign`, `recent`, `apt`, `apt-watch`, `cmds`
- Skills: `gemini` (Gemini CLI wrapper), `pptx` (PowerPoint toolkit)
- Agent: `career-researcher`
- Scripts: `apt_report.py`, `apt_watch.py`, `email_summary.py`, `generate_image.py`, `github-urls.sh`, `presign.py`, `recent.sh`
- Templates: T1 Executive Brief, T2 Tech Deep-Dive, T3 Market Analysis, T4 Comparative Evaluation, T5 Strategic Roadmap
