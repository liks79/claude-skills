---
name: gemini
description: "Use this skill when the user wants to interact with Google Gemini AI via the Gemini CLI. Triggers include: asking Gemini a question, using Gemini for code review, summarizing content with Gemini, comparing Claude vs Gemini responses, or running any gemini CLI command. Also use when the user says 'ask Gemini', 'use Gemini CLI', or '/gemini'."
---

# Antigravity CLI (agy) Skill

Antigravity CLI (`agy`) replaces the legacy `gemini` CLI. It is a multi-model AI coding assistant that supports Gemini, Claude, and GPT models via a unified interface.

## Quick Reference

| Purpose | Command |
|------|------|
| Simple question (non-interactive) | `agy -p "question"` |
| Ask about file contents | `cat file.md \| agy -p "summarize this"` |
| Code review | `cat file.py \| agy -p "review this code"` |
| Interactive mode | `agy` (interactive, requires TTY) |
| Specify model | `agy --model "Gemini 3.1 Pro (High)" -p "question"` |
| Continue last conversation | `agy -c -p "follow-up question"` |

## Non-Interactive (Headless) Mode

Use the `-p` / `--print` flag to get a single response. Use this mode when running inside a Claude Code session.

```bash
# Basic question
agy -p "Explain the difference between Terraform and Ansible"

# stdin pipe + prompt
cat report.md | agy -p "Summarize this report in Korean"

# Specify model
agy --model "Gemini 3.1 Pro (High)" -p "Complex architecture design question"
```

## Stdin Pipe Pattern

```bash
# Summarize a markdown document
cat notes/devops/cicd-tools-comparison-2026.md | agy -p "Summarize into 5 key points"

# Code review of diff
git diff | agy -p "Review these changes. Point out any potential issues."

# Combine multiple files and ask
cat file1.md file2.md | agy -p "Analyze the commonalities and differences between the two documents"
```

## Available Models

| Model Name | Notes |
|-----------|-------|
| `Gemini 3.5 Flash (Medium)` | Default — fast, balanced |
| `Gemini 3.5 Flash (High)` | Higher quality Gemini Flash |
| `Gemini 3.5 Flash (Low)` | Fastest Gemini Flash |
| `Gemini 3.1 Pro (Low)` | Gemini Pro, lower quota |
| `Gemini 3.1 Pro (High)` | Gemini Pro, higher quality |
| `Claude Sonnet 4.6 (Thinking)` | Claude via agy |
| `Claude Opus 4.6 (Thinking)` | Claude Opus via agy |
| `GPT-OSS 120B (Medium)` | Open-source GPT via agy |

Run `agy models` to get the latest list.

## Notes

- **Interactive mode** (`agy` alone) requires a TTY and cannot be run directly from Claude Code — always use the `-p` flag
- Model names contain spaces; always quote them: `--model "Gemini 3.5 Flash (High)"`
- For long responses, pipe to `| head -100` or save to `> output.md`
- Authentication is managed by `agy` itself (stored in `~/.gemini/antigravity-cli/`)
- The legacy `gemini` CLI (Google official) is no longer used — use `agy` exclusively
