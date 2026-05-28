"""SQLite persistence layer for FindJob job tracking."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Job


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company         TEXT    NOT NULL,
    job_id          TEXT    NOT NULL,
    title           TEXT    NOT NULL,
    location        TEXT,
    url             TEXT,
    description     TEXT,
    date_posted     TEXT,
    relevance_score REAL    DEFAULT 0.0,
    first_seen_date TEXT    NOT NULL,
    last_seen_date  TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'active',
    UNIQUE(company, job_id)
);

CREATE TABLE IF NOT EXISTS scans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_ts     TEXT    NOT NULL,
    company     TEXT    NOT NULL,
    jobs_found  INTEGER NOT NULL DEFAULT 0,
    success     INTEGER NOT NULL DEFAULT 1,
    error_msg   TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_company   ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_status    ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_scans_company  ON scans(company);
"""


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DBManager:
    """Manages job data persistence in a SQLite database."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def upsert_jobs(self, jobs: list[Job], scan_ts: str) -> dict[str, list[str]]:
        """Insert new jobs or update existing ones. Returns dict of {new, updated} job_ids."""
        new_ids: list[str] = []
        updated_ids: list[str] = []

        for job in jobs:
            key = (job.company, job.job_id)
            existing = self._conn.execute(
                "SELECT id, status FROM jobs WHERE company=? AND job_id=?", key
            ).fetchone()

            if existing is None:
                self._conn.execute(
                    """
                    INSERT INTO jobs
                        (company, job_id, title, location, url, description,
                         date_posted, relevance_score, first_seen_date, last_seen_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
                    """,
                    (
                        job.company,
                        job.job_id,
                        job.title,
                        job.location,
                        job.url,
                        job.description,
                        job.date_posted,
                        job.relevance_score,
                        scan_ts,
                        scan_ts,
                    ),
                )
                new_ids.append(job.job_id)
            else:
                self._conn.execute(
                    """
                    UPDATE jobs
                    SET title=?, location=?, url=?, description=?,
                        date_posted=?, relevance_score=?,
                        last_seen_date=?, status='active'
                    WHERE company=? AND job_id=?
                    """,
                    (
                        job.title,
                        job.location,
                        job.url,
                        job.description,
                        job.date_posted,
                        job.relevance_score,
                        scan_ts,
                        job.company,
                        job.job_id,
                    ),
                )
                updated_ids.append(job.job_id)

        self._conn.commit()
        return {"new": new_ids, "updated": updated_ids}

    def mark_removed(self, company: str, current_job_ids: list[str], scan_ts: str) -> list[str]:
        """Mark jobs for *company* not in *current_job_ids* as 'removed'."""
        if not current_job_ids:
            return []

        placeholders = ",".join("?" * len(current_job_ids))
        rows = self._conn.execute(
            f"""
            SELECT job_id FROM jobs
            WHERE company=? AND status='active'
              AND job_id NOT IN ({placeholders})
            """,
            [company] + current_job_ids,
        ).fetchall()

        removed_ids = [r["job_id"] for r in rows]
        if removed_ids:
            self._conn.execute(
                f"""
                UPDATE jobs SET status='removed', last_seen_date=?
                WHERE company=? AND job_id IN ({",".join("?" * len(removed_ids))})
                """,
                [scan_ts, company] + removed_ids,
            )
            self._conn.commit()
        return removed_ids

    def log_scan(
        self,
        scan_ts: str,
        company: str,
        jobs_found: int,
        success: bool = True,
        error_msg: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO scans (scan_ts, company, jobs_found, success, error_msg) VALUES (?,?,?,?,?)",
            (scan_ts, company, jobs_found, 1 if success else 0, error_msg),
        )
        self._conn.commit()

    def get_active_jobs(self, company: str | None = None) -> list[dict[str, Any]]:
        """Return all active jobs, optionally filtered by company."""
        if company:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE status='active' AND company=? ORDER BY relevance_score DESC",
                (company,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE status='active' ORDER BY company, relevance_score DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_new_jobs(self, scan_ts: str) -> list[dict[str, Any]]:
        """Return jobs first seen in the given scan."""
        rows = self._conn.execute(
            "SELECT * FROM jobs WHERE first_seen_date=? ORDER BY company, relevance_score DESC",
            (scan_ts,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_removed_jobs(self, scan_ts: str) -> list[dict[str, Any]]:
        """Return jobs that were removed in this scan."""
        rows = self._conn.execute(
            "SELECT * FROM jobs WHERE status='removed' AND last_seen_date=? ORDER BY company",
            (scan_ts,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict[str, Any]:
        total = self._conn.execute("SELECT COUNT(*) FROM jobs WHERE status='active'").fetchone()[0]
        companies = self._conn.execute(
            "SELECT COUNT(DISTINCT company) FROM jobs WHERE status='active'"
        ).fetchone()[0]
        total_removed = self._conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='removed'"
        ).fetchone()[0]
        return {
            "total_active": total,
            "active_companies": companies,
            "total_removed": total_removed,
        }

    def close(self) -> None:
        self._conn.close()
