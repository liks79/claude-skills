Apply a research template to an existing markdown document: $ARGUMENTS

## Usage

```
/apply-research-template <file-path> [Template N] [depth: <value>] [--inplace]

# Auto-detect template + standard depth
/apply-research-template 20_AREAS/ai-ml/rag-research-2026.md

# Specify template explicitly
/apply-research-template 20_AREAS/devops/k8s-analysis.md Template 2

# Specify template + depth
/apply-research-template 20_AREAS/career/companies/kakao.md Template 3 depth: deep

# Overwrite original file (default: create new file)
/apply-research-template 20_AREAS/ai-ml/rag-research-2026.md --inplace
```

## Procedure

### Step 1 — Parse arguments

Analyze `$ARGUMENTS`:

| Argument | Description | Default |
|----------|-------------|---------|
| `<file-path>` | Target markdown file path (required) | — |
| `Template N` | Template ID to apply (T1–T5) | Auto-detect |
| `depth: <value>` | quick \| standard \| deep \| exhaustive | standard |
| `--inplace` | Flag to overwrite original file | Create new file |

---

### Step 2 — Read source file

Read the target file using the Read tool. If the file does not exist, notify the user and stop.

---

### Step 3 — Auto-detect template (when Template N is not specified)

Read `TEMPLATES/research/_registry.md`, then analyze the file content's keywords and structure to determine the template:

| File content signals | Selected template |
|----------------------|-------------------|
| "comparison", "vs", "evaluation", "score", gap analysis present | **T4** Comparative Evaluation |
| "market", "trend", "landscape", "share", CAGR present | **T3** Market Analysis |
| "roadmap", "phase", "milestone", "Phase", Gantt present | **T5** Strategic Roadmap |
| "architecture", "sequence", "layer", many code blocks | **T2** Tech Deep-Dive |
| Other / unable to determine | **T1** Executive Brief |

Skip this step if the user specified `Template N`.

Show the detected result to the user and **confirm before proceeding**:
```
Detected template: T3 Market Analysis (depth: standard)
File: 20_AREAS/ai-ml/rag-research-2026.md → 20_AREAS/ai-ml/rag-research-2026-T3.md

Proceed? (Specify Template N if you want a different template)
```

---

### Step 4 — Load template

Read the selected template file:

| Template | File path |
|----------|-----------|
| T1 | `TEMPLATES/research/T1-executive-brief.md` |
| T2 | `TEMPLATES/research/T2-tech-deep-dive.md` |
| T3 | `TEMPLATES/research/T3-market-analysis.md` |
| T4 | `TEMPLATES/research/T4-comparative-evaluation.md` |
| T5 | `TEMPLATES/research/T5-strategic-roadmap.md` |

---

### Step 5 — Map content and restructure

Restructure the source file's content into the template structure.

**Mapping principles:**

1. **Preserve first** — Retain existing content as much as possible; reorganize sections
2. **Fill empty sections** — Sections not in the source are left as placeholders with a `<!-- TODO -->` comment
3. **Apply depth** — Read `<!-- depth: ... -->` comments and adjust description depth accordingly
4. **Supplement diagrams** — If the template includes Mermaid diagrams not in the source, add placeholders
5. **Merge frontmatter**:
   - Retain existing tags and metadata from the source
   - Add/update `classification` and `depth` fields from the template
   - Update `updated:` date to today

**Section mapping example (applying T3):**

```
Source "## Summary"                → T3 "## Executive Summary"
Source "## Overview"               → T3 "## Market Overview"
Source "## Competitors" / "Players"→ T3 "## Competitive Landscape"
Source "## Trends"                 → T3 "## Trend Analysis"
Source "## References"             → T3 "## References"
Unmapped sections                  → Placed in Appendix or similar section at the end
```

Remove `<!-- depth: ... -->` comments from the final file.

---

### Step 6 — Save output file

**Without `--inplace` (default)**: Save as a new file
```
Source: <dir>/<filename>.md
Output: <dir>/<filename>-T<N>.md
```

**With `--inplace`**: Overwrite the original file
- Show the first 50 lines of the original content and ask for final confirmation before overwriting

---

### Step 7 — Print conversion summary

```
✅ Template applied successfully

Source:   <source-path>
Output:   <output-path>
Template: T3 Market Analysis | depth: standard

Section mapping results:
  ✅ Executive Summary  ← moved from "## Summary"
  ✅ Market Overview    ← moved from "## Overview"
  ✅ Competitive Landscape ← moved from "## Competitors"
  ⚠️  Trend Analysis    ← not found in source (TODO placeholder added)
  ✅ References         ← existing references retained

Suggested next steps:
  - [ ] Fill in TODO placeholders in ⚠️ sections (2 sections)
  - [ ] Complete 3 Mermaid diagram placeholders
  - [ ] Run /wiki-ingest <output-path> to update the wiki
```
