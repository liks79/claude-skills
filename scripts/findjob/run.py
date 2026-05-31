#!/usr/bin/env python3
"""FindJob — main orchestrator.

Usage:
  uv run python scripts/findjob_run.py [--output-dir DIR] [--db-path PATH] [--config FILE]

Prints the path to the generated Markdown report on stdout.
Progress and errors go to stderr.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure scripts/ is on sys.path so `findjob.*` relative imports work
_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from .config import load_config, resolve_db_path, resolve_output_dir
from .db_manager import DBManager
from .link_validator import validate_jobs
from .models import CompanyResult, Job, ScanResult
from .parsers import get_parser
from .report_generator import generate_report


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FindJob — job opening tracker")
    p.add_argument("--output-dir", help="Directory for report files")
    p.add_argument("--db-path", help="SQLite DB file path")
    p.add_argument("--config", help="Path to findjob.md config file")
    p.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip link validation phase (faster, may include stale links)",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Deduplication helpers
# ---------------------------------------------------------------------------

_RE_BRACKET_PREFIX = re.compile(r"^\[.*?\]\s*")


def _norm_title(title: str) -> str:
    """Normalize job title for dedup key: strip [Company] prefix, lowercase."""
    t = _RE_BRACKET_PREFIX.sub("", title).strip().lower()
    return re.sub(r"\s+", " ", t)


def deduplicate_jobs(jobs: list[Job]) -> list[Job]:
    """Remove duplicate jobs across sources.

    Key: (company_name.lower(), normalized_title)
    Preference order (first wins): company career page > LinkedIn.
    """
    seen: dict[tuple[str, str], Job] = {}
    for job in jobs:
        key = (job.company.lower(), _norm_title(job.title))
        if key not in seen:
            seen[key] = job
        else:
            existing = seen[key]
            # Prefer direct career page URL over LinkedIn
            if "linkedin.com" in existing.url and "linkedin.com" not in job.url:
                seen[key] = job
    return list(seen.values())


# ---------------------------------------------------------------------------
# LinkedIn supplemental search
# ---------------------------------------------------------------------------

def _run_linkedin_search(
    companies: list[dict],
    locations: list[str],
    positions: list[str],
    min_score: float,
) -> list[Job]:
    """Search LinkedIn for each company's jobs and return matching results."""
    from .parsers.linkedin import LinkedInParser

    linkedin_jobs: list[Job] = []

    for company_cfg in companies:
        name: str = company_cfg["name"]
        li_query: str = company_cfg.get("linkedin_query", name)

        _eprint(f"[findjob] 🔎 LinkedIn: {name}")
        try:
            parser = LinkedInParser(
                company_name=name,
                company_url="",
                extra={"linkedin_query": li_query},
            )
            raw = parser.fetch_jobs(locations, positions)
            filtered = [j for j in raw if j.relevance_score >= min_score]
            linkedin_jobs.extend(filtered)
            _eprint(f"[findjob]   └─ {len(filtered)} matches from LinkedIn")
        except Exception as exc:
            _eprint(f"[findjob]   └─ ⚠️  LinkedIn failed for {name}: {exc}")

    return linkedin_jobs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> str:
    """Main entry point. Returns the path to the generated report."""
    args = parse_args()

    # ── Load configuration ──────────────────────────────────────────────────
    cfg = load_config(args.config)
    locations: list[str] = cfg["wanted_locations"]
    positions: list[str] = cfg["wanted_positions"]
    companies: list[dict] = cfg["companies"]
    min_score: float = float(cfg.get("min_match_score", 0.40))
    enable_validation: bool = cfg.get("enable_link_validation", True) and not args.skip_validation
    enable_linkedin: bool = cfg.get("enable_linkedin_search", True)

    # Separate LinkedIn entries from primary company entries
    primary_companies = [c for c in companies if c.get("parser") != "linkedin"]
    linkedin_company_cfgs = [c for c in companies if c.get("parser") == "linkedin"]

    # ── Resolve paths ───────────────────────────────────────────────────────
    output_dir = resolve_output_dir(args.output_dir)
    db_path = resolve_db_path(args.db_path, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _eprint(f"[findjob] Output dir    : {output_dir}")
    _eprint(f"[findjob] DB path       : {db_path}")
    _eprint(f"[findjob] Locations     : {locations}")
    _eprint(f"[findjob] Positions     : {len(positions)} defined")
    _eprint(f"[findjob] Companies     : {len(primary_companies)} defined")
    _eprint(f"[findjob] Min score     : {min_score}")
    _eprint(f"[findjob] Link validate : {'✅ enabled' if enable_validation else '⏭️  skipped'}")
    _eprint(f"[findjob] LinkedIn      : {'✅ enabled' if enable_linkedin else '⏭️  skipped'}")
    _eprint("")

    # ── Open DB ─────────────────────────────────────────────────────────────
    db = DBManager(db_path)
    scan_ts = _now_iso()

    # ── Phase 1: Run primary parsers ─────────────────────────────────────────
    results: list[CompanyResult] = []
    all_raw_jobs: list[Job] = []

    for company_cfg in primary_companies:
        name: str = company_cfg["name"]
        url: str = company_cfg.get("url", "")
        parser_key: str = company_cfg.get("parser", "")
        extra: dict = {
            k: v for k, v in company_cfg.items()
            if k not in ("name", "url", "parser")
        }

        _eprint(f"[findjob] ⏳ Scanning: {name} ({parser_key})")
        result = CompanyResult(company_name=name, company_url=url)

        try:
            parser = get_parser(parser_key, name, url, extra)
            raw_jobs = parser.fetch_jobs(locations, positions)
            jobs = [j for j in raw_jobs if j.relevance_score >= min_score]
            result.jobs = jobs
            all_raw_jobs.extend(jobs)
            _eprint(f"[findjob]  ✅ {name}: {len(jobs)} matches found")
        except Exception as exc:
            error_msg = str(exc)
            result.error = error_msg
            db.log_scan(scan_ts, name, 0, success=False, error_msg=error_msg)
            _eprint(f"[findjob]  ❌ {name}: {error_msg}")

        results.append(result)

    _eprint("")

    # ── Phase 2: Link validation ─────────────────────────────────────────────
    if enable_validation and all_raw_jobs:
        _eprint("")
        valid_jobs, invalid_jobs = validate_jobs(all_raw_jobs, eprint=_eprint)

        # Track which job_ids were invalidated per company
        invalid_ids: set[tuple[str, str]] = {
            (j.company, j.job_id) for j in invalid_jobs
        }

        # Update CompanyResult jobs to only include valid ones
        for result in results:
            if result.error:
                continue
            result.jobs = [
                j for j in result.jobs
                if (j.company, j.job_id) not in invalid_ids
            ]

        # Rebuild all_raw_jobs to only valid ones
        all_raw_jobs = valid_jobs
        _eprint("")

    # ── Phase 3: LinkedIn supplemental search ───────────────────────────────
    linkedin_jobs: list[Job] = []
    linkedin_result: CompanyResult | None = None

    if enable_linkedin:
        _eprint("[findjob] 🔗 Running LinkedIn supplemental search...")
        # Use either explicit linkedin parser entries or all primary companies
        search_targets = linkedin_company_cfgs if linkedin_company_cfgs else primary_companies
        linkedin_jobs = _run_linkedin_search(search_targets, locations, positions, min_score)

        if linkedin_jobs:
            # Deduplicate LinkedIn results against primary results
            before_dedup = len(linkedin_jobs)
            combined = deduplicate_jobs(all_raw_jobs + linkedin_jobs)
            li_unique = [j for j in combined if j.job_id.startswith("li_")]
            linkedin_jobs = li_unique

            _eprint(
                f"[findjob] 🔗 LinkedIn: {before_dedup} found, "
                f"{len(linkedin_jobs)} unique after dedup"
            )

            if linkedin_jobs:
                linkedin_result = CompanyResult(
                    company_name="LinkedIn (supplemental)",
                    company_url="https://www.linkedin.com/jobs/",
                    jobs=linkedin_jobs,
                )
                results.append(linkedin_result)
                all_raw_jobs.extend(linkedin_jobs)

        _eprint("")

    # ── Phase 4: Upsert into DB ─────────────────────────────────────────────
    for result in results:
        if result.error:
            # Fetch failed entirely — skip to avoid falsely marking all jobs removed
            continue

        valid_ids = [j.job_id for j in result.jobs]
        delta: dict[str, list[str]] = {"new": [], "updated": []}

        if result.jobs:
            delta = db.upsert_jobs(result.jobs, scan_ts)
            db.log_scan(scan_ts, result.company_name, len(result.jobs), success=True)

        # Always call mark_removed_force for non-error results so that jobs invalidated
        # by link validation (result.jobs emptied) are properly marked removed.
        removed_ids = db.mark_removed_force(
            result.company_name, valid_ids, scan_ts
        )

        label = "LinkedIn" if result.company_name.startswith("LinkedIn") else result.company_name
        _eprint(
            f"[findjob]  💾 {label}: {len(result.jobs)} saved "
            f"(+{len(delta['new'])} new, -{len(removed_ids)} removed)"
        )

    _eprint("")

    # ── Collect report data ─────────────────────────────────────────────────
    scan_result = ScanResult(scan_ts=scan_ts, results=results)
    new_jobs = db.get_new_jobs(scan_ts)
    removed_jobs = db.get_removed_jobs(scan_ts)
    all_active = db.get_active_jobs()
    db_stats = db.get_stats()

    _eprint(f"[findjob] 📊 Total active : {db_stats['total_active']}")
    _eprint(f"[findjob] 🆕 New          : {len(new_jobs)}")
    _eprint(f"[findjob] 🗑️  Removed      : {len(removed_jobs)}")

    # ── Generate report ─────────────────────────────────────────────────────
    report_md = generate_report(
        scan_result=scan_result,
        new_jobs=new_jobs,
        removed_jobs=removed_jobs,
        all_active=all_active,
        db_stats=db_stats,
        config=cfg,
    )

    date_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    report_path = output_dir / f"findjob-{date_str}.md"
    report_path.write_text(report_md, encoding="utf-8")

    db.close()

    _eprint(f"\n[findjob] ✅ Report saved: {report_path}")
    print(str(report_path))
    return str(report_path)


if __name__ == "__main__":
    run()
