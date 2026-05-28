"""Datadog Careers — Greenhouse ATS."""

from __future__ import annotations

from ..models import Job
from .greenhouse import GreenhouseParser


class DatadogParser(GreenhouseParser):
    """Datadog uses the Greenhouse ATS. Board name: 'datadog'."""

    # Greenhouse board is set via extra['greenhouse_board'] in config
    # Default fallback if not specified:
    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        if "greenhouse_board" not in self.extra:
            self.extra["greenhouse_board"] = "datadog"
        self.board = self.extra["greenhouse_board"]
        return super().fetch_jobs(locations, positions)
