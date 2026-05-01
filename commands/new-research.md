Create a new research note for the topic: $ARGUMENTS

1. **Detect career topics** — If the topic contains any of the following keywords, delegate to the `career-researcher` agent:
   - job search, career change, resume, interview, salary, company analysis, recruiting, job hunting

2. **Select template** — Apply the auto-selection logic below:

   | Topic keywords | Template |
   |----------------|----------|
   | "comparison", "vs", "selection", "evaluation" | T4 Comparative Evaluation |
   | "market", "trend", "landscape" | T3 Market Analysis |
   | "strategy", "roadmap", "plan" | T5 Strategic Roadmap |
   | "architecture", "deep dive", "analysis" | T2 Tech Deep-Dive |
   | Other / default | T1 Executive Brief |
   | User specifies `Template N` | Apply that template first |

   - If no `depth:` parameter is provided, apply `standard`
   - Resolve the templates directory and load the selected template as the scaffold:
     ```bash
     _TPL=$(find "$HOME/.claude/plugins/cache" -path "*/claude-skills/*/templates/research" -type d 2>/dev/null | sort -rV | head -1)
     [ -z "$_TPL" ] && _TPL="templates/research"
     ```
     Then Read `$_TPL/T<N>-<name>.md` (e.g. `$_TPL/T1-executive-brief.md`)

3. **Determine area**:
   - AI/ML → `notes/ai-ml/`
   - Web development → `notes/web-trends/`
   - Security → `notes/security/`
   - DevOps/Infrastructure → `notes/devops/`
   - Claude Code → `notes/claude-code/`
   - Tools/Config → `notes/tools/`

4. **Create file** — Write the file based on the selected template:
   - Path: `${BASE_DIR:+$BASE_DIR/}notes/<domain>/<topic-kebab-case>-YYYY.md`
   - If `$BASE_DIR` is not set, path is relative to the current working directory
   - Adjust section depth based on the frontmatter `depth` value
   - Remove `<!-- depth: ... -->` comments from the final file

5. Notify the user of the save path, selected template (T1–T5), and depth.
