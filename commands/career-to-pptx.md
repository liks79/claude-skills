Use the career-researcher agent to convert a career markdown file to PowerPoint: $ARGUMENTS

Input: `career/<subfolder>/<filename>.md`

## Procedure

1. **Read the file** — load the full content of the specified markdown file using the Read tool

2. **Slide mapping** — markdown structure → slide conversion rules:

   | Markdown element | Slide conversion |
   |-----------------|-----------------|
   | `# Title` | Cover slide title |
   | `**Date** / **Area** / **Status**` | Cover slide subtitle metadata |
   | `## Summary` | Executive Summary slide |
   | `## <Section>` | One section slide per heading |
   | `\| table \|` | Table slide (pptx table) |
   | `## References` | Sources slide (last) |

3. **Write PPTX generation script** — using `python-pptx`:

   ```python
   from pptx import Presentation
   from pptx.util import Inches, Pt, Emu
   from pptx.dml.color import RGBColor
   from pptx.enum.text import PP_ALIGN

   prs = Presentation()
   prs.slide_width  = Inches(13.33)
   prs.slide_height = Inches(7.5)
   ```

   **Slide style guide**:
   - Background: white (`FFFFFF`)
   - Title font: 28pt Bold, navy (`1F3864`)
   - Body font: 18pt, black (`222222`)
   - Bullet items: max 6 per slide
   - Table: header background navy (`1F3864`), font white

4. **Save** — output `.pptx` to the same path as the source markdown:
   - Input: `career/companies/toss.md`
   - Output: `career/companies/toss.pptx`

5. **Execute**:
   ```bash
   uv run python <temp script path>
   ```
   Delete the script file after execution (one-time use).

6. After generation, notify the user of the file path.

## Dependency Check

If `python-pptx` is not installed, install it first:
```bash
uv add python-pptx
```
