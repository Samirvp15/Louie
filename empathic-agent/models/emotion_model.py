from dataclasses import dataclass
from datetime import datetime


@dataclass
class EmotionPayload:
    emotion: str
    score: float
    timestamp: datetime
    session_id: str
    turn_id: int
    clinical_scores: dict
