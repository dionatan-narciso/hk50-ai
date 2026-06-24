def calculate_position_size(confidence, risk, live_score=0, robustness="UNKNOWN"):
    # AI Quality Control V1
    if confidence < 55:
        quality = "REJECT"
        risk_percent = 0
    elif confidence < 65:
        quality = "WEAK"
        risk_percent = 0.15
    elif confidence < 75:
        quality = "MODERATE"
        risk_percent = 0.35
    elif confidence < 85:
        quality = "STRONG"
        risk_percent = 0.65
    else:
        quality = "EXCEPTIONAL"
        risk_percent = 1.0

    # Market risk adjustment
    if risk == "High":
        risk_percent *= 0.5
    elif risk == "Low":
        risk_percent *= 1.2

    # Robustness adjustment
    if robustness == "UNSTABLE":
        risk_percent *= 0.5
    elif robustness == "FAIL":
        risk_percent = 0
        quality = "REJECT"

    # Live performance adjustment
    if live_score >= 15:
        risk_percent *= 1.2
    elif live_score <= 0:
        risk_percent *= 0.75

    risk_percent = round(max(0, min(risk_percent, 1.5)), 2)

    if risk_percent == 0:
        label = "NO TRADE"
    elif risk_percent <= 0.15:
        label = "VERY SMALL"
    elif risk_percent <= 0.35:
        label = "SMALL"
    elif risk_percent <= 0.75:
        label = "MEDIUM"
    else:
        label = "LARGE"

    return {
        "quality": quality,
        "position_size_label": label,
        "risk_per_trade_percent": risk_percent,
        "suggested_exposure_percent": round(risk_percent * 4, 2),
        "risk_adjusted": risk,
        "robustness_adjusted": robustness,
        "live_score_used": live_score
    }