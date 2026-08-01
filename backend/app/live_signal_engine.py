from app.research.director import run_research_director
from app.strategy_executor import execute_strategy
from app.strategy_voting_engine import run_strategy_vote
from app.voting_performance_memory import get_vote_strength_win_rate
from app.trade_analytics import run_trade_analytics
from app.quality_performance_memory import get_quality_analytics_bonus
from app.live_performance_memory import get_strategy_performance_bonus
from app.regime_analytics import get_regime_bonus
from app.strategy_rotation_engine import rotate_strategy
from app.confidence_calibration_memory import get_confidence_calibration_bonus


def clean_price(price_value):
    if isinstance(price_value, (int, float)):
        return float(price_value)

    return float(str(price_value).replace(",", ""))


def get_research_context():
    try:
        director = run_research_director()

        return {
            "best_strategy": director.get("best_strategy", "Unknown"),
            "most_robust_strategy": director.get("most_robust_strategy", "Unknown"),
            "director_confidence": director.get("confidence_score", 50),
            "confidence_label": director.get("confidence_label", "Moderate"),
            "director_available": True,
        }

    except Exception as e:
        return {
            "best_strategy": "Unknown",
            "most_robust_strategy": "Unknown",
            "director_confidence": 50,
            "confidence_label": "Moderate",
            "director_available": False,
            "error": str(e),
        }


def get_quality_from_confidence(confidence):
    if confidence < 55:
        return "REJECT"
    elif confidence < 65:
        return "WEAK"
    elif confidence < 75:
        return "MODERATE"
    elif confidence < 85:
        return "STRONG"
    else:
        return "EXCEPTIONAL"


def apply_trade_analytics_confidence(strategy_name, vote_strength, confidence):
    analytics = run_trade_analytics()

    adjusted_confidence = confidence
    analytics_reason = "Trade analytics made no confidence change."

    strategy_performance = analytics.get("strategy_performance", [])
    vote_performance = analytics.get("vote_performance", [])

    for row in strategy_performance:
        if row.get("strategy") == strategy_name:
            avg_return = float(row.get("average_return", 0))
            trades = int(row.get("trades", 0))

            if trades >= 5 and avg_return > 0.5:
                adjusted_confidence = min(adjusted_confidence + 5, 100)
                analytics_reason = (
                    f"Strategy analytics positive. "
                    f"{strategy_name} average return is {avg_return}%."
                )

            elif trades >= 5 and avg_return < 0:
                adjusted_confidence = max(adjusted_confidence - 5, 0)
                analytics_reason = (
                    f"Strategy analytics negative. "
                    f"{strategy_name} average return is {avg_return}%."
                )

    for row in vote_performance:
        if int(row.get("vote_strength", 0)) == int(vote_strength):
            avg_return = float(row.get("result_pct", 0))

            if avg_return > 0.5:
                adjusted_confidence = min(adjusted_confidence + 5, 100)
                analytics_reason += (
                    f" Vote strength {vote_strength} has positive "
                    f"average return of {avg_return}%."
                )

            elif avg_return < 0:
                adjusted_confidence = max(adjusted_confidence - 5, 0)
                analytics_reason += (
                    f" Vote strength {vote_strength} has negative "
                    f"average return of {avg_return}%."
                )

    return adjusted_confidence, analytics_reason


