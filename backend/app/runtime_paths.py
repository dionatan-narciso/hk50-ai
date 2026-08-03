"""Central runtime path definitions for HK50 AI.

Runtime state is separated by execution mode so replay, paper and future live
trading cannot silently share mutable files.
"""

from dataclasses import dataclass
import os
from pathlib import Path


DATA_ROOT_ENV_VAR = "HK50_DATA_DIR"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = BACKEND_ROOT / "data"


@dataclass(frozen=True)
class RuntimePaths:
    """Mode-aware filesystem locations used by runtime state."""

    data_root: Path
    paper_dir: Path
    replay_dir: Path
    live_dir: Path

    paper_trade_journal: Path
    paper_open_position: Path
    paper_last_signal: Path
    paper_entry_learning_memory: Path
    paper_voting_performance_memory: Path
    paper_quality_performance_memory: Path
    paper_strategy_performance_memory: Path
    paper_confidence_calibration_memory: Path
    paper_regime_performance_memory: Path
    paper_research_results: Path

    replay_trade_journal: Path
    replay_learning_memory: Path
    replay_learning_control: Path
    replay_entry_learning_memory: Path
    replay_entry_weight_tuning_log: Path


def resolve_runtime_paths(data_root: str | Path | None = None) -> RuntimePaths:
    """Return normalized runtime paths without creating directories.

    Resolution order:
    1. Explicit ``data_root`` argument.
    2. ``HK50_DATA_DIR`` environment variable.
    3. ``backend/data`` resolved from this module's location.

    The function is intentionally side-effect free so importing configuration
    cannot create or modify trading state.
    """

    configured_root = data_root or os.getenv(DATA_ROOT_ENV_VAR) or DEFAULT_DATA_ROOT
    root = Path(configured_root).expanduser().resolve()

    paper_dir = root / "paper"
    replay_dir = root / "replay"
    live_dir = root / "live"

    return RuntimePaths(
        data_root=root,
        paper_dir=paper_dir,
        replay_dir=replay_dir,
        live_dir=live_dir,
        paper_trade_journal=paper_dir / "trade_journal.csv",
        paper_open_position=paper_dir / "open_position.csv",
        paper_last_signal=paper_dir / "last_signal.csv",
        paper_entry_learning_memory=paper_dir / "entry_learning_memory.csv",
        paper_voting_performance_memory=paper_dir / "voting_performance_memory.csv",
        paper_quality_performance_memory=paper_dir / "quality_performance_memory.csv",
        paper_strategy_performance_memory=paper_dir / "live_strategy_performance.csv",
        paper_confidence_calibration_memory=paper_dir / "confidence_calibration.csv",
        paper_regime_performance_memory=paper_dir / "regime_performance.csv",
        paper_research_results=paper_dir / "research_results.csv",
        replay_trade_journal=replay_dir / "replay_trade_journal.csv",
        replay_learning_memory=replay_dir / "replay_learning_memory.csv",
        replay_learning_control=replay_dir / "replay_learning_control.csv",
        replay_entry_learning_memory=replay_dir / "entry_learning_memory.csv",
        replay_entry_weight_tuning_log=replay_dir / "entry_weight_tuning_log.csv",
    )


RUNTIME_PATHS = resolve_runtime_paths()
