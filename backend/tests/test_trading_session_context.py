import unittest
from datetime import datetime, timedelta, timezone

from app.market_context import derive_trading_session_context
from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    MarketContext,
    Rsi30Strategy,
    RsiPullbackStrategy,
    TrendFollowingStrategy,
)


class TradingSessionContextTests(unittest.TestCase):
    def test_asia_session(self):
        result = derive_trading_session_context(
            datetime(2026, 8, 23, 2, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(result.active_sessions, ("ASIA",))
        self.assertEqual(result.label, "ASIA")
        self.assertFalse(result.is_overlap)
        self.assertFalse(result.is_quiet)

    def test_asia_europe_overlap(self):
        result = derive_trading_session_context(
            datetime(2026, 8, 23, 8, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(result.active_sessions, ("ASIA", "EUROPE"))
        self.assertEqual(result.label, "ASIA+EUROPE")
        self.assertTrue(result.is_overlap)

    def test_europe_us_overlap(self):
        result = derive_trading_session_context(
            datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(result.active_sessions, ("EUROPE", "US"))
        self.assertEqual(result.label, "EUROPE+US")
        self.assertTrue(result.is_overlap)

    def test_us_session(self):
        result = derive_trading_session_context(
            datetime(2026, 8, 23, 18, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(result.active_sessions, ("US",))
        self.assertEqual(result.label, "US")

    def test_quiet_period(self):
        result = derive_trading_session_context(
            datetime(2026, 8, 23, 23, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(result.active_sessions, ())
        self.assertEqual(result.label, "QUIET")
        self.assertTrue(result.is_quiet)
        self.assertFalse(result.is_overlap)

    def test_timezone_conversion_is_deterministic(self):
        nz_offset = timezone(timedelta(hours=12))
        local = datetime(2026, 8, 23, 20, 0, tzinfo=nz_offset)
        result = derive_trading_session_context(local)
        self.assertEqual(
            result.timestamp_utc,
            datetime(2026, 8, 23, 8, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(result.label, "ASIA+EUROPE")

    def test_naive_datetime_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            derive_trading_session_context(datetime(2026, 8, 23, 8, 0))

    def test_session_context_does_not_change_strategy_decisions(self):
        data = {
            "rsi": 40,
            "trend": "Bullish",
            "risk": "Low",
            "price": 110,
            "ma20": 105,
            "ma50": 100,
            "confidence": 80,
        }
        session = derive_trading_session_context(
            datetime(2026, 8, 23, 14, 0, tzinfo=timezone.utc)
        )
        plain = MarketContext(symbol="HK50", timeframe="1h", data=data)
        enriched = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data=data,
            session={
                "label": session.label,
                "active_sessions": session.active_sessions,
                "is_overlap": session.is_overlap,
                "is_quiet": session.is_quiet,
            },
        )

        strategies = (
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
            Rsi30Strategy(),
        )
        for strategy in strategies:
            with self.subTest(strategy=strategy.name):
                self.assertEqual(
                    strategy.evaluate(plain),
                    strategy.evaluate(enriched),
                )


if __name__ == "__main__":
    unittest.main()
