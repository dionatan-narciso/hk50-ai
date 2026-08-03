"""Static architecture audit for HK50 AI production modules.

The audit enforces migration boundaries without changing runtime behaviour.
It identifies forbidden legacy imports, hardcoded mutable-state paths, and
critical production modules that lack a matching test file.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
TEST_ROOT = BACKEND_ROOT / "tests"

FORBIDDEN_RESEARCH_ENGINE_SYMBOLS = {
    "run_research_director",
    "save_trade_journal_entry",
    "run_trade_journal",
    "run_live_learning_feed",
}

# These modules remain transitional owners of research-lab execution.
# Importing lab functions from research_engine is currently allowed.
ALLOWED_RESEARCH_ENGINE_IMPORTERS = {
    "app/main.py",
    "app/research/source_loader.py",
}

CRITICAL_MODULES = {
    "app/live_signal_engine.py": (
        "test_live_signal_engine",
        "test_signal",
    ),
    "app/position_sizing_engine.py": (
        "test_position_sizing",
        "test_risk",
    ),
    "app/daily_risk_manager.py": (
        "test_daily_risk",
        "test_risk",
    ),
    "app/automatic_signal_tracker.py": (
        "test_automatic_signal_tracker",
        "test_signal_tracker",
        "test_paper_position_state",
    ),
    "app/strategy_voting_engine.py": (
        "test_strategy_voting",
        "test_voting",
    ),
}

MUTABLE_PATH_MARKERS = (
    "data/",
    "data\\",
    "trade_journal.csv",
    "open_position.csv",
    "last_signal.csv",
    "performance_memory.csv",
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    line: int
    message: str


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def relative_backend_path(path: Path) -> str:
    return path.resolve().relative_to(BACKEND_ROOT.resolve()).as_posix()


def inspect_imports(path: Path, tree: ast.AST) -> list[Finding]:
    findings: list[Finding] = []
    relative_path = relative_backend_path(path)

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "app.research_engine":
            continue

        imported = {alias.name for alias in node.names}
        forbidden = sorted(imported & FORBIDDEN_RESEARCH_ENGINE_SYMBOLS)
        if forbidden:
            findings.append(Finding(
                severity="error",
                code="FORBIDDEN_LEGACY_IMPORT",
                path=relative_path,
                line=node.lineno,
                message=(
                    "Imports migrated research/journal symbols from "
                    f"app.research_engine: {', '.join(forbidden)}"
                ),
            ))

        if relative_path not in ALLOWED_RESEARCH_ENGINE_IMPORTERS:
            findings.append(Finding(
                severity="warning",
                code="TRANSITIONAL_RESEARCH_ENGINE_IMPORT",
                path=relative_path,
                line=node.lineno,
                message=(
                    "Imports app.research_engine outside the approved lab "
                    "orchestration boundary. Review before removal."
                ),
            ))

    return findings


def inspect_string_paths(path: Path, tree: ast.AST) -> list[Finding]:
    findings: list[Finding] = []
    relative_path = relative_backend_path(path)

    # RuntimePaths itself defines canonical filenames and is exempt.
    if relative_path == "app/runtime_paths.py":
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        value = node.value
        if not any(marker in value for marker in MUTABLE_PATH_MARKERS):
            continue

        findings.append(Finding(
            severity="warning",
            code="HARDCODED_MUTABLE_PATH",
            path=relative_path,
            line=getattr(node, "lineno", 0),
            message=f"Potential hardcoded runtime-state path: {value!r}",
        ))

    return findings


def audit_production_code(app_root: Path = APP_ROOT) -> list[Finding]:
    findings: list[Finding] = []

    for path in iter_python_files(app_root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError) as exc:
            findings.append(Finding(
                severity="error",
                code="PARSE_FAILURE",
                path=relative_backend_path(path),
                line=getattr(exc, "lineno", 0) or 0,
                message=str(exc),
            ))
            continue

        findings.extend(inspect_imports(path, tree))
        findings.extend(inspect_string_paths(path, tree))

    return findings


def audit_critical_test_presence(test_root: Path = TEST_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    test_names = {
        path.stem.lower()
        for path in iter_python_files(test_root)
        if path.name.startswith("test_")
    }

    for module_path, expected_fragments in CRITICAL_MODULES.items():
        if any(
            any(fragment in test_name for fragment in expected_fragments)
            for test_name in test_names
        ):
            continue

        findings.append(Finding(
            severity="warning",
            code="CRITICAL_PATH_TEST_GAP",
            path=module_path,
            line=0,
            message=(
                "No clearly named characterization test was found for this "
                "critical production module."
            ),
        ))

    return findings


def run_audit() -> list[Finding]:
    return audit_production_code() + audit_critical_test_presence()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="Return failure when warnings are present",
    )
    args = parser.parse_args()

    findings = run_audit()
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    if args.json:
        print(json.dumps({
            "status": "fail" if errors else "pass_with_warnings" if warnings else "pass",
            "errors": len(errors),
            "warnings": len(warnings),
            "findings": [asdict(finding) for finding in findings],
        }, indent=2))
    else:
        print("HK50 AI architecture audit")
        print(f"Errors: {len(errors)} | Warnings: {len(warnings)}")
        for finding in findings:
            location = f"{finding.path}:{finding.line}" if finding.line else finding.path
            print(
                f"[{finding.severity.upper()}] {finding.code} "
                f"{location} - {finding.message}"
            )

    if errors or (args.strict_warnings and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
