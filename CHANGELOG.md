# Changelog

All notable changes to this project will be documented in this file.

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
