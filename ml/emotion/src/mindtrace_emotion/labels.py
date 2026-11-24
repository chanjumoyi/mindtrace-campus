"""Versioned label taxonomy and mapping helpers.

The taxonomy is deliberately small.  Fine-grained 27-class annotation is not
supported by the current label budget or by inter-annotator agreement data.
"""

from __future__ import annotations

from typing import Any

TAXONOMY_VERSION = "emotion-taxonomy-v1"
TAXONOMY = ("neutral", "positive", "sadness", "anxiety", "anger", "other")

# CPED has 13 labels.  Keep the mapping explicit so a taxonomy change requires
# a code/config review rather than silently renaming distributions.
CPED_TO_EMOTION = {
    "neutral": "neutral",
    "happy": "positive",
    "grateful": "positive",
    "relaxed": "positive",
    "positive-other": "positive",
    "depress": "sadness",
    "sadness": "sadness",
    "worried": "anxiety",
    "fear": "anxiety",
    "anger": "anger",
    "disgust": "anger",
    "astonished": "other",
    "negative-other": "other",
}

# GoEmotions ships ekman_mapping.json; these are the six Ekman families plus
# neutral, collapsed into the project taxonomy.
EKMAN_TO_EMOTION = {
    "joy": "positive",
    "sadness": "sadness",
    "fear": "anxiety",
    "anger": "anger",
    "disgust": "anger",
    "surprise": "other",
    "neutral": "neutral",
}

ALIASES = {
    "neutral": "neutral",
    "calm": "neutral",
    "positive": "positive",
    "happy": "positive",
    "joy": "positive",
    "grateful": "positive",
    "relaxed": "positive",
    "positive-other": "positive",
    "sad": "sadness",
    "sadness": "sadness",
    "depress": "sadness",
    "depressed": "sadness",
    "anxiety": "anxiety",
    "anxious": "anxiety",
    "worried": "anxiety",
    "worry": "anxiety",
    "fear": "anxiety",
    "nervous": "anxiety",
    "anger": "anger",
    "angry": "anger",
    "annoyed": "anger",
    "disgust": "anger",
    "other": "other",
    "astonished": "other",
    "surprise": "other",
    "negative-other": "other",
    "uncertain": None,
    "": None,
}


def normalize_emotion(value: Any) -> str | None:
    """Return a taxonomy label or None for missing/uncertain/unknown values."""
    if value is None:
        return None
    key = str(value).strip().lower().replace("_", "-").replace(" ", "-")
    if key in ALIASES:
        return ALIASES[key]
    return None


def weak_emotion_from_mood_stress(mood: Any, stress: Any) -> str | None:
    """Derive a noisy quadrant label; never treat this as a gold label.

    mood and stress are expected on a 1-5 scale.  The mapping is intentionally
    coarse and must be validated against manual labels before use.
    """
    try:
        mood_value = float(mood)
        stress_value = float(stress)
    except (TypeError, ValueError):
        return None
    if not (1.0 <= mood_value <= 5.0 and 1.0 <= stress_value <= 5.0):
        return None
    high_mood = mood_value >= 4
    low_mood = mood_value <= 2
    high_stress = stress_value >= 4
    low_stress = stress_value <= 2
    if high_mood and low_stress:
        return "positive"
    if low_mood and high_stress:
        return "anxiety"
    if low_mood and low_stress:
        return "sadness"
    if high_mood and high_stress:
        return "other"
    return "neutral"


def class_weights(labels: list[str | None]) -> dict[str, float]:
    """Inverse-frequency weights with missing labels ignored."""
    counts = {name: 0 for name in TAXONOMY}
    for label in labels:
        normalized = normalize_emotion(label)
        if normalized is not None:
            counts[normalized] += 1
    present = {name: count for name, count in counts.items() if count > 0}
    if not present:
        return {}
    total = sum(present.values())
    return {name: total / (len(present) * count) for name, count in present.items()}
