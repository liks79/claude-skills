"""OpenAI Careers — Ashby HQ public job board API."""

from __future__ import annotations

from ..models import Job
from .base import JobParser

_ASHBY_API = "https://api.ashbyhq.com/posting-api/job-board/{company}"
_JOB_URL = "https://jobs.ashbyhq.com/{company}/{job_id}"


class OpenAIParser(JobParser):
    """Fetches OpenAI jobs via the Ashby HQ public job board API.

    Fetches ALL postings, then filters locally by location + position score.
    """

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        ashby_company = self.extra.get("ashby_company", "openai")
        url = _ASHBY_API.format(company=ashby_company)

        try:
            resp = self._get(url, params={"includeCompensation": "false"})
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(f"OpenAI Ashby API error: {exc}") from exc

        jobs: list[Job] = []
        for item in data.get("jobs", []):
            title: str = item.get("title", "")
            location: str = item.get("location") or item.get("locationName") or ""

            # Score first — skip if no position match
            score = self._position_score(title, positions)
            if score <= 0:
                continue

            # Location check
            if not self._location_matches(location, locations):
                continue

            job_id: str = str(item.get("id", ""))
            job_url = item.get("jobUrl") or _JOB_URL.format(
                company=ashby_company, job_id=job_id
            )
            desc_html = item.get("descriptionHtml") or ""
            desc_text = self._strip_html(desc_html)[:500] if desc_html else None

            jobs.append(
                Job(
                    company=self.company_name,
                    job_id=job_id,
                    title=title,
                    location=location,
                    url=job_url,
                    description=desc_text,
                    date_posted=item.get("publishedAt", ""),
                    relevance_score=score,
                )
            )

        return jobs
