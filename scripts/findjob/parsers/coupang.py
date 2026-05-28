"""Coupang Careers — Greenhouse ATS (board: 'coupang').

coupang.jobs uses the Greenhouse ATS (confirmed by gh_jid= params in job URLs
and the boards-api endpoint returning 527 total / 239 Korea jobs).

The SmartRecruiters API does not work for Coupang — Greenhouse is the correct source.
"""

from __future__ import annotations

from ..models import Job
from .greenhouse import GreenhouseParser


class CoupangParser(GreenhouseParser):
    """Fetches Coupang jobs via the Greenhouse API. Board name: 'coupang'."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        self.extra.setdefault("greenhouse_board", "coupang")
        self.board = self.extra["greenhouse_board"]
        return super().fetch_jobs(locations, positions)
