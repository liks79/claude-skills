"""Google Careers — HTML scraping with structured data extraction.

Google's careers.google.com does not have a stable public JSON API.
We scrape the search results page and extract JSON-LD structured data or
fall back to link-based extraction.
"""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from ..models import Job
from .base import JobParser

_BASE_URL = "https://careers.google.com"
_SEARCH_URL = "https://careers.google.com/jobs/results/"


class GoogleParser(JobParser):
    """Fetches Google jobs by scraping the careers.google.com search page."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        all_jobs: list[Job] = []
        seen: set[str] = set()

        for pos in positions:
            jobs = self._fetch_one_position(pos, locations, positions)
            for j in jobs:
                if j.job_id not in seen:
                    seen.add(j.job_id)
                    all_jobs.append(j)

        return all_jobs

    def _fetch_one_position(
        self, pos: str, locations: list[str], all_positions: list[str]
    ) -> list[Job]:
        params = {
            "q": pos,
            "location": "South Korea",
            "hl": "en_US",
        }
        try:
            resp = self._get(_SEARCH_URL, params=params)
            html = resp.text
        except Exception as exc:
            raise RuntimeError(f"Google careers scrape error: {exc}") from exc

        jobs: list[Job] = []
        soup = BeautifulSoup(html, "html.parser")

        # Strategy 1: JSON-LD structured data
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict) and "@graph" in data:
                    items = data["@graph"]
                else:
                    items = [data]

                for item in items:
                    if item.get("@type") not in ("JobPosting", "jobPosting"):
                        continue
                    title = item.get("title", "")
                    loc_info = item.get("jobLocation", {})
                    if isinstance(loc_info, list):
                        loc_info = loc_info[0] if loc_info else {}
                    address = loc_info.get("address", {})
                    location = address.get("addressLocality", "") + ", " + address.get("addressCountry", "")

                    if not self._matches(title, location, [pos], locations):
                        continue

                    url = item.get("url", item.get("identifier", ""))
                    if not url:
                        continue
                    job_id = url.rstrip("/").split("/")[-1]
                    jobs.append(
                        Job(
                            company=self.company_name,
                            job_id=job_id,
                            title=title,
                            location=location.strip(", "),
                            url=url if url.startswith("http") else _BASE_URL + url,
                            description=item.get("description", "")[:500] or None,
                            date_posted=item.get("datePosted", ""),
                            relevance_score=self._position_score(title, all_positions),
                        )
                    )
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        if jobs:
            return jobs

        # Strategy 2: find job links from HTML
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            if "/jobs/results/" not in href:
                continue
            title = tag.get_text(strip=True)
            if not title:
                continue
            if not self._matches(title, "South Korea", [pos], locations):
                continue
            full_url = href if href.startswith("http") else _BASE_URL + href
            job_id = href.rstrip("/").split("/")[-1].split("?")[0]
            jobs.append(
                Job(
                    company=self.company_name,
                    job_id=job_id,
                    title=title,
                    location="Seoul, South Korea",
                    url=full_url,
                    relevance_score=self._position_score(title, all_positions),
                )
            )

        return jobs
