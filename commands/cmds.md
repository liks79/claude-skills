List all available custom commands in this repo.

---

## Procedure

Dynamically read and display all `.md` files in the `.claude/commands/` directory.

1. Collect the file list using Bash:
   ```bash
   _D=$(find "$HOME/.claude/plugins/cache" -path "*/claude-skills/*/commands" -type d 2>/dev/null | sort -rV | head -1)
   [ -z "$_D" ] && _D=".claude/commands"
   ls "$_D"/*.md 2>/dev/null | sort
   ```

2. For each file:
   - The command name is the filename with `.md` removed (e.g., `ship.md` → `/ship`)
   - Use the **first line** of the file as the description

3. Categorize and display the commands under the following categories:

   | Category | Command prefix or keyword |
   |----------|--------------------------|
   | Research | `new-research`, `apply-research-template` |
   | Career | `career-*` |
   | Git / GitHub | `ship`, `github-urls`, `grass-tracker` |
   | Wiki | `wiki-*` |
   | AI | `gemini`, `image-gen` |
   | Real Estate | `apt`, `apt-watch` |
   | Utilities | `cal`, `recent`, `email-summary`, `presign` |
   | Meta | `cmds` |

4. Output format:
   ```
   # Available Custom Commands (N)

   ## <Category>
     /<name>   — <first line>

   ...
   ```
