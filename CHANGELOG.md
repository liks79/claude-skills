# Changelog

All notable changes to this project will be documented in this file.

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
