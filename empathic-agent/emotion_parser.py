CLINICAL_EMOTIONS = {
    "anxiety",
    "sadness",
    "distress",
    "joy",
    "calmness",
    "enthusiasm",
}


def get_primary_emotion(scores: dict) -> tuple[str, float]:
    """
    From prosody.scores dict, return (emotion_name, confidence_score).
    First tries to find the highest score within CLINICAL_EMOTIONS.
    Falls back to the global max if none of the clinical emotions are present.
    """
    if not scores:
        return "neutral", 0.0

    clinical = {k: v for k, v in scores.items() if k in CLINICAL_EMOTIONS}
    if clinical:
        emotion = max(clinical, key=clinical.get)
        return emotion, float(clinical[emotion])

    emotion = max(scores, key=scores.get)
    return emotion, float(scores[emotion])


def get_clinical_scores(scores: dict) -> dict[str, float]:
    """Returns only the CLINICAL_EMOTIONS subset from the full scores dict."""
    return {k: float(v) for k, v in scores.items() if k in CLINICAL_EMOTIONS}


def format_emotion_for_log(emotion: str, score: float, session_id: str) -> str:
    """Returns a formatted string for logging."""
    return f"[EMOTION] session={session_id} | primary={emotion} | score={score:.2f}"
