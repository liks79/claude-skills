"""Anthropic Careers — Greenhouse ATS (board: 'anthropic')."""

from __future__ import annotations

from ..models import Job
from .greenhouse import GreenhouseParser


class AnthropicParser(GreenhouseParser):
    """Anthropic uses the Greenhouse ATS. Board name: 'anthropic'."""

    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        self.extra.setdefault("greenhouse_board", "anthropic")
        self.board = self.extra["greenhouse_board"]
        return super().fetch_jobs(locations, positions)
