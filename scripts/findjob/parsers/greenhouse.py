"""Generic Greenhouse ATS parser (shared base for Datadog, Cloudflare, Anthropic, Coupang etc.)."""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import JobParser

_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
_JOB_URL = "https://boards.greenhouse.io/{board}/jobs/{job_id}"


class GreenhouseParser(JobParser):
    """Parses jobs from the Greenhouse Boards public API.

    Strategy: fetch ALL jobs for the board (with content=false for speed), then
    filter by location and position score locally.  Using content=false avoids
    downloading large description HTML for every job.
    """

    def __init__(self, company_name: str, company_url: str, extra: dict[str, Any]) -> None:
        super().__init__(company_name, company_url, extra)
        self.board = extra.get("greenhouse_board", company_name.lower().replace(" ", ""))

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        url = _API_BASE.format(board=self.board)
        try:
            # content=false → faster (no HTML description per job)
            resp = self._get(url, params={"content": "false"})
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(f"Greenhouse API error for {self.company_name}: {exc}") from exc

        jobs: list[Job] = []
        for item in data.get("jobs", []):
            title: str = item.get("title", "")
            location: str = item.get("location", {}).get("name", "")

            # Score first — skip fast if no position match
            score = self._position_score(title, positions)
            if score <= 0:
                continue

            # Then check location
            if not self._location_matches(location, locations):
                continue

            job_id = str(item.get("id", ""))
            # Prefer the absolute_url from the API response
            job_url = item.get("absolute_url") or _JOB_URL.format(board=self.board, job_id=job_id)

            jobs.append(
                Job(
                    company=self.company_name,
                    job_id=job_id,
                    title=title,
                    location=location,
                    url=job_url,
                    description=None,  # omit for speed (content=false)
                    date_posted=item.get("updated_at", ""),
                    relevance_score=score,
                )
            )

        return jobs
