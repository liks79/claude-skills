Ship current changes: create branch, commit, push, and open PR. $ARGUMENTS

---

## Procedure

### Step 1 — Assess current state

Run the following commands **in parallel**:

```bash
git status
git diff
git log --oneline -5
```

Summarize the list of changed files and the diff content.
If there are no changes, notify the user and stop.

---

### Step 2 — Determine branch name and commit message

#### Branch naming rules (per CLAUDE.md)
- Must start with `claude/`
- Format: `claude/<type>-<short-description>` (kebab-case, English)
- Examples: `claude/feat-add-ship-command`, `claude/research-databricks-sa`

#### Commit message rules (Conventional Commits)
```
<type>(<scope>): <subject>
```

| type | Purpose |
|------|---------|
| feat | New feature, tool, or script |
| fix | Bug fix |
| research | Research notes, analysis results |
| experiment | Experimental code, PoC |
| docs | README, documentation |
| refactor | Structural improvement without functional change |
| chore | Dependencies, config, build |
| ci | CI/CD changes |

Scopes: `ai-ml` · `web-trends` · `security` · `devops` · `claude-code` · `career` · `root`

If `$ARGUMENTS` is provided, use it as a hint for the branch name and commit message.
If `$ARGUMENTS` is not provided, infer the most appropriate type/scope/subject from the diff.

Show the proposed branch name and commit message to the user and **get approval**.
If the user requests changes, apply them and confirm again.

---

### Step 3 — Create branch and stage files

If the current branch already starts with `claude/`, use that branch without creating a new one.
Otherwise, create a new branch with the approved name:

```bash
git checkout -b <branch-name>
```

Stage the changed files (exclude sensitive files like .env, credentials, etc.):

```bash
git add <list files individually — do not use git add -A>
```

---

### Step 4 — Commit

Commit with the approved message. Use the HEREDOC format:

```bash
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

If the commit fails (e.g., pre-commit hook), identify the cause, fix it, and retry with a **new commit** (do not use --amend).

---

### Step 5 — Push

```bash
git push -u origin <branch-name>
```

---

### Step 6 — Create PR

Create a PR using `gh pr create`. Set the reviewer to the value of `git config claude.reviewer` (omit if not set):

```bash
REVIEWER=$(git config --get claude.reviewer 2>/dev/null || echo "")
gh pr create \
  --title "<type>(<scope>): <subject>" \
  ${REVIEWER:+--reviewer "$REVIEWER"} \
  --body "$(cat <<'EOF'
## Summary

- <change bullet 1>
- <change bullet 2>

## Changes

<List of changed files with a brief description of each file's role>

## Test plan

- [ ] Review the content of changed files
- [ ] (If applicable) Confirm `uv run pytest` passes

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Notify the user of the PR URL.

---

### Step 7 — Done

Present the following information to the user:

- **Branch**: `<branch-name>`
- **Commit**: `<commit hash> — <message>`
- **PR**: `<PR URL>`
- **Reviewer**: value of `git config claude.reviewer` (omit if not set)

Suggest any additional steps if needed.
