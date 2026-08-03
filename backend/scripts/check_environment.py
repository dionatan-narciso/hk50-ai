"""Validate the local HK50 AI backend development environment.

Run from the backend directory:

    python scripts/check_environment.py

The checker does not create trading journals or positions. It may create the
configured data root and a short-lived probe file to confirm write access.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Iterable


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime_paths import DATA_ROOT_ENV_VAR, resolve_runtime_paths


MINIMUM_PYTHON = (3, 12)
REQUIRED_IMPORTS = (
    "fastapi",
    "pandas",
    "yfinance",
    "ta",
    "dotenv",
    "textblob",
    "requests",
)
BACKEND_IMPORTS = (
    "app.runtime_paths",
    "app.paper_trade_journal_repository",
    "app.research.director",
    "app.live_signal_engine",
    "app.main",
)


def _result(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail}


def check_python_version(version_info=None) -> dict[str, Any]:
    version = version_info or sys.version_info
    current = (version.major, version.minor)
    passed = current >= MINIMUM_PYTHON
    return _result(
        "python_version",
        passed,
        f"Python {version.major}.{version.minor}.{version.micro}; minimum is "
        f"{MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}",
    )


def check_imports(modules: Iterable[str], *, group_name: str) -> dict[str, Any]:
    failures: list[str] = []
    for module_name in modules:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # report the actual import failure to the developer
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")

    if failures:
        return _result(group_name, False, "; ".join(failures))
    return _result(group_name, True, f"Imported {len(tuple(modules))} modules")


def check_runtime_path_isolation(data_root: str | Path | None = None) -> dict[str, Any]:
    paths = resolve_runtime_paths(data_root)
    paper = paths.paper_dir.resolve()
    replay = paths.replay_dir.resolve()
    live = paths.live_dir.resolve()

    distinct = len({paper, replay, live}) == 3
    children_of_root = all(
        path.parent == paths.data_root.resolve()
        for path in (paper, replay, live)
    )
    passed = distinct and children_of_root
    return _result(
        "runtime_path_isolation",
        passed,
        f"data={paths.data_root}; paper={paper}; replay={replay}; live={live}",
    )


def check_data_root_write_access(data_root: str | Path | None = None) -> dict[str, Any]:
    paths = resolve_runtime_paths(data_root)
    probe = paths.data_root / ".hk50_write_probe"
    try:
        paths.data_root.mkdir(parents=True, exist_ok=True)
        probe.write_text("environment-check", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return _result(
            "data_root_write_access",
            False,
            f"Cannot write to {paths.data_root}: {exc}",
        )

    return _result(
        "data_root_write_access",
        True,
        f"Writable data root: {paths.data_root}",
    )


def run_environment_checks(data_root: str | Path | None = None) -> dict[str, Any]:
    checks = [
        check_python_version(),
        check_imports(REQUIRED_IMPORTS, group_name="required_dependencies"),
        check_imports(BACKEND_IMPORTS, group_name="backend_imports"),
        check_runtime_path_isolation(data_root),
        check_data_root_write_access(data_root),
    ]
    return {
        "status": "ok" if all(check["passed"] for check in checks) else "failed",
        "platform": platform.platform(),
        "python_executable": sys.executable,
        "configured_data_root": str(
            resolve_runtime_paths(data_root).data_root
        ),
        "data_root_environment_variable": os.getenv(DATA_ROOT_ENV_VAR),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        help="Optional isolated data root to validate instead of HK50_DATA_DIR",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )
    args = parser.parse_args()

    report = run_environment_checks(args.data_root)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("HK50 AI environment check")
        print(f"Python executable: {report['python_executable']}")
        print(f"Data root: {report['configured_data_root']}")
        for check in report["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            print(f"[{marker}] {check['name']}: {check['detail']}")
        print(f"Overall status: {report['status'].upper()}")

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
