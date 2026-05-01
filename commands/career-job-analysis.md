Use the career-researcher agent to analyze a job posting: $ARGUMENTS

Input: URL or full job posting text

## Template Selection

Default template per `TEMPLATES/research/_registry.md`: **T4 Comparative Evaluation**

| Situation | Template | Reason |
|-----------|----------|--------|
| Single posting analysis (default) | **T4** | Requirements vs. own skills evaluation structure |
| Quick summary needed | T1 Brief | Core conclusion-focused |

- If the user specifies `Template N` or `depth: <value>`, that value takes priority
- Otherwise defaults to T4, depth: standard
- Load the selected template file via Read → use its section structure as a scaffold
- Job-analysis-specific sections (Position Summary, Gap Analysis, Resume Keywords) are added on top of the template

## Procedure

1. **Collect the posting**
   - If a URL is given: fetch the full posting text via WebFetch
   - If text is given: analyze it as-is

2. **Structured analysis**

   | Field | Extracted content |
   |-------|-------------------|
   | Position | Job title, level (Junior/Senior/Staff) |
   | Core requirements | Must-have skills and experience |
   | Preferred qualifications | Nice-to-have |
   | Tech stack | Languages, frameworks, tools |
   | Domain | Company domain and team area |
   | Compensation & benefits | Stated salary, perks |
   | Interview process | Application → Resume → Coding test → Interview stages |

3. **Fit gap analysis**
   If the user has provided their current background/skills:
   - Compare Matched skills vs. Gap skills
   - Suggest preparation priorities

4. **Keyword extraction** — list of key keywords to use when writing a resume or cover letter

5. **Save** — `20_AREAS/career/job-search/<company>_<role>_YYYY-MM-DD.md`:

```markdown
# [Company] [Role] Job Posting Analysis

**Date**: YYYY-MM-DD
**Area**: career / job-search
**Status**: 🔬 In Progress
**Source**: [URL or "Direct input"]

## Position Summary

- **Level**:
- **Team / Domain**:
- **Location**:

## Requirements

### Must-have
-

### Nice-to-have
-

## Tech Stack
-

## Compensation & Benefits
-

## Interview Process
-

## Gap Analysis

| Item | Have it? | Notes |
|------|----------|-------|
| | ✅ / ⚠️ / ❌ | |

## Resume Keywords
`keyword1` `keyword2` `keyword3`

## References
- [Job posting URL](URL) — YYYY-MM-DD
```
