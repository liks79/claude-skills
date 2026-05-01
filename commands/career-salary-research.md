Use the career-researcher agent to research salary data for: $ARGUMENTS

Format: `<role> [region] [years of experience]`
Examples: `Backend Engineer Seoul 3 years`, `ML Engineer Korea senior`

## Template Selection

Default template: **T3 Market Analysis**

| Situation | Template | Reason |
|-----------|----------|--------|
| Overall market salary analysis (default) | **T3** | Market size, distribution, and trend structure |
| Salary comparison across specific companies | T4 Comparative | Item-by-item score comparison structure |
| Quick summary | T1 Brief | Key figures-focused |

- If the user specifies `Template N` or `depth: <value>`, that value takes priority
- Otherwise defaults to T3, depth: standard
- Load the selected template file via Read → use its section structure as a scaffold
- Salary-research-specific sections (salary distribution table, comparison by company type, negotiation points) are added on top of the template

## Procedure

1. **Web research** — query the following sources via WebSearch/WebFetch:
   - Jobkorea, Saramin, Wanted (`wanted.co.kr`) — posting-based salaries
   - Blind — salary reviews
   - LinkedIn Salary Insights
   - Stack Overflow Developer Survey (latest year)
   - Levels.fyi (`levels.fyi`) — including foreign companies

2. **Collected fields**

   | Field | Description |
   |-------|-------------|
   | Market median | Median salary by role and years of experience |
   | By company size | Startup / Mid-size / Enterprise / Foreign |
   | Regional adjustment | Seoul, Pangyo, Busan, etc. |
   | 25th / 75th percentile | Distribution range |
   | Non-cash compensation | Stock options, RSU, signing bonus |

3. **Save** — `career/salary/<role_slug>_YYYY-MM.md`:

```markdown
# [Role] Salary Research

**Date**: YYYY-MM-DD
**Area**: career / salary
**Status**: 🔬 In Progress

## Summary
(One-line summary)

## Salary Distribution

| Experience | 25th Percentile | Median | 75th Percentile |
|------------|-----------------|--------|-----------------|
| 0–2 years | | | |
| 3–5 years | | | |
| 5–8 years | | | |
| 8+ years  | | | |

## Comparison by Company Type

| Type | Salary Range | Notes |
|------|-------------|-------|
| Startup | | |
| Mid-size | | |
| Enterprise | | |
| Foreign company | | |

## Non-Cash Compensation

- Stock options / RSU:
- Signing bonus:
- Key benefits:

## Negotiation Points

-

## References

- [Source](URL) — YYYY-MM-DD
```

4. After saving, ask the user whether to add a negotiation strategy section.
