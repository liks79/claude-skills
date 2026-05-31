"""LinkedIn public guest-API job search parser.

Uses LinkedIn's undocumented guest jobs endpoint — no login required.
Returns HTML fragments that we parse with regex.

Endpoint: https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
  ?keywords={company_name}
  &location=Seoul%2C+South+Korea
  &geoId=105149290    ← LinkedIn geoId for Seoul, South Korea
  &start=0
  &count=25
"""

from __future__ import annotations

import re
from typing import Any

import requests

from ..models import Job
from .base import JobParser

_API_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_JOB_URL = "https://www.linkedin.com/jobs/view/{job_id}"
_SEOUL_GEO_ID = "105149290"
_PAGE_SIZE = 25
_MAX_PAGES = 3  # cap at 75 jobs per company search

_LI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.linkedin.com/jobs/",
    "X-Requested-With": "XMLHttpRequest",
}

# Regex patterns for LinkedIn's HTML job cards
_RE_JOB_ID = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"')
_RE_TITLE = re.compile(
    r'class="[^"]*base-search-card__title[^"]*"[^>]*>\s*(.*?)\s*</h3>',
    re.DOTALL,
)
_RE_COMPANY = re.compile(
    r'class="[^"]*base-search-card__subtitle[^"]*"[^>]*>.*?<a[^>]*>\s*(.*?)\s*</a>',
    re.DOTALL,
)
_RE_LOCATION = re.compile(
    r'class="[^"]*job-search-card__location[^"]*"[^>]*>\s*(.*?)\s*</span>',
    re.DOTALL,
)
_RE_DATE = re.compile(
    r'<time[^>]*datetime="([^"]+)"',
)


def _clean(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html)).strip()


class LinkedInParser(JobParser):
    """Searches LinkedIn for a specific company's open roles in Seoul.

    Config options (under ``extra``):
      linkedin_query: str  — custom search keyword (defaults to company name)
    """

    def __init__(self, company_name: str, company_url: str, extra: dict[str, Any]) -> None:
        super().__init__(company_name, company_url, extra)
        self.search_query: str = extra.get("linkedin_query", company_name)

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        jobs: list[Job] = []
        seen_ids: set[str] = set()

        for page in range(_MAX_PAGES):
            params = {
                "keywords": self.search_query,
                "location": "Seoul, South Korea",
                "geoId": _SEOUL_GEO_ID,
                "start": page * _PAGE_SIZE,
                "count": _PAGE_SIZE,
            }
            try:
                resp = requests.get(
                    _API_URL,
                    params=params,
                    headers=_LI_HEADERS,
                    timeout=15,
                    allow_redirects=True,
                )
                resp.raise_for_status()
            except Exception as exc:
                raise RuntimeError(
                    f"LinkedIn guest API error for {self.company_name}: {exc}"
                ) from exc

            html = resp.text.strip()
            if not html:
                break

            job_ids = _RE_JOB_ID.findall(html)
            if not job_ids:
                break

            titles = [_clean(t) for t in _RE_TITLE.findall(html)]
            companies = [_clean(c) for c in _RE_COMPANY.findall(html)]
            locs = [_clean(l) for l in _RE_LOCATION.findall(html)]
            dates = _RE_DATE.findall(html)

            for i, job_id in enumerate(job_ids):
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                title = titles[i] if i < len(titles) else ""
                location = locs[i] if i < len(locs) else "Seoul, South Korea"
                date_posted = dates[i][:10] if i < len(dates) else None

                if not title:
                    continue

                if not self._location_matches(location, locations):
                    continue

                score = self._position_score(title, positions)
                if score <= 0:
                    continue

                jobs.append(Job(
                    company=self.company_name,
                    job_id=f"li_{job_id}",
                    title=title,
                    location=location,
                    url=_JOB_URL.format(job_id=job_id),
                    description=None,
                    date_posted=date_posted,
                    relevance_score=score,
                ))

            if len(job_ids) < _PAGE_SIZE:
                break

        return jobs
