Use the career-researcher agent to analyze interview guides and generate a preparation report: $ARGUMENTS

Input format: `<company> <role> [interview guide URL]`
Examples: `Toss Backend Engineer`, `Kakao Frontend https://...`, `Google SWE`

---

## Template Selection

Default template: **T5 Strategic Roadmap**

| Situation | Template | Reason |
|-----------|----------|--------|
| Interview preparation roadmap (default) | **T5** | Step-by-step action plan and milestone structure |
| In-depth tech stack analysis | T2 Tech Deep-Dive | Focused on preparing for specific technologies |
| Comparing multiple companies | T4 Comparative | Compare difficulty and culture across companies |

- If the user specifies `Template N` or `depth: <value>`, that value takes priority
- Otherwise defaults to T5, depth: standard
- Load the selected template file via Read → use its section structure as a scaffold
- Interview-prep-specific sections (Interview process, Coding/System Design/Behavioral questions) are added on top of the template

## Procedure

### Step 1 — Collect Interview Guides

If the input includes a URL:
- Fetch the full page via WebFetch

If no URL is provided, run the following WebSearch queries (all of them):
- `"<company>" "<role>" interview questions 2024 OR 2025`
- `"<company>" coding test OR coding interview experience site:blind.so OR reddit.com`
- `"<company>" "<role>" system design interview`
- `"<company>" "<role>" behavioral interview questions`
- `"<company>" engineer interview glassdoor`
- `"<company>" technical interview questions OR interview experience`

Record actual source URLs and dates from the collected materials.

---

### Step 2 — Classify Questions and Scenarios

Classify the collected content into the following 4 categories.

#### A. Coding Interview (Coding)
- Extract frequently tested algorithm and data structure topics
- Tag problem types: `Array/String` `Tree/Graph` `DP` `Search` `Sort` `Hash` etc.
- Identify company-specific difficulty and platform (Programmers, BOJ, LeetCode)

#### B. System Design
- Collect actual scenario titles that appeared (e.g., "Design a URL shortener", "Design a chat system")
- Identify key discussion points for each scenario (Scale, Bottleneck, Trade-off)
- Identify design topics specific to the company's domain

#### C. Behavioral Interview
- Collect STAR-format questions
- Classify by theme: leadership, collaboration, failure experience, conflict resolution, etc.
- Group questions connected to company Core Values

#### D. Technical Deep-dive
- Questions related to specific technologies (DB, networking, language internals, etc.)
- Experience-based project questions (reasons for technology choices, trade-offs, etc.)

---

### Step 3 — Write the Report

Create `${BASE_DIR:+$BASE_DIR/}career/interview/<company>_<role>_prep_YYYY-MM-DD.md` using the template below:
(If `$BASE_DIR` is not set, path is relative to the current working directory.)

```markdown
# [Company] [Role] Interview Preparation Report

**Date**: YYYY-MM-DD
**Area**: career / interview
**Status**: 🔬 In Progress
**Target**: [Company] — [Role]

---

## 1. Interview Process Overview

| Stage | Format | Duration | Notes |
|-------|--------|----------|-------|
| Resume screening | | | |
| Coding test | | | |
| 1st technical interview | | | |
| 2nd technical interview | | | |
| Culture fit / HR | | | |

---

## 2. Coding Interview

### Frequently Tested Topics

| Topic | Frequency | Representative Problem Type | Recommended Platform |
|-------|-----------|----------------------------|----------------------|
| | ⭐⭐⭐ | | |

### Key Patterns by Scenario

#### Scenario 1: [Type]
- **Format**: (e.g., live coding, take-home)
- **Core algorithm**:
- **Pitfalls and watch-outs**:
- **Example problem**:

#### Scenario 2: [Type]
...

### Preparation Checklist
- [ ]
- [ ]

---

## 3. System Design

### Frequently Tested Scenarios

| Scenario | Key Discussion Points | Related Technologies |
|----------|-----------------------|----------------------|
| | | |

### Approach Guide by Scenario

#### [Scenario Title]
- **Requirements clarification**: Questions to ask
- **High-level design**: Key components
- **Scale points**: Bottlenecks, caching, sharding strategy
- **Trade-off**: Options and reasoning
- **Company domain connection**: Relevance to this company's services

---

## 4. Behavioral Interview

### Key Questions by Theme

#### Leadership / Ownership
- Q:
  - Key keywords:
  - STAR template: **S**ituation → **T**ask → **A**ction → **R**esult

#### Collaboration / Conflict Resolution
- Q:

#### Failure / Learning
- Q:

#### Growth / Motivation
- Q:

### Connecting to This Company's Core Values
- [Value 1]: Types of experience that can be connected
- [Value 2]:

---

## 5. Technical Deep-dive

### Frequently Asked Questions

| Area | Question | Key Answer Points |
|------|----------|------------------|
| DB | | |
| Networking | | |
| Language / Runtime | | |
| Architecture | | |

---

## 6. Preparation Roadmap

| Timeline | Focus Area | Specific Actions |
|----------|------------|-----------------|
| D-30 | | |
| D-14 | | |
| D-7  | | |
| D-3  | | |
| D-1  | | |

---

## 7. Reference Materials

| Type | Title / Link | Notes |
|------|-------------|-------|
| Interview reviews | | |
| Official materials | | |
| Problem solutions | | |

## References

- [Source](URL) — verified YYYY-MM-DD
```

---

### Step 4 — Create Per-Category Sub-files (optional)

After generating the report, suggest the following to the user:

1. **Coding problem list** → `${BASE_DIR:+$BASE_DIR/}career/interview/coding/<company>_<role>_problems.md`
2. **System design notes** → `${BASE_DIR:+$BASE_DIR/}career/interview/system-design/<company>_<role>_scenarios.md`
3. **Behavioral Q&A sheet** → `${BASE_DIR:+$BASE_DIR/}career/interview/behavioral/<company>_<role>_behavioral.md`
4. **PPTX conversion** → `/career-to-pptx ${BASE_DIR:+$BASE_DIR/}career/interview/<main-report>.md`

---

### Step 5 — Completion Notice

Notify the user of the saved file paths and next actions:
- If any section is thin, suggest additional web research
- If gap analysis is needed, suggest linking to `/career-job-analysis`
