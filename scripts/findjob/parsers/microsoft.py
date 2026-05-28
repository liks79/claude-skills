"""Microsoft Careers — LinkedIn Jobs API fallback.

Microsoft's main careers site (careers.microsoft.com) is now a full SPA using
Eightfold AI which requires JavaScript rendering and CSRF tokens — not accessible
via simple HTTP requests.

This parser tries two approaches:
  1. GCS services API (old endpoint, may work with SSL workaround)
  2. HTML scraping of the search page for any JSON-LD data
If both fail, it returns an empty list with a note rather than crashing the run.
"""

from __future__ import annotations

import warnings

import requests
import urllib3
from bs4 import BeautifulSoup

from ..models import Job
from .base import JobParser, _HEADERS, _REQUEST_TIMEOUT

_GCS_URL = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
_SEARCH_PAGE = "https://careers.microsoft.com/v2/global/en/search.html"
_JOB_BASE = "https://jobs.careers.microsoft.com/global/en/job/{job_id}"


class MicrosoftParser(JobParser):
    """Fetches Microsoft jobs with multiple fallback strategies."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        # Strategy 1: GCS API (classic endpoint, SSL workaround)
        try:
            jobs = self._fetch_gcs(positions, locations)
            if jobs is not None:
                return jobs
        except Exception:
            pass

        # Strategy 2: Scrape HTML page for structured data
        try:
            return self._scrape_html(positions, locations)
        except Exception:
            pass

        # Both failed — return empty (run continues for other companies)
        return []

    def _fetch_gcs(
        self, positions: list[str], locations: list[str]
    ) -> list[Job] | None:
        all_jobs: list[Job] = []
        seen: set[str] = set()

        for pos in positions:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                resp = requests.post(
                    _GCS_URL,
                    params={"lc": "en_us"},
                    json={
                        "q": pos,
                        "lc": "South Korea",
                        "pg": 1,
                        "pgSz": 20,
                        "o": "Relevance",
                        "flt": True,
                    },
                    headers={**_HEADERS, "Content-Type": "application/json"},
                    timeout=_REQUEST_TIMEOUT,
                    verify=False,
                )

            if not resp.ok or not resp.content:
                return None  # Signal to try next strategy

            try:
                data = resp.json()
            except Exception:
                return None

            for item in data.get("operationResult", {}).get("result", {}).get("jobs", []):
                title: str = item.get("title", "")
                location: str = item.get("primaryLocation", "")

                if not self._matches(title, location, [pos], locations):
                    continue

                job_id = str(item.get("jobId") or item.get("jobNumber") or "")
                if job_id in seen:
                    continue
                seen.add(job_id)

                job_url = _JOB_BASE.format(job_id=job_id) if job_id else self.company_url

                all_jobs.append(
                    Job(
                        company=self.company_name,
                        job_id=job_id,
                        title=title,
                        location=location,
                        url=job_url,
                        description=(item.get("summary") or "")[:500] or None,
                        date_posted=item.get("postingDate", ""),
                        relevance_score=self._position_score(title, positions),
                    )
                )

        return all_jobs

    def _scrape_html(self, positions: list[str], locations: list[str]) -> list[Job]:
        """Scrape the Microsoft careers search page for JSON-LD job data."""
        import json

        jobs: list[Job] = []
        seen: set[str] = set()

        for pos in positions:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
                    resp = requests.get(
                        _SEARCH_PAGE,
                        params={"q": pos, "lc": "South Korea"},
                        headers=_HEADERS,
                        timeout=_REQUEST_TIMEOUT,
                        verify=False,
                    )
                html = resp.text
            except Exception:
                continue

            soup = BeautifulSoup(html, "html.parser")

            for script in soup.find_all("script", {"type": "application/ld+json"}):
                try:
                    data = json.loads(script.string or "")
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if item.get("@type") not in ("JobPosting",):
                            continue
                        title = item.get("title", "")
                        location = item.get("jobLocation", {}).get("address", {}).get(
                            "addressLocality", ""
                        )
                        if not self._matches(title, location, [pos], locations):
                            continue
                        url = item.get("url", "")
                        job_id = url.rstrip("/").split("/")[-1] if url else title
                        if job_id in seen:
                            continue
                        seen.add(job_id)
                        jobs.append(
                            Job(
                                company=self.company_name,
                                job_id=job_id,
                                title=title,
                                location=location,
                                url=url or self.company_url,
                                date_posted=item.get("datePosted", ""),
                                relevance_score=self._position_score(title, positions),
                            )
                        )
                except (json.JSONDecodeError, AttributeError):
                    continue

        return jobs
