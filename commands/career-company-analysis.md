Use the career-researcher agent to research and analyze the company: $ARGUMENTS

## Template Selection

Default template: **T3 Market Analysis**

| Situation | Template | Reason |
|-----------|----------|--------|
| In-depth company analysis (default) | **T3** | Market position and competitive environment structure |
| Quick lookup | T1 Brief | Core summary-focused |
| Includes competitor comparison | T4 Comparative | Multi-company comparative evaluation |

- If the user specifies `Template N` or `depth: <value>`, that value takes priority
- Otherwise defaults to T3, depth: standard
- Load the selected template file via Read → use its section structure as a scaffold
- Company-analysis-specific sections (Tech Stack, Culture, Interview, Compensation) are added on top of the template

## Procedure

1. **Web research** — perform WebSearch with the following queries:
   - `"<company>" engineer blog tech stack site:tech.kakao.com OR engineering.linecorp.com OR medium.com`
   - `"<company>" engineering culture OR tech stack 2024 OR 2025`
   - `"<company>" glassdoor interview OR leetcode`
   - `"<company>" salary OR benefits OR work-life balance`

2. **Collected sections**

   | Section | Content |
   |---------|---------|
   | Overview | Industry, size, founding year, key products/services |
   | Tech Stack | Languages, frameworks, infrastructure, data |
   | Culture | Organizational culture, work-life balance, remote work policy |
   | Interview | Interview stages, coding test, take-home assignment, interview reviews |
   | Compensation | Salary range, stock options, benefits |
   | Pros / Cons | Summary of advantages and disadvantages (source-based) |

3. **Save** — save to `${BASE_DIR:+$BASE_DIR/}career/companies/<company_slug>.md` using the template below:
   If `$BASE_DIR` is not set, path is relative to the current working directory.

```markdown
# [Company] Company Analysis

**Date**: YYYY-MM-DD
**Area**: career / companies
**Status**: 🔬 In Progress

## Overview
...

## Tech Stack
...

## Culture
...

## Interview Process
...

## Compensation
...

## Pros / Cons
**Pros**:
-

**Cons**:
-

## References
- [Source](URL) — YYYY-MM-DD
```

4. Notify the user of the saved file path and ask whether they want a PPTX conversion.
   If needed, suggest `/career-to-pptx ${BASE_DIR:+$BASE_DIR/}career/companies/<company_slug>.md`.
