#!/usr/bin/env python3
"""FindJob — main orchestrator.

Usage:
  uv run python scripts/findjob_run.py [--output-dir DIR] [--db-path PATH] [--config FILE]

Prints the path to the generated Markdown report on stdout.
Progress and errors go to stderr.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure scripts/ is on sys.path so `findjob.*` relative imports work
_scripts_dir = Path(__file__).parent.parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from .config import load_config, resolve_db_path, resolve_output_dir
from .db_manager import DBManager
from .models import CompanyResult, ScanResult
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
    return p.parse_args()


def run() -> str:
    """Main entry point. Returns the path to the generated report."""
    args = parse_args()

    cfg = load_config(args.config)
    locations: list[str] = cfg["wanted_locations"]
    positions: list[str] = cfg["wanted_positions"]
    companies: list[dict] = cfg["companies"]
    min_score: float = float(cfg.get("min_match_score", 0.40))

    output_dir = resolve_output_dir(args.output_dir)
    db_path = resolve_db_path(args.db_path, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _eprint(f"[findjob] Output dir    : {output_dir}")
    _eprint(f"[findjob] DB path       : {db_path}")
    _eprint(f"[findjob] Locations     : {locations}")
    _eprint(f"[findjob] Positions     : {len(positions)} defined")
    _eprint(f"[findjob] Companies     : {len(companies)} defined")
    _eprint(f"[findjob] Min score     : {min_score}")
    _eprint("")

    db = DBManager(db_path)
    scan_ts = _now_iso()

    results: list[CompanyResult] = []

    for company_cfg in companies:
        name: str = company_cfg["name"]
        url: str = company_cfg.get("url", "")
        parser_key: str = company_cfg.get("parser", "")
        extra: dict = {k: v for k, v in company_cfg.items() if k not in ("name", "url", "parser")}

        _eprint(f"[findjob] ⏳ Scanning: {name} ({parser_key})")

        result = CompanyResult(company_name=name, company_url=url)

        try:
            parser = get_parser(parser_key, name, url, extra)
            raw_jobs = parser.fetch_jobs(locations, positions)
            jobs = [j for j in raw_jobs if j.relevance_score >= min_score]
            result.jobs = jobs

            delta = db.upsert_jobs(jobs, scan_ts)
            removed_ids = db.mark_removed(name, [j.job_id for j in jobs], scan_ts)
            db.log_scan(scan_ts, name, len(jobs), success=True)

            _eprint(
                f"[findjob]  ✅ {name}: {len(jobs)} matches "
                f"(+{len(delta['new'])} new, -{len(removed_ids)} removed)"
            )
        except Exception as exc:
            error_msg = str(exc)
            result.error = error_msg
            db.log_scan(scan_ts, name, 0, success=False, error_msg=error_msg)
            _eprint(f"[findjob]  ❌ {name}: {error_msg}")

        results.append(result)

    _eprint("")

    scan_result = ScanResult(scan_ts=scan_ts, results=results)
    new_jobs = db.get_new_jobs(scan_ts)
    removed_jobs = db.get_removed_jobs(scan_ts)
    all_active = db.get_active_jobs()
    db_stats = db.get_stats()

    _eprint(f"[findjob] 📊 Total active : {db_stats['total_active']}")
    _eprint(f"[findjob] 🆕 New          : {len(new_jobs)}")
    _eprint(f"[findjob] 🗑️  Removed      : {len(removed_jobs)}")

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
