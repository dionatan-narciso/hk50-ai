def safe_float(value, default=0):
    try:
        if value is None:
            return default
        return float(str(value).replace(",", ""))
    except Exception:
        return default


def detect_swing_levels(candles, lookback=3):
    supports = []
    resistances = []

    if len(candles) < lookback * 2 + 1:
        return supports, resistances

    for i in range(lookback, len(candles) - lookback):
        current = candles[i]

        current_high = safe_float(current.get("high") or current.get("High"))
        current_low = safe_float(current.get("low") or current.get("Low"))

        left = candles[i - lookback:i]
        right = candles[i + 1:i + lookback + 1]

        left_highs = [safe_float(c.get("high") or c.get("High")) for c in left]
        right_highs = [safe_float(c.get("high") or c.get("High")) for c in right]

        left_lows = [safe_float(c.get("low") or c.get("Low")) for c in left]
        right_lows = [safe_float(c.get("low") or c.get("Low")) for c in right]

        if current_high > max(left_highs) and current_high > max(right_highs):
            resistances.append(current_high)

        if current_low < min(left_lows) and current_low < min(right_lows):
            supports.append(current_low)

    return supports, resistances


def merge_nearby_levels(levels, tolerance_percent=0.35):
    if not levels:
        return []

    levels = sorted(levels)
    merged = []
    current_group = [levels[0]]

    for level in levels[1:]:
        group_average = sum(current_group) / len(current_group)
        distance_percent = abs((level - group_average) / group_average) * 100

        if distance_percent <= tolerance_percent:
            current_group.append(level)
        else:
            merged.append({
                "level": round(sum(current_group) / len(current_group), 2),
                "strength": len(current_group)
            })
            current_group = [level]

    merged.append({
        "level": round(sum(current_group) / len(current_group), 2),
        "strength": len(current_group)
    })

    return merged


def classify_sr_position(distance_to_support, distance_to_resistance):
    near_support = (
        distance_to_support is not None
        and distance_to_support <= 0.75
    )

    near_resistance = (
        distance_to_resistance is not None
        and distance_to_resistance <= 0.75
    )

    if near_support and near_resistance:
        return "COMPRESSED_BETWEEN_LEVELS"

    if near_support:
        return "NEAR_SUPPORT"

    if near_resistance:
        return "NEAR_RESISTANCE"

    return "OPEN_SPACE"


def analyse_break_context(
    current_price,
    merged_supports,
    merged_resistances
):
    supports_above_price = [
        level for level in merged_supports
        if level["level"] > current_price
    ]

    resistances_below_price = [
        level for level in merged_resistances
        if level["level"] < current_price
    ]

    last_broken_support = None
    last_broken_resistance = None

    if supports_above_price:
        last_broken_support = min(
            supports_above_price,
            key=lambda x: x["level"]
        )

    if resistances_below_price:
        last_broken_resistance = max(
            resistances_below_price,
            key=lambda x: x["level"]
        )

    distance_below_broken_support = None
    distance_above_broken_resistance = None

    if last_broken_support:
        distance_below_broken_support = round(
            ((last_broken_support["level"] - current_price) / current_price) * 100,
            3
        )

    if last_broken_resistance:
        distance_above_broken_resistance = round(
            ((current_price - last_broken_resistance["level"]) / current_price) * 100,
            3
        )

    return {
        "last_broken_support": (
            last_broken_support["level"] if last_broken_support else None
        ),
        "last_broken_support_strength": (
            last_broken_support["strength"] if last_broken_support else 0
        ),
        "distance_below_broken_support": distance_below_broken_support,
        "price_below_recent_support": last_broken_support is not None,

        "last_broken_resistance": (
            last_broken_resistance["level"] if last_broken_resistance else None
        ),
        "last_broken_resistance_strength": (
            last_broken_resistance["strength"] if last_broken_resistance else 0
        ),
        "distance_above_broken_resistance": distance_above_broken_resistance,
        "price_above_recent_resistance": last_broken_resistance is not None,
    }


def classify_break_status(
    support_resistance_status,
    break_context
):
    if break_context.get("price_below_recent_support"):
        return "BELOW_RECENT_SUPPORT"

    if break_context.get("price_above_recent_resistance"):
        return "ABOVE_RECENT_RESISTANCE"

    return support_resistance_status


def analyse_support_resistance(candles, current_price):
    current_price = safe_float(current_price)

    supports, resistances = detect_swing_levels(candles)

    merged_supports = merge_nearby_levels(supports)
    merged_resistances = merge_nearby_levels(resistances)

    valid_supports = [
        level for level in merged_supports
        if level["level"] < current_price
    ]

    valid_resistances = [
        level for level in merged_resistances
        if level["level"] > current_price
    ]

    nearest_support = None
    nearest_resistance = None

    if valid_supports:
        nearest_support = max(valid_supports, key=lambda x: x["level"])

    if valid_resistances:
        nearest_resistance = min(valid_resistances, key=lambda x: x["level"])

    distance_to_support = None
    distance_to_resistance = None

    if nearest_support:
        distance_to_support = round(
            ((current_price - nearest_support["level"]) / current_price) * 100,
            3
        )

    if nearest_resistance:
        distance_to_resistance = round(
            ((nearest_resistance["level"] - current_price) / current_price) * 100,
            3
        )

    support_resistance_status = classify_sr_position(
        distance_to_support,
        distance_to_resistance
    )

    break_context = analyse_break_context(
        current_price=current_price,
        merged_supports=merged_supports,
        merged_resistances=merged_resistances
    )

    final_status = classify_break_status(
        support_resistance_status=support_resistance_status,
        break_context=break_context
    )

    return {
        "nearest_support": nearest_support["level"] if nearest_support else None,
        "support_strength": nearest_support["strength"] if nearest_support else 0,
        "nearest_resistance": nearest_resistance["level"] if nearest_resistance else None,
        "resistance_strength": nearest_resistance["strength"] if nearest_resistance else 0,
        "distance_to_support": distance_to_support,
        "distance_to_resistance": distance_to_resistance,
        "support_resistance_status": final_status,
        "raw_support_resistance_status": support_resistance_status,
        **break_context,
    }