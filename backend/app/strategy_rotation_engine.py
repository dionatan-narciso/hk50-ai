from app.regime_analytics import get_regime_bonus
from app.live_performance_memory import get_strategy_performance_bonus


CANDIDATE_STRATEGIES = [
    "RSI < 30",
    "RSI Pullback",
    "MA Alignment",
    "Breakout",
    "Trend Following",
]


def get_base_research_score(strategy_name, research_context):
    best_strategy = research_context.get("best_strategy", "")
    most_robust_strategy = research_context.get("most_robust_strategy", "")
    director_confidence = research_context.get("director_confidence", 50)

    best_strategy_text = str(best_strategy).lower()
    robust_strategy_text = str(most_robust_strategy).lower()
    strategy_text = str(strategy_name).lower()

    score = 50

    if strategy_text in best_strategy_text:
        score += 20

    if strategy_text in robust_strategy_text:
        score += 10

    score += round((director_confidence - 50) / 2)

    return max(0, min(100, score))


def get_regime_preference_bias(strategy_name, market_regime, volatility_regime):
    bias = 0
    reason = "No regime preference bias applied."

    if market_regime == "TRENDING":
        if strategy_name in ["Breakout", "Trend Following"]:
            bias = 12
            reason = f"{strategy_name} preferred in trending markets."
        elif strategy_name == "MA Alignment":
            bias = 8
            reason = "MA Alignment supported in trending markets."
        elif strategy_name in ["RSI < 30", "RSI Pullback"]:
            bias = -12
            reason = f"{strategy_name} reduced in trending markets."

    elif market_regime == "RANGING":
        if strategy_name in ["RSI < 30", "RSI Pullback"]:
            bias = 10
            reason = f"{strategy_name} preferred in ranging markets."
        elif strategy_name in ["Breakout", "Trend Following"]:
            bias = -8
            reason = f"{strategy_name} reduced in ranging markets."

    elif market_regime == "HIGH_VOLATILITY":
        if strategy_name == "Breakout":
            bias = 8
            reason = "Breakout preferred in high volatility."
        elif strategy_name in ["RSI < 30", "RSI Pullback"]:
            bias = -8
            reason = f"{strategy_name} reduced in high volatility."

    elif market_regime == "LOW_VOLATILITY":
        if strategy_name in ["RSI < 30", "RSI Pullback"]:
            bias = 6
            reason = f"{strategy_name} supported in low volatility."
        elif strategy_name == "Breakout":
            bias = -6
            reason = "Breakout reduced in low volatility."

    if volatility_regime == "HIGH_VOLATILITY" and strategy_name == "Breakout":
        bias += 4
        reason += " Extra volatility breakout bonus applied."

    if volatility_regime == "LOW_VOLATILITY" and strategy_name == "Breakout":
        bias -= 4
        reason += " Extra low volatility breakout penalty applied."

    return {
        "regime_preference_bias": bias,
        "regime_preference_reason": reason,
    }


def score_strategy_for_current_market(
    strategy_name,
    market_regime,
    volatility_regime,
    research_context,
):
    research_score = get_base_research_score(strategy_name, research_context)

    regime_result = get_regime_bonus(
        strategy=strategy_name,
        market_regime=market_regime,
        volatility_regime=volatility_regime,
    )

    regime_bonus = regime_result.get("regime_bonus", 0)

    preference_result = get_regime_preference_bias(
        strategy_name=strategy_name,
        market_regime=market_regime,
        volatility_regime=volatility_regime,
    )

    regime_preference_bias = preference_result.get(
        "regime_preference_bias",
        0
    )

    live_result = get_strategy_performance_bonus(strategy_name)
    live_bonus = live_result.get("strategy_performance_bonus", 0)

    final_score = (
        research_score
        + regime_bonus
        + regime_preference_bias
        + live_bonus
    )

    final_score = max(0, min(100, final_score))

    return {
        "strategy": strategy_name,
        "research_score": research_score,
        "regime_bonus": regime_bonus,
        "regime_reason": regime_result.get("reason"),
        "regime_preference_bias": regime_preference_bias,
        "regime_preference_reason": preference_result.get(
            "regime_preference_reason"
        ),
        "live_bonus": live_bonus,
        "live_reason": live_result.get("reason"),
        "final_rotation_score": final_score,
    }


def rotate_strategy(
    current_strategy,
    market_regime,
    volatility_regime,
    research_context,
):
    rotation_scores = []

    for strategy in CANDIDATE_STRATEGIES:
        score = score_strategy_for_current_market(
            strategy_name=strategy,
            market_regime=market_regime,
            volatility_regime=volatility_regime,
            research_context=research_context,
        )
        rotation_scores.append(score)

    rotation_scores = sorted(
        rotation_scores,
        key=lambda row: row["final_rotation_score"],
        reverse=True
    )

    selected = rotation_scores[0]

    return {
        "selected_strategy": selected.get("strategy"),
        "original_strategy": current_strategy,
        "rotation_changed_strategy": selected.get("strategy") != current_strategy,
        "rotation_scores": rotation_scores,
        "rotation_reason": (
            f"Selected {selected.get('strategy')} with rotation score "
            f"{selected.get('final_rotation_score')}. "
            f"Preference: {selected.get('regime_preference_reason')}"
        ),
    }