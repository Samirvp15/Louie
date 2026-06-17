from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class SessionState:
    user_id: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    messages: list[dict] = field(default_factory=list)
    primary_emotion: str = "neutral"
    emotion_score: float = 0.0
    turn_count: int = 0

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def update_emotion(self, emotion: str, score: float) -> None:
        """Keep the emotion with the highest accumulated score across turns."""
        if score > self.emotion_score:
            self.primary_emotion = emotion
            self.emotion_score = score

    def close(self) -> None:
        self.ended_at = datetime.now(timezone.utc)
