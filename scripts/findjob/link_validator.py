"""Parallel HTTP link validator for job posting URLs.

Checks each job URL concurrently and returns only the jobs whose links
are still accessible.  A job is considered invalid when:
  - HTTP 4xx / 5xx (excluding transient errors like 429/503)
  - Response body contains well-known "job closed" phrases
"""

from __future__ import annotations

import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .models import Job

_TIMEOUT = 12         # seconds per request
_MAX_WORKERS = 20     # concurrent requests
_MAX_BODY_BYTES = 65_536  # read up to 64 KB for content checks

_CLOSED_PHRASES: list[str] = [
    "job is no longer available",
    "this job has expired",
    "job has been filled",
    "position has been filled",
    "no longer accepting applications",
    "job posting has been removed",
    "this position is no longer open",
    "this job is no longer active",
    "the job you are looking for is no longer available",
    "this opening is no longer available",
    "sorry, this job has expired",
    "this job listing has expired",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _check_url(url: str) -> tuple[str, bool, str]:
    """Return (url, is_valid, reason)."""
    try:
        with requests.get(
            url,
            headers=_HEADERS,
            timeout=_TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as resp:
            status = resp.status_code

            if status == 404:
                return url, False, "HTTP 404 Not Found"
            if status == 410:
                return url, False, "HTTP 410 Gone"

            # Rate-limit / server errors → optimistically assume valid
            if status == 429 or status >= 500:
                return url, True, f"HTTP {status} (assumed valid)"

            if status >= 400:
                return url, False, f"HTTP {status}"

            # Detect redirect-away: ATS systems redirect closed jobs to the
            # company career homepage (different domain or much shorter path).
            final_url = resp.url
            if final_url and final_url != url:
                from urllib.parse import urlparse

                orig_p = urlparse(url)
                final_p = urlparse(final_url)
                orig_domain = orig_p.netloc.lower()
                final_domain = final_p.netloc.lower()

                def _apex(domain: str) -> str:
                    parts = domain.lstrip("www.").split(".")
                    return ".".join(parts[-2:]) if len(parts) >= 2 else domain

                if _apex(orig_domain) != _apex(final_domain):
                    return url, False, f"Redirected to different domain: {final_url}"

                orig_path = orig_p.path.rstrip("/")
                final_path = final_p.path.rstrip("/")
                if orig_path and final_path and len(final_path) < len(orig_path) - 10:
                    return url, False, f"Redirected to shorter path: {final_url}"

            raw = b""
            for chunk in resp.iter_content(chunk_size=4096):
                raw += chunk
                if len(raw) >= _MAX_BODY_BYTES:
                    break

            body = raw.decode("utf-8", errors="replace").lower()
            for phrase in _CLOSED_PHRASES:
                if phrase in body:
                    return url, False, f"Closed phrase detected: '{phrase}'"

            return url, True, "OK"

    except requests.exceptions.Timeout:
        return url, True, "Timeout (assumed valid)"
    except requests.exceptions.ConnectionError as exc:
        return url, False, f"Connection error: {exc}"
    except Exception as exc:
        return url, True, f"Error (assumed valid): {exc}"


def validate_jobs(
    jobs: list[Job],
    max_workers: int = _MAX_WORKERS,
    eprint=None,
) -> tuple[list[Job], list[Job]]:
    """Validate job URLs in parallel.

    Returns:
        (valid_jobs, invalid_jobs)
    """
    if eprint is None:
        def eprint(*args):
            print(*args, file=sys.stderr)

    if not jobs:
        return [], []

    eprint(f"[findjob] 🔗 Validating {len(jobs)} job links (parallel, timeout={_TIMEOUT}s)...")

    url_to_jobs: dict[str, list[Job]] = {}
    for job in jobs:
        url_to_jobs.setdefault(job.url, []).append(job)

    unique_urls = list(url_to_jobs.keys())
    results: dict[str, bool] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(_check_url, url): url for url in unique_urls}
        for future in as_completed(future_to_url):
            url, is_valid, reason = future.result()
            results[url] = is_valid
            if not is_valid:
                short = url if len(url) <= 90 else url[:87] + "..."
                eprint(f"[findjob]   ✂️  Removed: {short}")
                eprint(f"[findjob]              Reason : {reason}")

    valid_jobs = [j for j in jobs if results.get(j.url, True)]
    invalid_jobs = [j for j in jobs if not results.get(j.url, True)]

    eprint(
        f"[findjob] 🔗 Validation done: "
        f"{len(valid_jobs)} valid, {len(invalid_jobs)} removed"
    )
    return valid_jobs, invalid_jobs
