"""Generate a Markdown job search report from scan results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import Job, ScanResult


def _stars(count: int) -> str:
    if count >= 8:
        return "⭐⭐⭐"
    if count >= 4:
        return "⭐⭐"
    if count >= 1:
        return "⭐"
    return "—"


def _format_table_row(job: dict[str, Any], is_new: bool = False, show_company: bool = False) -> str:
    status_badge = "🆕 New" if is_new else "✅ Active"
    title_col = f"[{job['title']}]({job['url']})"
    score = f"{job['relevance_score']:.0%}" if job.get("relevance_score") else "—"
    date = job.get("date_posted") or job.get("first_seen_date", "—")
    # Only truncate ISO timestamps (YYYY-MM-DDTHH:MM:SSZ); leave human-readable dates intact
    if date and len(date) > 10 and date[4:5] == "-":
        date = date[:10]
    row = f"| {title_col} | {job['location'] or '—'} | {date} | {score} | {status_badge} |"
    if show_company:
        row = f"| {job.get('company', '—')} {row}"
    return row


def generate_report(
    scan_result: ScanResult,
    new_jobs: list[dict[str, Any]],
    removed_jobs: list[dict[str, Any]],
    all_active: list[dict[str, Any]],
    db_stats: dict[str, Any],
    config: dict[str, Any],
) -> str:
    """Build and return the full Markdown report string."""

    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []

    # ─── Header ──────────────────────────────────────────────────────────────
    lines += [
        f"# 💼 Job Market Report — {date_str}",
        "",
        f"> **Generated**: {ts_str}  ",
        f"> **Scanned**: {len(scan_result.results) - len(scan_result.failed_companies)} / {len(scan_result.results)} companies  ",
        f"> **With openings**: {scan_result.companies_with_jobs} / {len(scan_result.results)} companies  ",
        f"> **Config**: `wanted_positions` × `wanted_locations` filter applied",
        "",
        "---",
        "",
    ]

    # ─── Executive Summary ───────────────────────────────────────────────────
    lines += [
        "## 📊 Executive Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total active positions | **{db_stats.get('total_active', 0)}** |",
        f"| 🆕 New since last scan | **{len(new_jobs)}** |",
        f"| 🗑️ Removed since last scan | **{len(removed_jobs)}** |",
        f"| Companies scanned | **{len(scan_result.results) - len(scan_result.failed_companies)} / {len(scan_result.results)}** |",
        f"| Companies with openings | **{scan_result.companies_with_jobs} / {len(scan_result.results)}** |",
        f"| Scan timestamp | {ts_str} |",
        "",
    ]

    # ─── Failed companies ─────────────────────────────────────────────────────
    failed = scan_result.failed_companies
    if failed:
        lines += [
            f"> ⚠️ **Fetch errors** (data may be stale): {', '.join(failed)}",
            "",
        ]

    # ─── Top Recommended Companies ───────────────────────────────────────────
    company_jobs: dict[str, list[dict]] = {}
    for job in all_active:
        company_jobs.setdefault(job["company"], []).append(job)

    ranked = sorted(company_jobs.items(), key=lambda x: len(x[1]), reverse=True)

    lines += [
        "## 🏆 Top Recommended Companies",
        "",
    ]

    if ranked:
        lines += [
            "| Rank | Company | Open Positions | Rating |",
            "|------|---------|---------------|--------|",
        ]
        for rank, (company, jobs_list) in enumerate(ranked[:5], 1):
            count = len(jobs_list)
            company_url = next(
                (c["url"] for c in config.get("companies", []) if c["name"] == company),
                "#",
            )
            lines.append(
                f"| #{rank} | [{company}]({company_url}) | {count} | {_stars(count)} |"
            )
        lines.append("")
    else:
        lines += ["_No matching positions found in current scan._", ""]

    lines += ["---", ""]

    # ─── New Positions ────────────────────────────────────────────────────────
    if new_jobs:
        lines += [
            f"## 🆕 New Positions ({len(new_jobs)} found)",
            "",
            "| Company | Title | Location | Posted | Match | Status |",
            "|---------|-------|----------|--------|-------|--------|",
        ]
        for job in sorted(new_jobs, key=lambda j: j.get("relevance_score", 0), reverse=True):
            lines.append(_format_table_row(job, is_new=True, show_company=True))
        lines += ["", "---", ""]
    else:
        lines += ["## 🆕 New Positions", "", "_No new positions since last scan._", "", "---", ""]

    # ─── Removed Positions ───────────────────────────────────────────────────
    if removed_jobs:
        lines += [
            f"## 🗑️ Removed Positions ({len(removed_jobs)} closed)",
            "",
            "| Company | Title | Last Seen |",
            "|---------|-------|-----------|",
        ]
        for job in removed_jobs:
            last_seen = (job.get("last_seen_date") or "")[:10]
            title_col = f"[{job['title']}]({job['url']})" if job.get("url") else job["title"]
            lines.append(f"| {job['company']} | {title_col} | {last_seen} |")
        lines += ["", "---", ""]

    # ─── All Active Positions by Company ─────────────────────────────────────
    lines += [
        "## 📋 All Active Positions by Company",
        "",
    ]

    new_job_ids = {j["job_id"] for j in new_jobs}

    for company, jobs_list in ranked:
        lines += [
            f"### {company} ({len(jobs_list)} position{'s' if len(jobs_list) != 1 else ''})",
            "",
            "| Title | Location | Posted | Match | Status |",
            "|-------|----------|--------|-------|--------|",
        ]
        sorted_jobs = sorted(jobs_list, key=lambda j: j.get("relevance_score", 0), reverse=True)
        for job in sorted_jobs:
            is_new = job["job_id"] in new_job_ids
            lines.append(_format_table_row(job, is_new=is_new))
        lines += [""]

    # ─── Companies with No Openings ──────────────────────────────────────────
    scanned_companies = {r.company_name for r in scan_result.results}
    no_opening = [c for c in scanned_companies if c not in company_jobs]
    if no_opening:
        lines += [
            "### Companies with No Matching Openings",
            "",
            ", ".join(f"_{c}_" for c in sorted(no_opening)),
            "",
        ]

    # ─── Footer ──────────────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## ℹ️ About This Report",
        "",
        "- Generated by `/findjob` command  ",
        "- Positions filtered by `wanted_locations` and `wanted_positions` in `commands/findjob.md`  ",
        "- Match % = keyword overlap between job title and wanted positions  ",
        "- History tracked in `jobs.db` (SQLite) — run `/findjob` again to see deltas  ",
        f"- Total positions in DB (all time, including removed): "
        f"{db_stats.get('total_active', 0) + db_stats.get('total_removed', 0)}  ",
        "",
    ]

    return "\n".join(lines)
