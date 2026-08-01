"""Modular Research Director entry point.

This adapter preserves the legacy Research Director implementation while
redirecting its hard-coded strategy-performance read to the canonical paper
runtime path. It is intentionally temporary: later batches can extract the
remaining ranking logic behind the same public function.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

from app.live_performance_memory import get_strategy_performance_path
from app.research_engine import run_research_director as run_legacy_research_director


LEGACY_STRATEGY_PERFORMANCE_PATHS = {
    "data/live_strategy_performance.csv",
    "backend/data/live_strategy_performance.csv",
}


@contextmanager
def _canonical_strategy_performance_read():
    """Redirect only the legacy strategy-memory CSV read during one call."""
    original_read_csv = pd.read_csv
    canonical_path = get_strategy_performance_path()

    def read_csv_with_runtime_path(filepath_or_buffer: Any, *args: Any, **kwargs: Any):
        path_text = str(filepath_or_buffer).replace("\\", "/")
        if path_text in LEGACY_STRATEGY_PERFORMANCE_PATHS:
            filepath_or_buffer = canonical_path
        return original_read_csv(filepath_or_buffer, *args, **kwargs)

    pd.read_csv = read_csv_with_runtime_path
    try:
        yield
    finally:
        pd.read_csv = original_read_csv


def run_research_director():
    """Run the existing Research Director against canonical paper memory."""
    with _canonical_strategy_performance_read():
        return run_legacy_research_director()
