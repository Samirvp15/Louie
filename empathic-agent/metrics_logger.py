import csv
import os
from datetime import datetime, timezone

LOGS_DIR = "./logs"
os.makedirs(LOGS_DIR, exist_ok=True)


def get_log_path(session_id: str) -> str:
    return f"{LOGS_DIR}/session_{session_id}.csv"


def init_log(session_id: str, user_id: str) -> None:
    """Creates the CSV file with headers for a new session."""
    with open(get_log_path(session_id), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "turn_id",
            "user_id",
            "session_id",
            "timestamp_audio_in",
            "timestamp_audio_out",
            "latency_ms",
            "emotion_primary",
            "emotion_score",
            "transcript_snippet",
        ])


def log_turn(
    session_id: str,
    user_id: str,
    turn_id: int,
    ts_in: datetime,
    ts_out: datetime,
    emotion: str,
    score: float,
    transcript: str = "",
) -> None:
    """Appends one turn row to the session CSV."""
    latency_ms = int((ts_out - ts_in).total_seconds() * 1000)
    with open(get_log_path(session_id), "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            turn_id,
            user_id,
            session_id,
            ts_in.isoformat(),
            ts_out.isoformat(),
            latency_ms,
            emotion,
            round(score, 4),
            transcript[:80],
        ])


def log_session_summary(
    session_id: str,
    user_id: str,
    total_turns: int,
    dominant_emotion: str,
) -> None:
    """Writes a summary row at session end."""
    summary_path = f"{LOGS_DIR}/summary_all_sessions.csv"
    write_header = not os.path.exists(summary_path)
    with open(summary_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "session_id",
                "user_id",
                "total_turns",
                "dominant_emotion",
                "ended_at",
            ])
        writer.writerow([
            session_id,
            user_id,
            total_turns,
            dominant_emotion,
            datetime.now(timezone.utc).isoformat(),
        ])
