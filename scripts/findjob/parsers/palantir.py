"""Palantir Careers — SmartRecruiters public API."""

from __future__ import annotations

from ..models import Job
from .base import JobParser

_SR_API = "https://api.smartrecruiters.com/v1/companies/{company}/postings"
_JOB_URL = "https://jobs.smartrecruiters.com/{company}/{job_id}"


class PalantirParser(JobParser):
    """Fetches Palantir jobs via the SmartRecruiters public API."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        sr_company = self.extra.get("smartrecruiters_company", "palantir")
        url = _SR_API.format(company=sr_company)
        all_jobs: list[Job] = []
        seen: set[str] = set()

        for pos in positions:
            try:
                resp = self._get(
                    url,
                    params={"q": pos, "country": "KR", "limit": 50, "offset": 0},
                )
                data = resp.json()
            except Exception as exc:
                raise RuntimeError(f"Palantir SmartRecruiters API error: {exc}") from exc

            for item in data.get("content", []):
                title: str = item.get("name", "")
                loc = item.get("location", {})
                city = loc.get("city", "")
                country = loc.get("country", "")
                location = ", ".join(filter(None, [city, country]))

                if not self._matches(title, location or "South Korea", [pos], locations):
                    continue

                job_id = str(item.get("id", ""))
                if job_id in seen:
                    continue
                seen.add(job_id)

                job_url = item.get("ref") or _JOB_URL.format(company=sr_company, job_id=job_id)

                all_jobs.append(
                    Job(
                        company=self.company_name,
                        job_id=job_id,
                        title=title,
                        location=location,
                        url=job_url,
                        date_posted=item.get("releasedDate", ""),
                        relevance_score=self._position_score(title, positions),
                    )
                )

        return all_jobs
