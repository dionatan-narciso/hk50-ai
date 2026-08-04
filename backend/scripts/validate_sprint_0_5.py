"""Run every Sprint 0.5 baseline validation gate in a fixed order."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence


BACKEND_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ValidationStep:
    name: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class ValidationResult:
    name: str
    command: tuple[str, ...]
    return_code: int

    @property
    def passed(self) -> bool:
        return self.return_code == 0


VALIDATION_STEPS = (
    ValidationStep(
        "Environment check",
        (sys.executable, "scripts/check_environment.py"),
    ),
    ValidationStep(
        "Architecture audit",
        (sys.executable, "scripts/audit_architecture.py"),
    ),
    ValidationStep(
        "Dead-code audit",
        (sys.executable, "scripts/audit_dead_code.py"),
    ),
    ValidationStep(
        "Backend tests",
        (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"),
    ),
)


def run_validation(
    steps: Sequence[ValidationStep] = VALIDATION_STEPS,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[ValidationResult]:
    """Run validation steps in order and stop after the first failure."""

    results: list[ValidationResult] = []

    for step in steps:
        print(f"\n=== {step.name} ===")
        completed = runner(step.command, cwd=BACKEND_ROOT, check=False)
        result = ValidationResult(step.name, step.command, completed.returncode)
        results.append(result)

        if not result.passed:
            break

    return results


def build_summary(results: Sequence[ValidationResult]) -> dict:
    passed = bool(results) and all(result.passed for result in results)
    completed_all = len(results) == len(VALIDATION_STEPS)

    return {
        "status": "PASS" if passed and completed_all else "FAIL",
        "completed_all_steps": completed_all,
        "steps": [
            {
                **asdict(result),
                "command": list(result.command),
                "passed": result.passed,
            }
            for result in results
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run all Sprint 0.5 baseline validation gates."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final summary as JSON.",
    )
    args = parser.parse_args(argv)

    results = run_validation()
    summary = build_summary(results)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("\n=== Sprint 0.5 Baseline ===")
        print(summary["status"])
        for step in summary["steps"]:
            marker = "PASS" if step["passed"] else "FAIL"
            print(f"[{marker}] {step['name']}")

    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
