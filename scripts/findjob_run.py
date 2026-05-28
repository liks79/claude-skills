#!/usr/bin/env python3
"""Launcher wrapper for findjob package.

Run as:  uv run python scripts/findjob_run.py [--output-dir ...] [--db-path ...] [--config ...]

This wrapper adds the scripts directory to sys.path so that the `findjob`
package (using relative imports) can be imported correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add scripts/ to sys.path so `import findjob.*` works
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

import runpy

runpy.run_module("findjob.run", run_name="__main__", alter_sys=True)
