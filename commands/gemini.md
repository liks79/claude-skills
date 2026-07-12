Ask questions or perform tasks using Antigravity CLI (agy) with Google Gemini AI. $ARGUMENTS

---

## Usage

```
/gemini <question or prompt>
/gemini <question> --model "Gemini 3.1 Pro (High)"
/gemini <question> --file <file_path>
/gemini --diff          Code review of current git diff using Gemini
/gemini --summary <file_path>   Summarize file contents
```

## Options

| Option | Description |
|--------|-------------|
| `--model <name>` | Specify model (default: `Gemini 3.5 Flash (Medium)`) |
| `--file <path>` | Pass file contents along with the prompt |
| `--diff` | Code review of `git diff` output using Gemini |
| `--summary <path>` | Summarize a file |

## Available Models

| Model | Notes |
|-------|-------|
| `Gemini 3.5 Flash (Medium)` | Default — fast, balanced |
| `Gemini 3.5 Flash (High)` | Higher quality Gemini Flash |
| `Gemini 3.5 Flash (Low)` | Fastest Gemini Flash |
| `Gemini 3.1 Pro (Low)` | Gemini Pro, lower quota |
| `Gemini 3.1 Pro (High)` | Gemini Pro, higher quality |
| `Claude Sonnet 4.6 (Thinking)` | Claude via agy |
| `Claude Opus 4.6 (Thinking)` | Claude Opus via agy |
| `GPT-OSS 120B (Medium)` | Open-source GPT via agy |

## Procedure

### Step 1 — Parse Arguments

Analyze `$ARGUMENTS`:

- If `--diff` flag is present → code review mode, passing git diff via stdin
- If `--summary <path>` is present → file summarization mode
- If `--file <path>` is present → pass file contents along with the prompt
- If `--model <name>` is present → add `--model "<name>"` flag; otherwise omit (agy defaults to `Gemini 3.5 Flash (Medium)`)
- Remaining text → use as the prompt

### Step 2 — Execute Command

**General question:**
```bash
agy -p "<prompt>"
```

**Including file contents:**
```bash
cat "<file_path>" | agy -p "<prompt>"
```

**git diff code review:**
```bash
git diff | agy -p "Please review these code changes. List any potential bugs, improvements, and code quality issues by category."
```

**File summarization:**
```bash
cat "<file_path>" | agy -p "Summarize the key content of this document. Include main points, conclusions, and action items."
```

**Specify model:**
```bash
agy --model "<model-name>" -p "<prompt>"
```

### Step 3 — Display Results

Show the response to the user as-is.
If the response is long, also provide a brief summary of the key points.

### Step 4 — Error Handling

| Error | Response |
|-------|----------|
| Auth / login error | Run `agy` interactively in a terminal to complete login |
| No response / timeout | Simplify the prompt and retry |
| File not found | Ask user to recheck the file path |
| Unknown model name | Run `agy models` to list valid names and pick the closest match |
