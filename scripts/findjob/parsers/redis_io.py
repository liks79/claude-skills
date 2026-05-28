"""Redis.io Careers — HTML scraping with BeautifulSoup fallback + Greenhouse API attempt."""

from __future__ import annotations

from bs4 import BeautifulSoup

from ..models import Job
from .base import JobParser
from .greenhouse import GreenhouseParser

_CAREERS_URL = "https://redis.io/company/careers/current-job-openings/"
_GREENHOUSE_BOARD = "redis"


class RedisParser(JobParser):
    """Tries Greenhouse API first, falls back to HTML scraping."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        # Try Greenhouse API first
        try:
            gh = GreenhouseParser(
                company_name=self.company_name,
                company_url=self.company_url,
                extra={"greenhouse_board": _GREENHOUSE_BOARD},
            )
            jobs = gh.fetch_jobs(locations, positions)
            if jobs:
                return jobs
        except Exception:
            pass

        # Fallback: HTML scrape the Redis careers page
        return self._scrape_html(locations, positions)

    def _scrape_html(self, locations: list[str], positions: list[str]) -> list[Job]:
        try:
            resp = self._get(_CAREERS_URL)
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as exc:
            raise RuntimeError(f"Redis careers HTML scrape failed: {exc}") from exc

        jobs: list[Job] = []
        # Redis renders a list of job postings; try to find job links
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            if "/careers/" not in href and "job" not in href.lower():
                continue

            title = tag.get_text(strip=True)
            if not title:
                # Look for a nearby title element
                parent = tag.find_parent()
                if parent:
                    title = parent.get_text(strip=True)[:120]

            # Try to find location near the link
            location = ""
            parent = tag.find_parent("li") or tag.find_parent("div")
            if parent:
                loc_el = parent.find(string=lambda t: t and ("korea" in t.lower() or "seoul" in t.lower()))
                if loc_el:
                    location = loc_el.strip()

            if not self._matches(title, location or "Seoul, South Korea", positions, locations):
                continue

            full_url = href if href.startswith("http") else f"https://redis.io{href}"
            jobs.append(
                Job(
                    company=self.company_name,
                    job_id=href.rstrip("/").split("/")[-1],
                    title=title,
                    location=location or "Seoul, South Korea",
                    url=full_url,
                    relevance_score=self._position_score(title, positions),
                )
            )

        return jobs
