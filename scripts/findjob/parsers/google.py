"""Google Careers — HTML scraping with AF_initDataCallback data extraction.

Google's careers.google.com embeds job results in AF_initDataCallback JS blocks
rather than JSON-LD. We extract from the ds:1 block which contains the job list.

Direct job URL format:
  https://www.google.com/about/careers/applications/jobs/results/{job_id}
"""

from __future__ import annotations

import re

from ..models import Job
from .base import JobParser

_SEARCH_URL = "https://careers.google.com/jobs/results/"
_JOB_URL = "https://www.google.com/about/careers/applications/jobs/results/{job_id}"

# Pattern to extract all AF_initDataCallback data arrays
_RE_AF_BLOCK = re.compile(
    r"AF_initDataCallback\(\{[^{]+data:(\[.*?)\}\);", re.DOTALL
)
# Split raw ds:1 data block on each job entry (numeric 15+ digit ID)
_RE_JOB_SPLIT = re.compile(r'(?=\["\d{15,}",)')
# Extract job ID + title from start of each block
_RE_JOB_HEADER = re.compile(r'\["(\d{15,})",\s*"([^"]{5,200})"')
# Extract location array: [["Seoul, South Korea", ...]]
_RE_LOCATION = re.compile(r'\[\["([^"]{3,60})"')


class GoogleParser(JobParser):
    """Fetches Google jobs by scraping careers.google.com AF_initDataCallback data."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        all_jobs: list[Job] = []
        seen: set[str] = set()

        for pos in positions:
            for job in self._fetch_one_position(pos, locations, positions):
                if job.job_id not in seen:
                    seen.add(job.job_id)
                    all_jobs.append(job)

        return all_jobs

    def _fetch_one_position(
        self, pos: str, locations: list[str], all_positions: list[str]
    ) -> list[Job]:
        try:
            resp = self._get(
                _SEARCH_URL,
                params={"q": pos, "location": "South Korea", "hl": "en_US"},
            )
            html = resp.text
        except Exception as exc:
            raise RuntimeError(f"Google careers scrape error: {exc}") from exc

        jobs = self._extract_from_af_callback(html, locations, all_positions)
        if jobs:
            return jobs

        # Fallback: JSON-LD (retained for future compatibility)
        return self._extract_from_jsonld(html, pos, locations, all_positions)

    def _extract_from_af_callback(
        self, html: str, locations: list[str], all_positions: list[str]
    ) -> list[Job]:
        """Extract jobs from AF_initDataCallback embedded JS data (Strategy 1)."""
        blocks = _RE_AF_BLOCK.findall(html)
        # ds:1 block (index 1) contains the job list
        if len(blocks) < 2:
            return []

        raw = blocks[1]
        # Split into per-job segments
        segments = _RE_JOB_SPLIT.split(raw)

        jobs: list[Job] = []
        for seg in segments:
            header = _RE_JOB_HEADER.search(seg)
            if not header:
                continue

            job_id = header.group(1)
            title = header.group(2)

            # Location appears as the first [["X"]] array after the job header
            loc_match = _RE_LOCATION.search(seg, header.end())
            location = loc_match.group(1) if loc_match else "Seoul, South Korea"

            if not self._location_matches(location, locations):
                continue

            score = self._position_score(title, all_positions)
            if score <= 0:
                continue

            jobs.append(Job(
                company=self.company_name,
                job_id=job_id,
                title=title,
                location=location,
                url=_JOB_URL.format(job_id=job_id),
                description=None,
                date_posted=None,
                relevance_score=score,
            ))

        return jobs

    def _extract_from_jsonld(
        self, html: str, pos: str, locations: list[str], all_positions: list[str]
    ) -> list[Job]:
        """Fallback: extract from JSON-LD structured data (Strategy 2)."""
        import json
        from bs4 import BeautifulSoup

        jobs: list[Job] = []
        soup = BeautifulSoup(html, "html.parser")

        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "")
                items: list = (
                    data if isinstance(data, list)
                    else data.get("@graph", [data]) if isinstance(data, dict)
                    else []
                )
                for item in items:
                    if item.get("@type") not in ("JobPosting", "jobPosting"):
                        continue
                    title = item.get("title", "")
                    loc_info = item.get("jobLocation") or {}
                    if isinstance(loc_info, list):
                        loc_info = loc_info[0] if loc_info else {}
                    address = loc_info.get("address", {})
                    location = (
                        address.get("addressLocality", "")
                        + ", "
                        + address.get("addressCountry", "")
                    ).strip(", ")

                    if not self._matches(title, location, [pos], locations):
                        continue

                    url = item.get("url") or item.get("identifier") or ""
                    if not url:
                        continue
                    job_id = url.rstrip("/").split("/")[-1]
                    jobs.append(Job(
                        company=self.company_name,
                        job_id=job_id,
                        title=title,
                        location=location,
                        url=url if url.startswith("http") else f"https://careers.google.com{url}",
                        description=(item.get("description") or "")[:500] or None,
                        date_posted=item.get("datePosted", ""),
                        relevance_score=self._position_score(title, all_positions),
                    ))
            except (json.JSONDecodeError, AttributeError, TypeError):
                continue

        return jobs
