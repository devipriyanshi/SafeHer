from backend.models.signal import SafetySignal, SignalType, SignalSeverity


FEATURE_NAMES = [
    "journey_delay",
    "route_deviation",
    "repeated_warnings",
    "manual_checks",
    "user_triggered",
    "journey_expired",
    "high_severity_count",
    "extension_count",
]


def extract_features(signals: list[SafetySignal], extension_count: int) -> dict:
    """
    Convert a list of SafetySignal objects into a named feature dict.
    Each feature is a simple count or binary flag — fully explainable.
    """
    counts = {t: 0 for t in SignalType}
    high_severity = 0

    for sig in signals:
        counts[sig.signal_type] += 1
        if sig.severity == SignalSeverity.HIGH:
            high_severity += 1

    return {
        "journey_delay":      min(counts[SignalType.JOURNEY_DELAY], 1),
        "route_deviation":    min(counts[SignalType.ROUTE_DEVIATION], 1),
        "repeated_warnings":  counts[SignalType.REPEATED_WARNING],
        "manual_checks":      counts[SignalType.MANUAL_CHECK],
        "user_triggered":     min(counts[SignalType.USER_TRIGGERED], 1),
        "journey_expired":    min(counts[SignalType.JOURNEY_EXPIRED], 1),
        "high_severity_count": high_severity,
        "extension_count":    extension_count,
    }


def features_to_vector(feature_dict: dict) -> list[float]:
    return [float(feature_dict[f]) for f in FEATURE_NAMES]


def build_explanation(feature_dict: dict, indication: str) -> tuple[str, str]:
    """
    Returns (explanation_text, suggested_action) based on active features.
    """
    active = []

    if feature_dict["journey_expired"]:
        active.append("Journey arrival time has passed without confirmation")
    if feature_dict["journey_delay"]:
        active.append("Journey is taking longer than the expected duration")
    if feature_dict["route_deviation"]:
        active.append("An unexpected route deviation was detected")
    if feature_dict["repeated_warnings"] >= 2:
        active.append(f"Multiple repeated warnings observed ({feature_dict['repeated_warnings']})")
    if feature_dict["high_severity_count"] >= 2:
        active.append(f"Multiple high-severity signals present ({feature_dict['high_severity_count']})")
    if feature_dict["extension_count"] >= 2:
        active.append(f"Journey has been extended {feature_dict['extension_count']} times")

    if not active:
        explanation = "No unusual signals detected during this journey."
    else:
        explanation = "The following signals contributed to this indication:\n• " + "\n• ".join(active)

    actions = {
        "normal": "No action needed. Your journey appears to be progressing normally.",
        "attention_recommended": "Please confirm your current safety status using the 'Mark Safe' option.",
        "potentially_unusual": "Consider confirming your safety or contacting a trusted person. Use SOS if needed.",
    }
    return explanation, actions.get(indication, "Please check your safety status.")
