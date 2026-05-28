"""Parser registry — maps parser key → parser class."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import JobParser


def get_parser(
    parser_key: str,
    company_name: str,
    company_url: str,
    extra: dict,
) -> "JobParser":
    """Instantiate the correct parser for the given key."""
    # Import lazily to avoid circular imports and speed up startup
    from .aws import AWSParser
    from .anthropic import AnthropicParser
    from .cloudflare import CloudflareParser
    from .coupang import CoupangParser
    from .databricks import DatabricksParser
    from .datadog import DatadogParser
    from .google import GoogleParser
    from .microsoft import MicrosoftParser
    from .openai import OpenAIParser
    from .palantir import PalantirParser
    from .redis_io import RedisParser

    registry: dict[str, type] = {
        "aws": AWSParser,
        "google": GoogleParser,
        "microsoft": MicrosoftParser,
        "redis_io": RedisParser,
        "datadog": DatadogParser,
        "databricks": DatabricksParser,
        "palantir": PalantirParser,
        "cloudflare": CloudflareParser,
        "anthropic": AnthropicParser,
        "openai": OpenAIParser,
        "coupang": CoupangParser,
    }

    cls = registry.get(parser_key)
    if cls is None:
        raise ValueError(f"Unknown parser key: {parser_key!r}. Available: {list(registry)}")

    return cls(company_name=company_name, company_url=company_url, extra=extra)
