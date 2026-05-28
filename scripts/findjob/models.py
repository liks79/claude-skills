"""Data models for FindJob."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    """Represents a single job posting."""

    company: str
    job_id: str
    title: str
    location: str
    url: str
    description: Optional[str] = None
    date_posted: Optional[str] = None
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "company": self.company,
            "job_id": self.job_id,
            "title": self.title,
            "location": self.location,
            "url": self.url,
            "description": self.description,
            "date_posted": self.date_posted,
            "relevance_score": self.relevance_score,
        }


@dataclass
class CompanyResult:
    """Aggregated scan result for one company."""

    company_name: str
    company_url: str
    jobs: list[Job] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def job_count(self) -> int:
        return len(self.jobs)


@dataclass
class ScanResult:
    """Full scan result across all companies."""

    scan_ts: str  # ISO timestamp
    results: list[CompanyResult] = field(default_factory=list)

    @property
    def all_jobs(self) -> list[Job]:
        jobs: list[Job] = []
        for r in self.results:
            jobs.extend(r.jobs)
        return jobs

    @property
    def total_jobs(self) -> int:
        return sum(r.job_count for r in self.results)

    @property
    def companies_with_jobs(self) -> int:
        return sum(1 for r in self.results if r.job_count > 0)

    @property
    def failed_companies(self) -> list[str]:
        return [r.company_name for r in self.results if not r.success]
