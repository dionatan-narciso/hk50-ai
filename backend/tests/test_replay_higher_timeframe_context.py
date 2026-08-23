import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.replay_higher_timeframe_context import (
    derive_replay_higher_timeframe_context,
)
from app.replay_higher_timeframe_enrichment import (
    enrich_replay_journal_with_higher_timeframes,
)


def build_history(days=90):
    index = pd.date_range(
        "2026-01-01 00:00:00+00:00",
        periods=days * 24,
        freq="1h",
    )
    close = pd.Series(range(len(index)), index=index, dtype=float) + 20000
    return pd.DataFrame(
        {
            "Open": close - 2,
            "High": close + 5,
            "Low": close - 5,
            "Close": close,
        },
        index=index,
    )


class ReplayHigherTimeframeContextTests(unittest.TestCase):
    def test_context_uses_only_rows_before_entry_timestamp(self):
        history = build_history()
        entry = history.index[-100]
        baseline = derive_replay_higher_timeframe_context(history, entry)

        changed = history.copy()
        changed.loc[changed.index >= entry, "Close"] = 1
        changed.loc[changed.index >= entry, "Open"] = 1
        changed.loc[changed.index >= entry, "High"] = 1
        changed.loc[changed.index >= entry, "Low"] = 1

        after_future_change = derive_replay_higher_timeframe_context(changed, entry)
        self.assertEqual(baseline, after_future_change)

    def test_entry_candle_itself_is_excluded(self):
        history = build_history()
        entry = history.index[-100]
        baseline = derive_replay_higher_timeframe_context(history, entry)

        changed = history.copy()
        changed.loc[entry, ["Open", "High", "Low", "Close"]] = 1

        self.assertEqual(
            baseline,
            derive_replay_higher_timeframe_context(changed, entry),
        )

    def test_uptrend_produces_bullish_4h_and_daily_context_when_enough_history_exists(self):
        history = build_history()
        context = derive_replay_higher_timeframe_context(history, history.index[-1])

        self.assertEqual(context.trend_4h, "Bullish")
        self.assertEqual(context.trend_1d, "Bullish")
        self.assertEqual(context.agreement, "ALIGNED")
        self.assertEqual(context.aligned_direction, "Bullish")

    def test_insufficient_daily_history_is_neutral_not_guessed(self):
        history = build_history(days=20)
        context = derive_replay_higher_timeframe_context(history, history.index[-1])

        self.assertEqual(context.trend_1d, "Neutral")
        self.assertIn(context.agreement, {"PARTIAL", "NEUTRAL"})

    def test_journal_enrichment_is_additive_and_preserves_trade_results(self):
        history = build_history()
        entry_a = history.index[-200]
        entry_b = history.index[-100]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "replay_trade_journal.csv"
            original = pd.DataFrame(
                [
                    {
                        "strategy": "RSI < 30",
                        "opened_at": str(entry_a),
                        "return_percent": 0.5,
                    },
                    {
                        "strategy": "Trend Following",
                        "opened_at": str(entry_b),
                        "return_percent": -0.2,
                    },
                ]
            )
            original.to_csv(path, index=False)

            result = enrich_replay_journal_with_higher_timeframes(history, path)
            enriched = pd.read_csv(path)

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["trades_enriched"], 2)
            self.assertEqual(enriched["return_percent"].tolist(), [0.5, -0.2])
            self.assertEqual(
                enriched["strategy"].tolist(),
                ["RSI < 30", "Trend Following"],
            )
            self.assertIn("context_htf_trend_4h", enriched.columns)
            self.assertIn("context_htf_trend_1d", enriched.columns)
            self.assertIn("context_htf_agreement", enriched.columns)
            self.assertIn("context_htf_aligned_direction", enriched.columns)

    def test_missing_journal_returns_no_data(self):
        history = build_history()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.csv"
            result = enrich_replay_journal_with_higher_timeframes(history, path)

        self.assertEqual(result["status"], "no_data")
        self.assertEqual(result["trades_enriched"], 0)


if __name__ == "__main__":
    unittest.main()