def generate_research_driven_signal(market_data, research_context):
    current_price = clean_price(market_data.get("price", 0))

    market_confidence = market_data.get("confidence", 50)
    director_confidence = research_context.get("director_confidence", 50)
    best_strategy = research_context.get("best_strategy", "Trend Following")

    strategy_vote = run_strategy_vote(market_data)

    initial_strategy_result = execute_strategy(best_strategy, market_data)

    market_regime = initial_strategy_result.get(
        "market_regime",
        {
            "market_regime": "UNKNOWN",
            "volatility_regime": "UNKNOWN",
            "preferred_strategies": [],
            "blocked_strategies": [],
            "confidence_adjustment": 0,
        }
    )

    rotation_result = rotate_strategy(
        current_strategy=best_strategy,
        market_regime=market_regime.get("market_regime", "UNKNOWN"),
        volatility_regime=market_regime.get("volatility_regime", "UNKNOWN"),
        research_context=research_context,
    )

    rotated_strategy = rotation_result.get("selected_strategy", best_strategy)

    strategy_result = execute_strategy(rotated_strategy, market_data)

    market_regime = strategy_result.get(
        "market_regime",
        market_regime
    )

    combined_confidence = round((market_confidence + director_confidence) / 2)

    raw_strategy_signal = strategy_result["signal"]
    final_signal = raw_strategy_signal

    vote_signal = strategy_vote.get("final_vote", "HOLD")
    vote_strength = strategy_vote.get("vote_strength", 0)
    total_votes = strategy_vote.get("total_votes", 0)

    voting_assist_reason = "Voting assist made no change."

    if combined_confidence < 55:
        final_signal = "HOLD"
        voting_assist_reason = "Combined confidence below 55. Forced HOLD."

    else:
        if vote_signal == raw_strategy_signal:
            voting_assist_reason = f"Voting confirmed {raw_strategy_signal} signal."

            if raw_strategy_signal != "HOLD":
                historical_win_rate = get_vote_strength_win_rate(vote_strength)

                if historical_win_rate is None:
                    combined_confidence = min(combined_confidence + 5, 100)
                    voting_assist_reason += (
                        " No voting history yet. Default confidence increased by 5."
                    )

                elif historical_win_rate >= 60:
                    combined_confidence = min(combined_confidence + 10, 100)
                    voting_assist_reason += (
                        f" Historical vote win rate is {historical_win_rate}%. "
                        "Confidence increased by 10."
                    )

                elif historical_win_rate >= 55:
                    combined_confidence = min(combined_confidence + 5, 100)
                    voting_assist_reason += (
                        f" Historical vote win rate is {historical_win_rate}%. "
                        "Confidence increased by 5."
                    )

                elif historical_win_rate < 45:
                    combined_confidence = max(combined_confidence - 5, 0)
                    voting_assist_reason += (
                        f" Historical vote win rate is {historical_win_rate}%. "
                        "Confidence reduced by 5."
                    )

                else:
                    voting_assist_reason += (
                        f" Historical vote win rate is {historical_win_rate}%. "
                        "Confidence unchanged."
                    )

        elif (
            raw_strategy_signal in ["BUY", "SELL"]
            and vote_signal in ["BUY", "SELL"]
            and vote_signal != raw_strategy_signal
            and vote_strength >= 3
        ):
            final_signal = "HOLD"
            voting_assist_reason = (
                "Voting strongly disagrees with strategy signal. Forced HOLD."
            )

        elif vote_strength < 3:
            final_signal = raw_strategy_signal
            voting_assist_reason = (
                "Voting strength is weak. Original strategy signal kept."
            )

    strategy_name_for_analytics = (
        strategy_result["strategy_used"].get("strategy")
        if isinstance(strategy_result["strategy_used"], dict)
        else strategy_result["strategy_used"]
    )

    combined_confidence, analytics_reason = apply_trade_analytics_confidence(
        strategy_name=strategy_name_for_analytics,
        vote_strength=vote_strength,
        confidence=combined_confidence
    )

    strategy_bonus_result = get_strategy_performance_bonus(
        strategy_name_for_analytics
    )

    strategy_performance_bonus = strategy_bonus_result.get(
        "strategy_performance_bonus",
        0
    )

    combined_confidence = max(
        0,
        min(100, combined_confidence + strategy_performance_bonus)
    )

    regime_bonus_result = get_regime_bonus(
        strategy=strategy_name_for_analytics,
        market_regime=market_regime.get("market_regime", "UNKNOWN"),
        volatility_regime=market_regime.get("volatility_regime", "UNKNOWN"),
    )

    regime_bonus = regime_bonus_result.get("regime_bonus", 0)

    combined_confidence = max(
        0,
        min(100, combined_confidence + regime_bonus)
    )

    confidence_calibration_result = get_confidence_calibration_bonus(
    combined_confidence
)

    confidence_calibration_bonus = confidence_calibration_result.get(
    "confidence_calibration_bonus",
    0
)

    combined_confidence = max(
    0,
    min(100, combined_confidence + confidence_calibration_bonus)
)

    quality = get_quality_from_confidence(combined_confidence)
    quality_analytics = get_quality_analytics_bonus(quality)
    quality_analytics_bonus = quality_analytics.get("analytics_bonus", 0)

    combined_confidence = max(
        0,
        min(100, combined_confidence + quality_analytics_bonus)
    )

    final_quality = get_quality_from_confidence(combined_confidence)

    reason = (
        f'{strategy_result["strategy_reason"]} '
        f'Research strategy used: {strategy_result["strategy_used"]}. '
        f'Original strategy: {rotation_result.get("original_strategy")}. '
        f'Rotated strategy: {rotation_result.get("selected_strategy")}. '
        f'Rotation reason: {rotation_result.get("rotation_reason")} '
        f'Market regime: {market_regime.get("market_regime")}. '
        f'Volatility regime: {market_regime.get("volatility_regime")}. '
        f'Combined confidence: {combined_confidence}. '
        f'Voting assist: {voting_assist_reason} '
        f'Trade analytics: {analytics_reason} '
        f'Strategy performance: {strategy_bonus_result.get("reason")} '
        f'Regime analytics: {regime_bonus_result.get("reason")} '
        f'Quality analytics: {quality_analytics.get("reason")} '
        f'Confidence calibration: {confidence_calibration_result.get("reason")} '
    )

    return {
        "symbol": "HK50",
        "current_price": current_price,
        "signal": final_signal,
        "final_signal": final_signal,
        "raw_signal": raw_strategy_signal,
        "raw_strategy_signal": raw_strategy_signal,
        "confidence": combined_confidence,
        "reason": reason,
        "market_confidence": market_confidence,
        "director_confidence": director_confidence,
        "best_strategy": research_context.get("best_strategy"),
        "most_robust_strategy": research_context.get("most_robust_strategy"),
        "confidence_label": research_context.get("confidence_label"),
        "strategy_used": strategy_result["strategy_used"],
        "strategy_name": strategy_name_for_analytics,
        "strategy_reason": strategy_result["strategy_reason"],
        "rotation_selected_strategy": rotation_result.get("selected_strategy"),
        "rotation_original_strategy": rotation_result.get("original_strategy"),
        "rotation_changed_strategy": rotation_result.get(
            "rotation_changed_strategy"
        ),
        "rotation_reason": rotation_result.get("rotation_reason"),
        "rotation_scores": rotation_result.get("rotation_scores", []),
        "market_regime": market_regime.get("market_regime"),
        "volatility_regime": market_regime.get("volatility_regime"),
        "preferred_strategies": market_regime.get("preferred_strategies", []),
        "blocked_strategies": market_regime.get("blocked_strategies", []),
        "regime_confidence_adjustment": market_regime.get(
            "confidence_adjustment",
            0
        ),
        "regime_bonus": regime_bonus,
        "regime_bonus_reason": regime_bonus_result.get("reason"),
        "strategy_vote": strategy_vote,
        "vote_signal": vote_signal,
        "vote_strength": vote_strength,
        "total_votes": total_votes,
        "voting_assist_reason": voting_assist_reason,
        "trade_analytics_reason": analytics_reason,
        "strategy_performance_bonus": strategy_performance_bonus,
        "strategy_performance_reason": strategy_bonus_result.get("reason"),
        "quality": final_quality,
        "quality_before_analytics": quality,
        "quality_analytics_bonus": quality_analytics_bonus,
        "quality_analytics_reason": quality_analytics.get("reason"),
    }

