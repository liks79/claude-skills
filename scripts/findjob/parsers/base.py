"""Abstract base class for job site parsers — with improved title matching."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

import requests

from ..models import Job

# Common browser-like headers to avoid simple bot rejection
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

_REQUEST_TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Matching helpers (module-level for reuse / testability)
# ---------------------------------------------------------------------------

def _stem(word: str) -> str:
    """Minimal English suffix stripping for fuzzy word matching.

    Strips common noun/verb endings so that "solution" matches "solutions",
    "architect" matches "architecture", "deploy" matches "deployed", etc.
    """
    if len(word) <= 3:
        return word
    # Longer suffixes first to avoid partial stripping
    for sfx in ("tions", "tion", "ments", "ment", "ness", "ings", "ies",
                "ing", "ers", "ion", "es", "ed", "s"):
        if word.endswith(sfx) and len(word) - len(sfx) >= 3:
            return word[: -len(sfx)]
    return word


def _tokenize(text: str) -> set[str]:
    """Split text into stemmed tokens, ignoring short words and punctuation."""
    words = re.split(r"[\s,./|\-–()\[\]]+", text.lower())
    return {_stem(w) for w in words if len(w) >= 3}


# Role alias patterns: (compiled_regex_for_job_title, canonical_wanted_position)
# If the regex matches the job title, treat the job as qualifying for the canonical position.
_ROLE_ALIASES: list[tuple[re.Pattern[str], str]] = [
    # Solutions Architect variants
    (re.compile(r"\bsolution\s+architect"),              "solutions architect"),
    (re.compile(r"\bcloud\s+architect"),                 "solutions architect"),
    (re.compile(r"\bplatform\s+architect"),              "solutions architect"),
    (re.compile(r"\btechnical\s+architect"),             "solutions architect"),
    (re.compile(r"\benterprise\s+architect"),            "solutions architect"),
    (re.compile(r"\binfrastructure\s+architect"),        "solutions architect"),
    (re.compile(r"\b(?<!\w)sa(?!\w)"),                   "solutions architect"),  # standalone "SA"
    # Forward Deployed Engineer / FDE
    (re.compile(r"\bforward\s+deployed"),                "forward deployed engineer"),
    (re.compile(r"\bfde\b"),                             "forward deployed engineer"),
    # Senior / Staff / Principal Engineer → "Senior Engineer" family
    (re.compile(r"\bstaff\s+engineer"),                  "senior engineer"),
    (re.compile(r"\bprincipal\s+engineer"),              "senior engineer"),
    (re.compile(r"\bsr\.?\s*engineer"),                  "senior engineer"),
    (re.compile(r"\bsenior\s+software\s+engineer"),      "senior engineer"),
    (re.compile(r"\bsenior\s+swe\b"),                    "senior engineer"),
    # Engineering Manager / SDM
    (re.compile(r"\bsdm\b"),                             "engineering manager"),
    (re.compile(r"\b(?<!\w)em(?!\w)"),                   "engineering manager"),
    (re.compile(r"\bdevelopment\s+manager"),             "engineering manager"),
    (re.compile(r"\btech(?:nical)?\s+lead\s+manager"),   "engineering manager"),
    (re.compile(r"\bsdm\b"),                             "software development manager"),
    (re.compile(r"\bengineering\s+manager"),             "software development manager"),
    # Technical Project/Program Manager
    (re.compile(r"\btechnical\s+program\s+manager"),     "technical project manager"),
    (re.compile(r"\bprogram\s+manager"),                 "technical project manager"),
    (re.compile(r"\btpm\b"),                             "technical project manager"),
    # DevOps / SRE / Platform / Infrastructure
    (re.compile(r"\bsite\s+reliability"),                "devops engineer"),
    (re.compile(r"\bsre\b"),                             "devops engineer"),
    (re.compile(r"\bcloud\s+engineer"),                  "devops engineer"),
    (re.compile(r"\binfrastructure\s+engineer"),         "platform engineer"),
    (re.compile(r"\bsre\b"),                             "platform engineer"),
    # Director / VP / Head of ...
    (re.compile(r"\bhead\s+of\s+engineer"),              "director"),
    (re.compile(r"\bhead\s+of\s+platform"),              "director"),
    (re.compile(r"\bhead\s+of\s+infrastructure"),        "director"),
    (re.compile(r"\bvp\s+(?:of\s+)?engineer"),           "director"),
    (re.compile(r"\bvice\s+president"),                  "director"),
    (re.compile(r"\bvp\s+of\s+"),                        "director"),
    # Staff / Principal for "Staff Engineer" position
    (re.compile(r"\bstaff\s+"),                          "staff engineer"),
    (re.compile(r"\bprincipal\s+"),                      "principal engineer"),
]

# Abbreviation → full canonical form (checked against wanted_positions)
_ABBREV_MAP: dict[str, str] = {
    "fde":  "forward deployed engineer",
    "sdm":  "software development manager",
    "tpm":  "technical project manager",
    "em":   "engineering manager",
    "sa":   "solutions architect",
    "sre":  "devops engineer",
    "swe":  "senior engineer",
}


class JobParser(ABC):
    """Base class for all company-specific job parsers."""

    def __init__(self, company_name: str, company_url: str, extra: dict[str, Any]) -> None:
        self.company_name = company_name
        self.company_url = company_url
        self.extra = extra

    @abstractmethod
    def fetch_jobs(self, locations: list[str], positions: list[str]) -> list[Job]:
        """Fetch and return jobs filtered by location and position keywords."""

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Any = None, **kwargs: Any) -> requests.Response:
        """GET with default headers and timeout."""
        resp = requests.get(
            url,
            params=params,
            headers=_HEADERS,
            timeout=_REQUEST_TIMEOUT,
            **kwargs,
        )
        resp.raise_for_status()
        return resp

    def _post(self, url: str, json: dict | None = None, **kwargs: Any) -> requests.Response:
        """POST with default headers and timeout."""
        resp = requests.post(
            url,
            json=json,
            headers=_HEADERS,
            timeout=_REQUEST_TIMEOUT,
            **kwargs,
        )
        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Location matching
    # ------------------------------------------------------------------

    def _location_matches(self, location: str, wanted_locations: list[str]) -> bool:
        """True if *location* contains any wanted location string (case-insensitive)."""
        if not wanted_locations:
            return True
        loc_lower = location.lower()
        return any(wl.lower() in loc_lower for wl in wanted_locations)

    # ------------------------------------------------------------------
    # Position scoring (improved)
    # ------------------------------------------------------------------

    def _position_score(self, title: str, wanted_positions: list[str]) -> float:
        """Return a 0–1 relevance score for a job title vs wanted positions.

        Scoring strategy (highest matching score wins):
          1.00  Exact phrase match (case-insensitive)
          0.95  Role alias pattern matches (e.g. "solution architect" → "solutions architect")
          0.90  All stemmed position-words found in title tokens
          0.60–0.85  Partial word coverage (≥60% of position keywords present)
          0.25–0.59  Low partial match (≥30% of keywords)
          0.00  No meaningful overlap
        """
        if not wanted_positions:
            return 0.5

        title_lower = title.lower()
        wanted_lower = [p.lower() for p in wanted_positions]
        title_tokens = _tokenize(title)
        best = 0.0

        # ── Pass 1: exact phrase match ─────────────────────────────────
        for pos_lower in wanted_lower:
            if pos_lower in title_lower:
                return 1.0

        # ── Pass 2: role alias patterns ───────────────────────────────
        for pattern, canonical in _ROLE_ALIASES:
            if canonical not in wanted_lower:
                continue
            if pattern.search(title_lower):
                best = max(best, 0.95)

        if best >= 0.95:
            return round(best, 3)

        # ── Pass 3: abbreviation check ────────────────────────────────
        title_words = set(re.split(r"\W+", title_lower))
        for abbrev, expansion in _ABBREV_MAP.items():
            if expansion not in wanted_lower:
                continue
            if abbrev in title_words:
                best = max(best, 0.90)

        # ── Pass 4: word-level match with stemming ────────────────────
        for pos_lower in wanted_lower:
            pos_stems = [_stem(w) for w in re.split(r"\s+", pos_lower) if len(w) >= 3]
            if not pos_stems:
                continue

            matched = sum(1 for ps in pos_stems if ps in title_tokens)
            coverage = matched / len(pos_stems)

            if coverage >= 1.0:
                best = max(best, 0.90)
            elif coverage >= 0.60:
                best = max(best, coverage * 0.85)
            elif coverage >= 0.30:
                best = max(best, coverage * 0.65)

        return round(best, 3)

    def _matches(
        self,
        title: str,
        location: str,
        wanted_positions: list[str],
        wanted_locations: list[str],
        min_score: float = 0.0,
    ) -> bool:
        """Return True if the job passes both location and position filters."""
        if not self._location_matches(location, wanted_locations):
            return False
        score = self._position_score(title, wanted_positions)
        return score > min_score

    def _strip_html(self, html: str) -> str:
        """Very lightweight HTML tag stripper."""
        return re.sub(r"<[^>]+>", " ", html).strip()
