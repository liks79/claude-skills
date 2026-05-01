# Claude Skills — Claude Code Plugin

A curated collection of slash commands, skills, and agents for [Claude Code](https://claude.ai/code).

**22 commands · 2 skills · 1 agent**

---

## Installation

### Option 1: Via Marketplace (Recommended)

Add this repo as a marketplace, then install the plugin:

```
/plugin marketplace add github:liks79/claude-skills
/plugin install claude-skills@liks79-skills
```

### Option 2: Direct Install

```bash
claude plugin install github:liks79/claude-skills --scope user
```

### Option 3: Enable in `settings.json`

After adding the marketplace, add to your `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "liks79-skills": {
      "source": {
        "source": "github",
        "repo": "liks79/claude-skills"
      }
    }
  },
  "enabledPlugins": {
    "claude-skills@liks79-skills": true
  }
}
```

---

## Commands

### Research & Knowledge

| Command | Description |
|---------|-------------|
| `/new-research <topic>` | Create a new research note with auto-selected template (T1–T5) |
| `/apply-research-template <file>` | Restructure an existing markdown file into a research template |
| `/wiki-ingest <file-or-url>` | Ingest a file, web URL, or YouTube video into the LLM wiki |
| `/wiki-query <question>` | Search and synthesize answers from the wiki |
| `/wiki-lint` | Validate wiki consistency (broken links, orphaned pages, stale entries) |

### Career Development

| Command | Description |
|---------|-------------|
| `/career-company-analysis <company>` | Research and analyze a company (tech stack, culture, interview, compensation) |
| `/career-job-analysis <URL>` | Analyze a job posting with gap analysis and resume keywords |
| `/career-interview-prep <company> <role>` | Generate a structured interview preparation guide |
| `/career-salary-research <role> [region] [years]` | Research market salary data with distribution tables |
| `/career-to-pptx <md-path>` | Convert a career markdown file to PowerPoint |

### Git & GitHub

| Command | Description |
|---------|-------------|
| `/ship [hint]` | Full git workflow: branch → commit → push → PR |
| `/github-urls [N]` | Show GitHub URLs for recently changed files |
| `/grass-tracker [username]` | Show GitHub contribution graph status |

### AI Tools

| Command | Description |
|---------|-------------|
| `/gemini <prompt>` | Ask questions or run tasks via Google Gemini CLI |
| `/image-gen <prompt>` | Generate images via Google Gemini API (NanoBanana / Imagen) |

### Productivity

| Command | Description |
|---------|-------------|
| `/email-summary [days]` | Classify and summarize Gmail by importance |
| `/cal <event>` | Add or view Google Calendar events (natural language) |
| `/presign <file> [hours]` | Upload to Cloudflare R2 / AWS S3 and return a presigned URL |
| `/recent [N]` | List the N most recently modified files |

### Korea Real Estate

| Command | Description |
|---------|-------------|
| `/apt <region>` | Seoul/metro apartment price report via MOLIT API |
| `/apt-watch <complex>` | Track specific apartment complex listings on Naver Real Estate |

### Meta

| Command | Description |
|---------|-------------|
| `/cmds` | List all available commands from this plugin |

---

## Skills

Skills are loaded automatically by Claude Code when relevant.

| Skill | Trigger | Description |
|-------|---------|-------------|
| `gemini` | "ask Gemini", "use Gemini CLI", `/gemini` | Google Gemini CLI wrapper for Q&A, code review, file summarization |
| `pptx` | Any `.pptx` file, "deck", "slides", "presentation" | Full PowerPoint workflow: read, edit, create from scratch, QA |

---

## Agent

| Agent | Description |
|-------|-------------|
| `career-researcher` | Sub-agent dedicated to career research. Auto-delegated by `/new-research` for career topics and all `/career-*` commands. Operates exclusively within `20_AREAS/career/`. |

---

## Configuration

Some commands require API keys or CLI tools. Add to `~/.claude/settings.local.json`:

```json
{
  "env": {
    "GEMINI_API_KEY": "your-gemini-api-key",
    "DATA_GO_KR_API_KEY": "your-data-go-kr-key",
    "STORAGE_PROVIDER": "r2",
    "R2_ACCOUNT_ID": "...",
    "R2_ACCESS_KEY_ID": "...",
    "R2_SECRET_ACCESS_KEY": "...",
    "R2_BUCKET_NAME": "presign-shared"
  }
}
```

### External CLI Requirements

| Command(s) | Requires |
|------------|----------|
| `/gemini`, `/image-gen` | [Gemini CLI](https://github.com/google-gemini/gemini-cli) + `GEMINI_API_KEY` |
| `/ship`, `/github-urls`, `/grass-tracker` | [GitHub CLI (`gh`)](https://cli.github.com/) |
| `/cal` | `gws` CLI (Google Workspace CLI) |
| `/apt`, `/apt-watch`, `/presign`, `/email-summary`, `/image-gen` | [`uv`](https://docs.astral.sh/uv/) |
| `/email-summary` | Gmail MCP (via Claude Code Gmail integration) |

---

## Note: Project-Structure-Dependent Commands

The following commands write to a **PARA-structured knowledge base** (`20_AREAS/`, `TEMPLATES/`, `WIKI/`).
They work best when your project follows that directory structure:

- `/new-research`, `/apply-research-template`
- All `/career-*` commands
- All `/wiki-*` commands
- `/apt`, `/apt-watch`

---

## License

MIT — see [LICENSE](LICENSE)