def generate_live_signal(market_data):
    research_context = get_research_context()
    return generate_research_driven_signal(market_data, research_context)


def apply_voting_assist(strategy_signal, confidence, strategy_vote):
    vote_signal = strategy_vote.get("final_vote", "HOLD")
    vote_strength = strategy_vote.get("vote_strength", 0)
    total_votes = strategy_vote.get("total_votes", 0)

    final_signal = strategy_signal
    adjusted_confidence = confidence
    assist_reason = "Voting assist made no change."

    if total_votes == 0:
        return final_signal, adjusted_confidence, assist_reason

    if vote_signal == strategy_signal and strategy_signal != "HOLD":
        adjusted_confidence = min(confidence + 5, 100)
        assist_reason = "Voting agrees with strategy signal. Confidence increased."

    elif (
        strategy_signal in ["BUY", "SELL"]
        and vote_signal in ["BUY", "SELL"]
        and vote_signal != strategy_signal
        and vote_strength >= 3
    ):
        final_signal = "HOLD"
        assist_reason = "Voting strongly disagrees with strategy signal. Forced HOLD."

    elif vote_strength < 3:
        final_signal = strategy_signal
        assist_reason = "Voting strength is weak. Original strategy signal kept."

    return final_signal, adjusted_confidence, assist_reason