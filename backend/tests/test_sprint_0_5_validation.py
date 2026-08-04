import subprocess
import unittest
from unittest.mock import Mock

from scripts.validate_sprint_0_5 import (
    VALIDATION_STEPS,
    ValidationResult,
    ValidationStep,
    build_summary,
    run_validation,
)


class Sprint05ValidationTests(unittest.TestCase):
    def test_validation_steps_run_in_expected_order(self):
        self.assertEqual(
            [step.name for step in VALIDATION_STEPS],
            [
                "Environment check",
                "Architecture audit",
                "Dead-code audit",
                "Backend tests",
            ],
        )

    def test_successful_validation_runs_every_step(self):
        runner = Mock(
            side_effect=[
                subprocess.CompletedProcess(step.command, 0)
                for step in VALIDATION_STEPS
            ]
        )

        results = run_validation(runner=runner)

        self.assertEqual(len(results), len(VALIDATION_STEPS))
        self.assertTrue(all(result.passed for result in results))
        self.assertEqual(runner.call_count, len(VALIDATION_STEPS))

    def test_validation_stops_after_first_failure(self):
        steps = (
            ValidationStep("First", ("python", "first.py")),
            ValidationStep("Second", ("python", "second.py")),
            ValidationStep("Third", ("python", "third.py")),
        )
        runner = Mock(
            side_effect=[
                subprocess.CompletedProcess(steps[0].command, 0),
                subprocess.CompletedProcess(steps[1].command, 1),
            ]
        )

        results = run_validation(steps=steps, runner=runner)

        self.assertEqual([result.name for result in results], ["First", "Second"])
        self.assertFalse(results[-1].passed)
        self.assertEqual(runner.call_count, 2)

    def test_summary_passes_only_when_all_default_steps_complete(self):
        results = [
            ValidationResult(step.name, step.command, 0)
            for step in VALIDATION_STEPS
        ]

        summary = build_summary(results)

        self.assertEqual(summary["status"], "PASS")
        self.assertTrue(summary["completed_all_steps"])

    def test_summary_fails_when_a_step_fails(self):
        results = [
            ValidationResult(VALIDATION_STEPS[0].name, VALIDATION_STEPS[0].command, 0),
            ValidationResult(VALIDATION_STEPS[1].name, VALIDATION_STEPS[1].command, 1),
        ]

        summary = build_summary(results)

        self.assertEqual(summary["status"], "FAIL")
        self.assertFalse(summary["completed_all_steps"])
        self.assertFalse(summary["steps"][-1]["passed"])


if __name__ == "__main__":
    unittest.main()
