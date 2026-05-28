"""Cloudflare Careers — Greenhouse ATS."""

from __future__ import annotations

from ..models import Job
from .greenhouse import GreenhouseParser


class CloudflareParser(GreenhouseParser):
    """Cloudflare uses the Greenhouse ATS. Board name: 'cloudflare'."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        if "greenhouse_board" not in self.extra:
            self.extra["greenhouse_board"] = "cloudflare"
        self.board = self.extra["greenhouse_board"]
        return super().fetch_jobs(locations, positions)
