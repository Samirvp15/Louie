CLINICAL_EMOTIONS = {
    "anxiety",
    "sadness",
    "distress",
    "joy",
    "calmness",
    "enthusiasm",
}

# Hume uses "Excitement" instead of "enthusiasm"
HUME_EMOTION_ALIASES = {
    "excitement": "enthusiasm",
}


def normalize_scores(scores: dict) -> dict[str, float]:
    """Normalize Hume emotion keys to lowercase snake_case."""
    normalized: dict[str, float] = {}
    for key, value in scores.items():
        norm_key = key.lower().replace(" ", "_")
        norm_key = HUME_EMOTION_ALIASES.get(norm_key, norm_key)
        normalized[norm_key] = float(value)
    return normalized


def extract_prosody_scores(message) -> dict[str, float]:
    """Extract prosody scores from a Hume user_message or assistant_message."""
    if not hasattr(message, "models") or not message.models:
        return {}

    prosody = getattr(message.models, "prosody", None)
    if not prosody or not getattr(prosody, "scores", None):
        return {}

    scores = prosody.scores
    if hasattr(scores, "model_dump"):
        raw = scores.model_dump(by_alias=False)
    elif isinstance(scores, dict):
        raw = scores
    else:
        try:
            raw = dict(scores)
        except (TypeError, ValueError):
            return {}

    return normalize_scores(raw)


def get_primary_emotion(scores: dict) -> tuple[str, float]:
    """
    From prosody.scores dict, return (emotion_name, confidence_score).
    First tries to find the highest score within CLINICAL_EMOTIONS.
    Falls back to the global max if none of the clinical emotions are present.
    """
    if not scores:
        return "neutral", 0.0

    scores = normalize_scores(scores) if any(k[0].isupper() for k in scores) else scores

    clinical = {k: v for k, v in scores.items() if k in CLINICAL_EMOTIONS}
    if clinical:
        emotion = max(clinical, key=clinical.get)
        return emotion, float(clinical[emotion])

    emotion = max(scores, key=scores.get)
    return emotion, float(scores[emotion])


def get_clinical_scores(scores: dict) -> dict[str, float]:
    """Returns only the CLINICAL_EMOTIONS subset from the full scores dict."""
    scores = normalize_scores(scores) if scores and any(k[0].isupper() for k in scores) else scores
    return {k: float(v) for k, v in scores.items() if k in CLINICAL_EMOTIONS}


def format_emotion_for_log(emotion: str, score: float, session_id: str) -> str:
    """Returns a formatted string for logging."""
    return f"[EMOTION] session={session_id} | primary={emotion} | score={score:.2f}"
