"""Amazon Web Services — amazon.jobs JSON search API.

Fix: Use `normalized_country_code[]=KOR` instead of `loc_query=Korea`.
This returns all Korea-based jobs (69 as of 2026-05) in a single request.
We then filter locally by position score.
"""

from __future__ import annotations

import requests

from ..models import Job
from .base import JobParser, _HEADERS, _REQUEST_TIMEOUT

_SEARCH_URL = "https://www.amazon.jobs/en/search.json"
_JOB_BASE = "https://www.amazon.jobs"
_JOB_URL_FALLBACK = "https://www.amazon.jobs/en/jobs/{job_id}"


class AWSParser(JobParser):
    """Fetches all Korea AWS jobs via normalized_country_code filter, then matches locally."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        all_items = self._fetch_all_korea_jobs()

        jobs: list[Job] = []
        seen: set[str] = set()

        for item in all_items:
            title: str = item.get("title", "")
            normalized_location = item.get("normalized_location")
            if isinstance(normalized_location, list):
                location = ", ".join(normalized_location) if normalized_location else item.get("location", "")
            elif isinstance(normalized_location, str):
                location = normalized_location or item.get("location", "")
            else:
                location = item.get("location", "")

            score = self._position_score(title, positions)
            if score <= 0:
                continue

            # Prefer id_icims (numeric, stable) over UUID-style id
            job_id = str(item.get("id_icims") or item.get("id") or item.get("job_id") or "")
            if job_id in seen:
                continue
            seen.add(job_id)

            # Use job_path (slug URL) if available — UUID-based URLs return 404
            job_path = item.get("job_path", "")
            if job_path:
                job_url = f"{_JOB_BASE}{job_path}"
            elif job_id:
                job_url = _JOB_URL_FALLBACK.format(job_id=job_id)
            else:
                job_url = self.company_url
            raw_desc = item.get("description_short") or item.get("description") or ""
            desc = self._strip_html(raw_desc)[:500] if raw_desc else None

            jobs.append(
                Job(
                    company=self.company_name,
                    job_id=job_id,
                    title=title,
                    location=location,
                    url=job_url,
                    description=desc,
                    date_posted=item.get("posted_date", ""),
                    relevance_score=score,
                )
            )

        return jobs

    def _fetch_all_korea_jobs(self) -> list[dict]:
        """Bulk-fetch all Korea-based jobs using the normalized_country_code filter.

        Amazon's API returns up to `result_limit` results per page.  We paginate
        until we've received all jobs or hit a 500-job safety cap.
        """
        all_items: list[dict] = []
        page_size = 100
        offset = 0
        safety_cap = 500  # prevent infinite loops

        while offset < safety_cap:
            # `params` must be a list-of-tuples because `[]` keys are repeated
            params: list[tuple[str, str]] = [
                ("normalized_country_code[]", "KOR"),
                ("result_limit", str(page_size)),
                ("job_count", "10"),
                ("radius", "24km"),
                ("offset", str(offset)),
            ]
            try:
                resp = requests.get(
                    _SEARCH_URL,
                    params=params,
                    headers=_HEADERS,
                    timeout=_REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                raise RuntimeError(f"AWS Jobs API error (offset={offset}): {exc}") from exc

            page_jobs: list[dict] = data.get("jobs") or []
            all_items.extend(page_jobs)

            total_hits: int = int(data.get("hits") or len(all_items))
            if len(all_items) >= total_hits or len(page_jobs) < page_size:
                break  # received all results

            offset += page_size

        return all_items
