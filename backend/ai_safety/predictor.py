"""
SafeHer AI Predictor
---------------------
Loads the trained model and produces an assistive safety indication.
If the model is unavailable, returns a safe fallback — core features continue.
"""
import pathlib
import numpy as np
import joblib

from backend.ai_safety.features import (
    extract_features, features_to_vector, build_explanation, FEATURE_NAMES
)
from backend.models.signal import SafetySignal

MODEL_PATH = pathlib.Path(__file__).parent / "model_artifact.pkl"

_artifact: dict | None = None


def _load_model() -> dict | None:
    global _artifact
    if _artifact is None and MODEL_PATH.exists():
        _artifact = joblib.load(MODEL_PATH)
    return _artifact


# Score ranges per indication — assistive only, not danger measurement
_SCORE_RANGES = {
    "normal": (0, 30),
    "attention_recommended": (31, 60),
    "potentially_unusual": (61, 100),
}


def _compute_score(feature_dict: dict, indication: str) -> float:
    """
    Deterministic score within the indication's range based on active signal count.
    Clearly labelled as an assistive software signal.
    """
    low, high = _SCORE_RANGES[indication]
    active_count = sum([
        feature_dict["journey_delay"],
        feature_dict["route_deviation"],
        min(feature_dict["repeated_warnings"], 3),
        min(feature_dict["high_severity_count"], 3),
        feature_dict["journey_expired"],
        min(feature_dict["extension_count"], 2),
    ])
    max_possible = 13
    ratio = min(active_count / max_possible, 1.0)
    return round(low + ratio * (high - low), 1)


class SafetyPredictor:
    def predict(
        self,
        signals: list[SafetySignal],
        extension_count: int,
    ) -> dict:
        """
        Returns:
            indication: normal | attention_recommended | potentially_unusual
            assistance_score: 0–100 (assistive signal, not danger measurement)
            explanation: why this indication was produced
            suggested_action: what the user can do
            contributing_features: which features were active
            ai_available: False if model could not be loaded
        """
        feature_dict = extract_features(signals, extension_count)
        vector = np.array([features_to_vector(feature_dict)])

        artifact = _load_model()

        if artifact is None:
            # AI unavailable — safe fallback, core features unaffected
            return {
                "indication": "normal",
                "assistance_score": 0.0,
                "explanation": "Safety analysis temporarily unavailable. Core safety features continue to work normally.",
                "suggested_action": "Use the Mark Safe or SOS button as needed.",
                "contributing_features": {},
                "ai_available": False,
            }

        model = artifact["model"]
        le = artifact["label_encoder"]

        raw_label = le.inverse_transform(model.predict(vector))[0]
        explanation, suggested_action = build_explanation(feature_dict, raw_label)
        score = _compute_score(feature_dict, raw_label)

        active_features = {k: v for k, v in feature_dict.items() if v}

        return {
            "indication": raw_label,
            "assistance_score": score,
            "explanation": explanation,
            "suggested_action": suggested_action,
            "contributing_features": active_features,
            "ai_available": True,
        }


predictor = SafetyPredictor()
