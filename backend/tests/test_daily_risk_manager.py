import unittest
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from app import daily_risk_manager


class DailyRiskManagerTests(unittest.TestCase):
    def test_empty_journal_returns_no_today_trades(self):
        with patch.object(
            daily_risk_manager,
            "load_paper_trade_journal",
            return_value=pd.DataFrame(),
        ):
            self.assertEqual(daily_risk_manager.get_today_trades(), [])

    def test_missing_closed_at_column_returns_no_today_trades(self):
        journal = pd.DataFrame([{"return_percent": 1.0}])

        with patch.object(
            daily_risk_manager,
            "load_paper_trade_journal",
            return_value=journal,
        ):
            self.assertEqual(daily_risk_manager.get_today_trades(), [])

    def test_only_trades_closed_today_are_returned(self):
        today = datetime.now().strftime("%Y-%m-%d")
        journal = pd.DataFrame(
            [
                {"closed_at": f"{today} 10:00:00", "return_percent": 1.0},
                {"closed_at": "2000-01-01 10:00:00", "return_percent": -1.0},
            ]
        )

        with patch.object(
            daily_risk_manager,
            "load_paper_trade_journal",
            return_value=journal,
        ):
            trades = daily_risk_manager.get_today_trades()

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]["return_percent"], 1.0)
        self.assertEqual(trades[0]["closed_date"], today)

    def test_five_trades_blocks_before_other_limits(self):
        trades = [
            {"return_percent": 1.0},
            {"return_percent": 1.0},
            {"return_percent": 1.0},
            {"return_percent": 1.0},
            {"return_percent": 1.0},
        ]

        with patch.object(daily_risk_manager, "get_today_trades", return_value=trades):
            result = daily_risk_manager.check_daily_risk_limits()

        self.assertFalse(result["allow_trade"])
        self.assertEqual(result["reason"], "Daily trade limit reached.")
        self.assertEqual(result["daily_trades"], 5)
        self.assertEqual(result["daily_losses"], 0)
        self.assertEqual(result["daily_return"], 5.0)

    def test_three_non_positive_results_trigger_loss_limit(self):
        trades = [
            {"return_percent": -0.2},
            {"return_percent": 0},
            {"return_percent": -0.3},
        ]

        with patch.object(daily_risk_manager, "get_today_trades", return_value=trades):
            result = daily_risk_manager.check_daily_risk_limits()

        self.assertFalse(result["allow_trade"])
        self.assertEqual(result["reason"], "Daily loss limit reached.")
        self.assertEqual(result["daily_losses"], 3)
        self.assertEqual(result["daily_return"], -0.5)

    def test_drawdown_limit_triggers_at_exactly_minus_two(self):
        trades = [
            {"return_percent": -1.25},
            {"return_percent": -0.75},
        ]

        with patch.object(daily_risk_manager, "get_today_trades", return_value=trades):
            result = daily_risk_manager.check_daily_risk_limits()

        self.assertFalse(result["allow_trade"])
        self.assertEqual(result["reason"], "Daily drawdown limit reached.")
        self.assertEqual(result["daily_losses"], 2)
        self.assertEqual(result["daily_return"], -2.0)

    def test_trading_is_allowed_below_all_limits_and_return_is_rounded(self):
        trades = [
            {"return_percent": "0.3333"},
            {"return_percent": "-0.1111"},
        ]

        with patch.object(daily_risk_manager, "get_today_trades", return_value=trades):
            result = daily_risk_manager.check_daily_risk_limits()

        self.assertTrue(result["allow_trade"])
        self.assertEqual(result["reason"], "Daily risk limits allow trading.")
        self.assertEqual(result["daily_trades"], 2)
        self.assertEqual(result["daily_losses"], 1)
        self.assertEqual(result["daily_return"], 0.222)

    def test_trade_limit_takes_precedence_over_loss_and_drawdown_limits(self):
        trades = [{"return_percent": -1.0} for _ in range(5)]

        with patch.object(daily_risk_manager, "get_today_trades", return_value=trades):
            result = daily_risk_manager.check_daily_risk_limits()

        self.assertEqual(result["reason"], "Daily trade limit reached.")
        self.assertEqual(result["daily_losses"], 5)
        self.assertEqual(result["daily_return"], -5.0)


if __name__ == "__main__":
    unittest.main()
