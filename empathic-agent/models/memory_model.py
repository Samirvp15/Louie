from dataclasses import dataclass


@dataclass
class MemoryRecord:
    memory_id: str
    text: str
    user_id: str
    emotion: str
    emotion_score: float
    session_id: str
    created_at: str
