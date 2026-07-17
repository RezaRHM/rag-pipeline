"""Runtime loader for the frozen deterministic intent classifier."""

from pathlib import Path

import joblib


VALID_INTENTS = {
    "standard", "procedural", "comparison", "troubleshooting"
}
ARTIFACT = Path(__file__).with_name("intent_router.joblib")
_classifier = None


def _get_classifier():
    global _classifier
    if _classifier is None:
        if not ARTIFACT.exists():
            raise FileNotFoundError(
                f"Intent-router artifact not found: {ARTIFACT}"
            )
        _classifier = joblib.load(ARTIFACT)
    return _classifier


def classify_intent(question: str) -> dict:
    """Return the intent and calibrated class probabilities for a query."""
    classifier = _get_classifier()
    probabilities = classifier.predict_proba([question])[0]
    best_index = int(probabilities.argmax())
    intent = str(classifier.classes_[best_index])
    if intent not in VALID_INTENTS:
        raise ValueError(f"Unexpected intent label: {intent}")
    return {
        "intent": intent,
        "confidence": float(probabilities[best_index]),
        "probabilities": {
            str(label): float(value)
            for label, value in zip(classifier.classes_, probabilities)
        },
    }
