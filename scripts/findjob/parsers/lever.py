"""Generic Lever ATS parser (shared base for Anthropic, etc.)."""

from __future__ import annotations

from typing import Any

from ..models import Job
from .base import JobParser

_API_URL = "https://api.lever.co/v0/postings/{company}?mode=json"


class LeverParser(JobParser):
    """Parses jobs from the Lever public postings API."""

    def __init__(self, company_name: str, company_url: str, extra: dict[str, Any]) -> None:
        super().__init__(company_name, company_url, extra)
        self.lever_name = extra.get("lever_name", company_name.lower().replace(" ", ""))

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        url = _API_URL.format(company=self.lever_name)
        try:
            resp = self._get(url)
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(f"Lever API error for {self.company_name}: {exc}") from exc

        jobs: list[Job] = []
        for item in data:
            title: str = item.get("text", "")
            # Lever location is in categories.location
            categories = item.get("categories", {})
            location: str = categories.get("location", "")

            if not self._matches(title, location, positions, locations):
                continue

            job_url = item.get("hostedUrl") or item.get("applyUrl") or self.company_url
            description_list = item.get("descriptionBody") or item.get("description") or ""
            desc = self._strip_html(description_list)[:500] if description_list else None
            date_posted = ""
            created_at = item.get("createdAt")
            if created_at:
                try:
                    from datetime import datetime, timezone

                    dt = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                    date_posted = dt.strftime("%Y-%m-%d")
                except Exception:
                    date_posted = str(created_at)

            jobs.append(
                Job(
                    company=self.company_name,
                    job_id=item.get("id", ""),
                    title=title,
                    location=location,
                    url=job_url,
                    description=desc,
                    date_posted=date_posted,
                    relevance_score=self._position_score(title, positions),
                )
            )

        return jobs
