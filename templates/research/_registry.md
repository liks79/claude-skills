# Research Template Registry

> 모든 리서치 커맨드에서 공유하는 템플릿 매핑 테이블.
> 커맨드는 이 레지스트리를 참조해 적합한 템플릿 파일을 Read한 뒤 스캐폴드로 사용한다.

---

## Template Files

| ID | 파일 | 분류 | 참고 서식 |
|----|------|------|-----------|
| T1 | `templates/research/T1-executive-brief.md` | EXECUTIVE BRIEF | Gartner |
| T2 | `templates/research/T2-tech-deep-dive.md` | TECHNOLOGY ANALYSIS | Forrester |
| T3 | `templates/research/T3-market-analysis.md` | MARKET ANALYSIS | CB Insights / McKinsey |
| T4 | `templates/research/T4-comparative-evaluation.md` | COMPARATIVE EVALUATION | Forrester Wave |
| T5 | `templates/research/T5-strategic-roadmap.md` | STRATEGIC ROADMAP | Deloitte Tech Trends |

---

## Command × Template 매핑

| 커맨드 | 기본 템플릿 | 대안 템플릿 | 선택 기준 |
|--------|------------|------------|-----------|
| `/new-research` | 주제에 따라 자동 선택 (아래 참조) | — | 키워드 기반 |
| `/career-job-analysis` | **T4** Comparative Evaluation | T1 Brief | 단일 공고=T1, 복수 비교=T4 |
| `/career-company-analysis` | **T3** Market Analysis | T1 Brief | 심층=T3, 빠른 조회=T1 |
| `/career-salary-research` | **T3** Market Analysis | T4 Comparative | 시장 전체=T3, 회사 비교=T4 |
| `/career-interview-prep` | **T5** Strategic Roadmap | T2 Deep-Dive | 준비 계획=T5, 기술 분석=T2 |

---

## `/new-research` 자동 선택 로직

인자(주제) 키워드를 분석하여 템플릿을 결정한다.

```
주제에 포함된 키워드          → 선택 템플릿
────────────────────────────────────────────
"비교", "vs", "선택", "평가"  → T4 Comparative Evaluation
"시장", "트렌드", "동향"       → T3 Market Analysis
"전략", "로드맵", "계획"       → T5 Strategic Roadmap
"아키텍처", "심층", "분석"     → T2 Tech Deep-Dive
그 외 (기본)                   → T1 Executive Brief
사용자가 명시 (Template N)     → 해당 템플릿 우선 적용
```

---

## Depth Parameter

모든 템플릿 공통 파라미터. 프롬프트에서 `depth: <값>`으로 지정.

| 값 | 각 섹션 처리 방식 |
|----|-----------------|
| `quick` | 핵심 bullet, 다이어그램 선택, Abstract = 1문장 |
| `standard` | 섹션당 서술 + 데이터 포인트 *(기본값)* |
| `deep` | 완전한 근거·반례·수치, 모든 다이어그램 |
| `exhaustive` | 제한 없음, Appendix + 케이스스터디 포함 |

---

## 커맨드에서 템플릿 사용하는 방법

```
1. 이 레지스트리(_registry.md)에서 적합한 템플릿 ID 결정
2. 해당 템플릿 파일을 Read 도구로 로드
3. 템플릿 구조를 스캐폴드로 사용하여 콘텐츠 생성
4. frontmatter의 depth 값에 따라 각 섹션 서술 깊이 조정
5. <!-- depth: ... --> 주석은 최종 출력에서 제거
```
