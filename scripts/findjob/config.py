"""Load FindJob configuration from the command definition file."""

import os
import re
from pathlib import Path
from typing import Any

import yaml


# Default command file: go up from scripts/findjob/ → scripts/ → repo-root/ → commands/findjob.md
# Works both in dev (repo root) and as installed plugin (plugin cache root).
_DEFAULT_COMMAND_FILE = Path(__file__).parent.parent.parent / "commands" / "findjob.md"


def _find_config_block(text: str) -> str:
    """Extract the findjob-config YAML block from markdown."""
    pattern = re.compile(
        r"```yaml\s*\n(.*?# findjob-config.*?)\n```",
        re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(text)
    if m:
        return m.group(1)

    # Fallback: first ```yaml block
    pattern2 = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)
    m2 = pattern2.search(text)
    if m2:
        return m2.group(1)

    raise ValueError(
        "No YAML config block found in the command file. "
        "Make sure the file contains a ```yaml block with '# findjob-config'."
    )


def load_config(config_file: str | Path | None = None) -> dict[str, Any]:
    """Load and parse FindJob configuration.

    Priority:
    1. ``config_file`` argument
    2. ``FINDJOB_CONFIG_FILE`` environment variable
    3. Default command file path (relative to this script's location)

    Returns a dict with keys:
      - ``wanted_locations``: list[str]
      - ``wanted_positions``: list[str]
      - ``companies``: list[dict]
      - ``min_match_score``: float
    """
    if config_file is None:
        env_path = os.environ.get("FINDJOB_CONFIG_FILE")
        config_file = Path(env_path) if env_path else _DEFAULT_COMMAND_FILE

    config_file = Path(config_file)
    if not config_file.exists():
        raise FileNotFoundError(
            f"FindJob config file not found: {config_file}\n"
            "Set FINDJOB_CONFIG_FILE env var or pass --config."
        )

    raw = config_file.read_text(encoding="utf-8")
    yaml_block = _find_config_block(raw)
    cfg: dict[str, Any] = yaml.safe_load(yaml_block) or {}

    cfg.setdefault("wanted_locations", [])
    cfg.setdefault("wanted_positions", [])
    cfg.setdefault("companies", [])
    cfg.setdefault("min_match_score", 0.40)

    return cfg


def resolve_output_dir(cli_arg: str | None = None) -> Path:
    """Resolve the output directory: CLI arg → env var → BASE_DIR → default."""
    if cli_arg:
        return Path(cli_arg)
    env = os.environ.get("FINDJOB_OUTPUT_DIR")
    if env:
        return Path(env)
    base_dir = os.environ.get("BASE_DIR")
    if base_dir:
        return Path(base_dir) / "career" / "job-search" / "findjob"
    return Path("career/job-search/findjob")


def resolve_db_path(cli_arg: str | None = None, output_dir: Path | None = None) -> Path:
    """Resolve the SQLite DB path: CLI arg → env var → default inside output_dir."""
    if cli_arg:
        return Path(cli_arg)
    env = os.environ.get("FINDJOB_DB_PATH")
    if env:
        return Path(env)
    base = output_dir or resolve_output_dir()
    return base / "jobs.db"
