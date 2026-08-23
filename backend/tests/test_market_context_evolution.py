import unittest

from app.strategies import (
    BreakoutStrategy,
    MaAlignmentStrategy,
    MarketContext,
    Rsi30Strategy,
    RsiPullbackStrategy,
    TrendFollowingStrategy,
)
from app.strategies.voting import run_registry_strategy_vote


class MarketContextEvolutionTests(unittest.TestCase):
    def test_existing_constructor_and_get_contract_are_preserved(self):
        context = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data={"rsi": 42, "risk": "Low"},
        )

        self.assertEqual(context.symbol, "HK50")
        self.assertEqual(context.timeframe, "1h")
        self.assertEqual(context.get("rsi"), 42)
        self.assertEqual(context.get("missing", "fallback"), "fallback")
        self.assertEqual(dict(context.metadata), {})
        self.assertEqual(dict(context.higher_timeframes), {})
        self.assertEqual(dict(context.regime), {})
        self.assertEqual(dict(context.session), {})
        self.assertEqual(dict(context.structure), {})
        self.assertEqual(dict(context.features), {})

    def test_higher_timeframe_data_is_namespaced(self):
        context = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data={"rsi": 42},
            higher_timeframes={
                "4h": {"rsi": 55, "trend": "Bullish"},
                "1d": {"trend": "Bullish"},
            },
        )

        self.assertEqual(context.get("rsi"), 42)
        self.assertEqual(context.get_timeframe("4h")["rsi"], 55)
        self.assertEqual(context.get_timeframe("1d")["trend"], "Bullish")
        self.assertEqual(dict(context.get_timeframe("15m")), {})
        self.assertEqual(
            context.get_timeframe("15m", {"status": "missing"}),
            {"status": "missing"},
        )

    def test_context_enrichment_namespaces_are_independent(self):
        context = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data={"trend": "Bullish"},
            regime={"market": "TRENDING", "volatility": "NORMAL"},
            session={"name": "ASIA", "is_open": True},
            structure={"bias": "BULLISH", "support": 24500},
            features={"trend_strength": 0.72, "distance_from_ma20": 0.4},
        )

        self.assertEqual(context.get("trend"), "Bullish")
        self.assertEqual(context.regime["market"], "TRENDING")
        self.assertEqual(context.session["name"], "ASIA")
        self.assertEqual(context.structure["support"], 24500)
        self.assertEqual(context.get_feature("trend_strength"), 0.72)
        self.assertEqual(context.get_feature("missing", 0), 0)

    def test_existing_strategy_outputs_ignore_enrichment_until_explicitly_used(self):
        strategies = (
            RsiPullbackStrategy(),
            MaAlignmentStrategy(),
            BreakoutStrategy(),
            TrendFollowingStrategy(),
            Rsi30Strategy(),
        )
        data = {
            "rsi": 40,
            "trend": "Bullish",
            "risk": "Low",
            "price": 110,
            "ma20": 105,
            "ma50": 100,
            "confidence": 80,
        }
        plain = MarketContext(symbol="HK50", timeframe="1h", data=data)
        enriched = MarketContext(
            symbol="HK50",
            timeframe="1h",
            data=data,
            higher_timeframes={"4h": {"trend": "Bearish", "rsi": 80}},
            regime={"market": "RANGING"},
            session={"name": "US"},
            structure={"bias": "BEARISH"},
            features={"trend_strength": 0.1},
        )

        for strategy in strategies:
            with self.subTest(strategy=strategy.name):
                plain_decision = strategy.evaluate(plain)
                enriched_decision = strategy.evaluate(enriched)
                self.assertEqual(enriched_decision.signal, plain_decision.signal)
                self.assertEqual(enriched_decision.reason, plain_decision.reason)

    def test_registry_voting_response_is_unchanged_by_market_context_extension(self):
        market_data = {
            "rsi": 40,
            "trend": "Bullish",
            "risk": "Low",
            "price": 110,
            "ma20": 105,
            "ma50": 100,
            "confidence": 80,
        }

        result = run_registry_strategy_vote(market_data)

        self.assertEqual(result["total_votes"], 4)
        self.assertEqual(result["buy_votes"], 4)
        self.assertEqual(result["sell_votes"], 0)
        self.assertEqual(result["hold_votes"], 0)
        self.assertEqual(result["final_vote"], "BUY")
        self.assertEqual(result["vote_strength"], 4)


if __name__ == "__main__":
    unittest.main()
