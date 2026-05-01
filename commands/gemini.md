Ask questions or perform tasks using Gemini CLI with Google Gemini AI. $ARGUMENTS

---

## Usage

```
/gemini <question or prompt>
/gemini <question> --model gemini-2.5-pro
/gemini <question> --file <file_path>
/gemini --diff          Code review of current git diff using Gemini
/gemini --summary <file_path>   Summarize file contents
```

## Options

| Option | Description |
|--------|-------------|
| `--model <id>` | Specify model (default: gemini-2.5-flash) |
| `--file <path>` | Pass file contents along with the prompt |
| `--diff` | Code review of `git diff` output using Gemini |
| `--summary <path>` | Summarize a file |

## Procedure

### Step 1 — Parse Arguments

Analyze `$ARGUMENTS`:

- If `--diff` flag is present → code review mode, passing git diff via stdin
- If `--summary <path>` is present → file summarization mode
- If `--file <path>` is present → pass file contents along with the prompt
- If `--model <id>` is present → add `-m <id>` flag
- Remaining text → use as the prompt

### Step 2 — Execute Command

**General question:**
```bash
gemini -p "<prompt>"
```

**Including file contents:**
```bash
cat "<file_path>" | gemini -p "<prompt>"
```

**git diff code review:**
```bash
git diff | gemini -p "Please review these code changes. List any potential bugs, improvements, and code quality issues by category."
```

**File summarization:**
```bash
cat "<file_path>" | gemini -p "Summarize the key content of this document. Include main points, conclusions, and action items."
```

**Specify model:**
```bash
gemini -m <model-id> -p "<prompt>"
```

### Step 3 — Display Results

Show Gemini's response to the user as-is.
If the response is long, also provide a brief summary of the key points.

### Step 4 — Error Handling

| Error | Response |
|-------|----------|
| `GEMINI_API_KEY` not set | Ask user to add the key to the `env` block in `settings.local.json` |
| No response / timeout | Simplify the prompt and retry |
| File not found | Ask user to recheck the file path |
