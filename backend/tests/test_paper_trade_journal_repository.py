import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from app.daily_risk_manager import check_daily_risk_limits
from app.equity_curve import run_equity_curve
from app.paper_trade_journal_repository import (
    append_paper_trade,
    get_paper_trade_journal_path,
    load_paper_trade_journal,
)
from app.trade_analytics import run_trade_analytics


class PaperTradeJournalRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_root = Path(self.temp_dir.name)
        self.env_patch = patch.dict(os.environ, {"HK50_DATA_DIR": str(self.data_root)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_tracker_schema_is_normalised_for_all_consumers(self):
        closed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = append_paper_trade({
            "signal": "BUY",
            "reason": "RSI < 30",
            "entry_price": 100,
            "exit_price": 101,
            "return_percent": 1.0,
            "result": "TRAILING_PROFIT_EXIT",
            "confidence": 70,
            "vote_strength": 4,
            "closed_at": closed_at,
        })

        self.assertEqual(row["result_pct"], 1.0)
        self.assertEqual(row["strategy"], "RSI < 30")
        self.assertEqual(row["direction"], "BUY")
        self.assertEqual(row["timestamp"], closed_at)

        analytics = run_trade_analytics()
        self.assertEqual(analytics["total_trades"], 1)
        self.assertEqual(analytics["strategy_performance"][0]["strategy"], "RSI < 30")

        equity = run_equity_curve()
        self.assertEqual(equity["current_equity"], 10100.0)
        self.assertEqual(equity["total_return"], 1.0)

        risk = check_daily_risk_limits()
        self.assertEqual(risk["daily_trades"], 1)
        self.assertEqual(risk["daily_return"], 1.0)

    def test_research_schema_is_normalised_for_daily_risk(self):
        append_paper_trade({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategy": "Trend Following",
            "direction": "SELL",
            "result_pct": -0.5,
            "result": "LOSS",
        })

        df = load_paper_trade_journal()
        self.assertEqual(float(df.iloc[0]["return_percent"]), -0.5)
        self.assertEqual(df.iloc[0]["reason"], "Trend Following")
        self.assertEqual(df.iloc[0]["signal"], "SELL")

        risk = check_daily_risk_limits()
        self.assertEqual(risk["daily_losses"], 1)
        self.assertEqual(risk["daily_return"], -0.5)

    def test_legacy_and_replay_files_are_ignored(self):
        legacy = self.data_root / "trade_journal.csv"
        replay = self.data_root / "replay" / "replay_trade_journal.csv"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        replay.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"result_pct": 99}]).to_csv(legacy, index=False)
        pd.DataFrame([{"return_percent": 99}]).to_csv(replay, index=False)

        self.assertEqual(run_trade_analytics(), {"total_trades": 0})
        self.assertEqual(check_daily_risk_limits()["daily_trades"], 0)
        self.assertEqual(run_equity_curve()["current_equity"], 10000)
        self.assertEqual(
            get_paper_trade_journal_path(),
            self.data_root.resolve() / "paper" / "trade_journal.csv",
        )


if __name__ == "__main__":
    unittest.main()
