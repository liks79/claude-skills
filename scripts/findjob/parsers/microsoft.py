"""Microsoft Careers — Eightfold PCSX API.

Uses the internal PCSX search endpoint discovered in the pcsxPwa.js bundle:
  /api/pcsx/search?domain=microsoft.com&query=<q>&location=<loc>&start=<n>

Session cookies (_vs, _vscid) are required and obtained by visiting the
careers homepage first.  The endpoint returns up to 10 positions per page.

Job URL format:
  https://apply.careers.microsoft.com/careers/job/{position_id}
"""

from __future__ import annotations

import requests

from ..models import Job
from .base import JobParser, _HEADERS, _REQUEST_TIMEOUT

_CAREERS_BASE = "https://apply.careers.microsoft.com"
_SEARCH_URL = f"{_CAREERS_BASE}/api/pcsx/search"
_JOB_URL = f"{_CAREERS_BASE}/careers/job/{{position_id}}"
_PAGE_SIZE = 10  # fixed by the API
_MAX_PAGES = 20  # cap at 200 jobs per location


class MicrosoftParser(JobParser):
    """Fetches Microsoft Korea jobs via the Eightfold PCSX search API.

    Searches across Korea-based locations (Seoul and others) using the
    private-but-unauthenticated /api/pcsx/search endpoint.
    """

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        session = self._make_session()
        raw = self._fetch_korea_jobs(session)
        return self._filter_and_score(raw, locations, positions)

    def _make_session(self) -> requests.Session:
        """Establish session cookies by visiting the careers homepage."""
        session = requests.Session()
        session.headers.update(_HEADERS)
        session.headers.update({
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Referer": _CAREERS_BASE,
        })
        try:
            session.get(f"{_CAREERS_BASE}/careers", timeout=_REQUEST_TIMEOUT)
        except Exception:
            pass  # proceed without cookies — may still work
        session.headers["Accept"] = "application/json, */*"
        return session

    def _fetch_korea_jobs(self, session: requests.Session) -> list[dict]:
        """Paginate through all Korea-based positions."""
        all_items: list[dict] = []
        seen_ids: set[int] = set()

        for location in ("Seoul", "Korea"):
            for page in range(_MAX_PAGES):
                start = page * _PAGE_SIZE
                try:
                    resp = session.get(
                        _SEARCH_URL,
                        params={
                            "domain": "microsoft.com",
                            "query": "",
                            "location": location,
                            "start": start,
                        },
                        timeout=_REQUEST_TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:
                    raise RuntimeError(
                        f"Microsoft PCSX API error (location={location}, start={start}): {exc}"
                    ) from exc

                batch: list[dict] = data.get("data", {}).get("positions") or []
                for item in batch:
                    pid = item.get("id")
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_items.append(item)

                if len(batch) < _PAGE_SIZE:
                    break  # last page for this location

        return all_items

    def _filter_and_score(
        self,
        raw: list[dict],
        locations: list[str],
        positions: list[str],
    ) -> list[Job]:
        """Filter by location and score by position relevance."""
        jobs: list[Job] = []

        for item in raw:
            title: str = item.get("name", "")
            position_id = item.get("id", "")
            ats_job_id: str = item.get("displayJobId") or item.get("atsJobId") or str(position_id)
            job_locs: list[str] = item.get("locations") or []

            location_str = ", ".join(job_locs) if job_locs else ""

            if not self._location_matches(location_str, locations):
                continue

            score = self._position_score(title, positions)
            if score <= 0:
                continue

            jobs.append(Job(
                company=self.company_name,
                job_id=ats_job_id,
                title=title,
                location=job_locs[0] if job_locs else "Seoul, South Korea",
                url=_JOB_URL.format(position_id=position_id),
                description=None,
                date_posted=None,
                relevance_score=score,
            ))

        return jobs
