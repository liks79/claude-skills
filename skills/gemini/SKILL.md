---
name: gemini
description: "Use this skill when the user wants to interact with Google Gemini AI via the Gemini CLI. Triggers include: asking Gemini a question, using Gemini for code review, summarizing content with Gemini, comparing Claude vs Gemini responses, or running any gemini CLI command. Also use when the user says 'ask Gemini', 'use Gemini CLI', or '/gemini'."
---

# Gemini CLI Skill

Gemini CLI (`gemini`) must be installed and available in PATH. Install via `brew install gemini-cli` or see https://github.com/google-gemini/gemini-cli.

## Quick Reference

| Purpose | Command |
|------|------|
| Simple question (non-interactive) | `gemini -p "question"` |
| Ask about file contents | `cat file.md \| gemini -p "summarize this"` |
| Code review | `cat file.py \| gemini -p "review this code"` |
| Interactive mode | `gemini` (interactive, requires TTY) |
| Specify model | `gemini -m gemini-2.5-pro -p "question"` |
| YOLO mode (auto-approve) | `gemini -y -p "question"` |

## Non-Interactive (Headless) Mode

Use the `-p` / `--prompt` flag to get a single response. Use this mode when running inside a Claude Code session.

```bash
# Basic question
gemini -p "Explain the difference between Terraform and Ansible"

# stdin pipe + prompt
cat report.md | gemini -p "Summarize this report in Korean"

# Direct file path reference
gemini -p "$(cat file.py)" # small files

# Specify model
gemini -m gemini-2.5-pro -p "Complex architecture design question"
```

## Stdin Pipe Pattern

```bash
# Summarize a markdown document
cat notes/devops/cicd-tools-comparison-2026-04.md | gemini -p "Summarize into 5 key points"

# Code review of diff
git diff | gemini -p "Review these changes. Point out any potential issues."

# Combine multiple files and ask
cat file1.md file2.md | gemini -p "Analyze the commonalities and differences between the two documents"
```

## Model Options

| Model ID | Characteristics |
|---------|------|
| `gemini-2.5-flash` (default) | Fast, general purpose |
| `gemini-2.5-pro` | High quality, complex reasoning |
| `gemini-2.0-flash` | Lightweight, fast responses |

## Notes

- **Interactive mode** (`gemini` alone) requires a TTY and cannot be run directly from Claude Code — always use the `-p` flag
- For long responses, pipe to `| head -100` or save to `> output.md`
- API key is set via the `GEMINI_API_KEY` environment variable in `settings.local.json`
