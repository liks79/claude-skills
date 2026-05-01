Create a new research note for the topic: $ARGUMENTS

1. **Detect career topics** — If the topic contains any of the following keywords, delegate to the `career-researcher` agent:
   - job search, career change, resume, interview, salary, company analysis, recruiting, job hunting

2. **Select template** — Apply the auto-selection logic from `TEMPLATES/research/_registry.md`:

   | Topic keywords | Template |
   |----------------|----------|
   | "comparison", "vs", "selection", "evaluation" | T4 Comparative Evaluation |
   | "market", "trend", "landscape" | T3 Market Analysis |
   | "strategy", "roadmap", "plan" | T5 Strategic Roadmap |
   | "architecture", "deep dive", "analysis" | T2 Tech Deep-Dive |
   | Other / default | T1 Executive Brief |
   | User specifies `Template N` | Apply that template first |

   - If no `depth:` parameter is provided, apply `standard`
   - Load the selected template file using the Read tool and use it as the scaffold

3. **Determine area**:
   - AI/ML → `20_AREAS/ai-ml/`
   - Web development → `20_AREAS/web-trends/`
   - Security → `20_AREAS/security/`
   - DevOps/Infrastructure → `20_AREAS/devops/`
   - Claude Code → `20_AREAS/claude-code/`
   - Tools/Config → `20_AREAS/tools/`

4. **Create file** — Write the file based on the selected template:
   - Path: `20_AREAS/<domain>/<topic-kebab-case>-YYYY.md`
   - Adjust section depth based on the frontmatter `depth` value
   - Remove `<!-- depth: ... -->` comments from the final file

5. Notify the user of the save path, selected template (T1–T5), and depth.
