import asyncio
import base64
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import WebSocket, WebSocketDisconnect
from mem0 import AsyncMemory

import emotion_parser
import metrics_logger
from hume_client import HumeEVIClient
from mem0_client import get_relevant_memories, save_memory
from session_manager import SessionState

load_dotenv()
logger = logging.getLogger(__name__)

HUME_API_KEY = os.getenv("HUME_API_KEY", "")
HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID", "")

BASE_SYSTEM_PROMPT = (
    "You are Louie, an empathic, warm, and attentive conversational agent. "
    "Listen carefully to the user's emotional tone and respond with genuine care. "
    "Keep responses concise and natural for spoken conversation. "
    "Acknowledge feelings when appropriate without being overly clinical."
)


def format_memories_as_context(memories: list[dict]) -> str:
    """Joins memory texts into a readable context string."""
    if not memories:
        return ""

    lines = []
    for item in memories:
        text = item.get("memory") or item.get("text") or item.get("content", "")
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


def build_system_prompt(context: str) -> str:
    """
    Base personality: empathic, warm, attentive conversational agent.
    If context is not empty, prepend user history from Mem0.
    """
    if not context.strip():
        return BASE_SYSTEM_PROMPT

    return (
        f"{BASE_SYSTEM_PROMPT}\n\n"
        f"Here is what you know about this user from previous conversations:\n{context}"
    )


async def run_session(
    websocket: WebSocket,
    user_id: str,
    memory_client: AsyncMemory,
) -> None:
    """Core orchestrator: coordinates Hume EVI, Mem0, metrics, and client WebSocket."""
    session = SessionState(user_id=user_id)
    metrics_logger.init_log(session.session_id, user_id)
    await websocket.accept()

    turn_state: dict = {
        "turn_id": 0,
        "ts_in": None,
        "last_transcript": "",
        "pending_log": False,
    }
    session_closed = False

    async def send_json(payload: dict) -> None:
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as exc:
            logger.debug("Could not send JSON to client: %s", exc)

    async def finalize_session() -> None:
        nonlocal session_closed
        if session_closed:
            return
        session_closed = True
        session.close()
        if session.messages:
            await save_memory(
                memory_client,
                user_id,
                session.messages,
                session.primary_emotion,
                session.emotion_score,
            )
        metrics_logger.log_session_summary(
            session.session_id,
            user_id,
            session.turn_count,
            session.primary_emotion,
        )
        await send_json({
            "type": "session_summary",
            "session_id": session.session_id,
            "turn_count": session.turn_count,
            "dominant_emotion": session.primary_emotion,
            "emotion_score": round(session.emotion_score, 4),
        })

    try:
        memory_task = get_relevant_memories(
            memory_client,
            user_id,
            query="user preferences and emotional history",
        )
        memories = await asyncio.gather(memory_task, asyncio.sleep(0))
        memories = memories[0]
    except Exception as exc:
        logger.warning("Memory retrieval failed: %s — continuing with empty context", exc)
        memories = []

    context = format_memories_as_context(memories)
    system_prompt = build_system_prompt(context)

    async def on_message(message) -> None:
        msg_type = getattr(message, "type", None)

        if msg_type == "chat_metadata":
            chat_id = getattr(message, "chat_id", "unknown")
            logger.info("Hume chat started: %s", chat_id)

        elif msg_type == "user_message":
            content = ""
            if hasattr(message, "message") and message.message:
                content = getattr(message.message, "content", "") or ""
            if content:
                session.add_message("user", content)
                turn_state["last_transcript"] = content
                turn_state["ts_in"] = datetime.now(timezone.utc)
                turn_state["pending_log"] = True
                session.turn_count += 1
                turn_state["turn_id"] = session.turn_count
                await send_json({"type": "transcript", "role": "user", "content": content})

        elif msg_type == "assistant_message":
            content = ""
            if hasattr(message, "message") and message.message:
                content = getattr(message.message, "content", "") or ""
            if content:
                session.add_message("assistant", content)
                await send_json({"type": "transcript", "role": "assistant", "content": content})

            scores: dict = {}
            if hasattr(message, "models") and message.models and message.models.prosody:
                raw_scores = message.models.prosody.scores
                if raw_scores:
                    scores = dict(raw_scores)

            if scores:
                emotion, score = emotion_parser.get_primary_emotion(scores)
                session.update_emotion(emotion, score)
                clinical = emotion_parser.get_clinical_scores(scores)
                logger.info(
                    emotion_parser.format_emotion_for_log(
                        emotion, score, session.session_id
                    )
                )
                await send_json({
                    "type": "emotion_update",
                    "emotion": emotion,
                    "score": round(score, 4),
                    "clinical_scores": clinical,
                    "turn_id": turn_state["turn_id"],
                })

        elif msg_type == "audio_output":
            ts_out = datetime.now(timezone.utc)
            raw_data = getattr(message, "data", "") or ""
            if raw_data:
                audio_bytes = base64.b64decode(raw_data.encode("utf-8"))
                await websocket.send_bytes(audio_bytes)

            if turn_state["pending_log"] and turn_state["ts_in"]:
                ts_in = turn_state["ts_in"]
                metrics_logger.log_turn(
                    session_id=session.session_id,
                    user_id=user_id,
                    turn_id=turn_state["turn_id"],
                    ts_in=ts_in,
                    ts_out=ts_out,
                    emotion=session.primary_emotion,
                    score=session.emotion_score,
                    transcript=turn_state["last_transcript"],
                )
                turn_state["pending_log"] = False

        elif msg_type == "error":
            code = getattr(message, "code", "unknown")
            err_msg = getattr(message, "message", "Unknown error")
            logger.error("Hume EVI error (%s): %s", code, err_msg)

    async def on_close() -> None:
        await finalize_session()

    hume = HumeEVIClient(HUME_API_KEY, HUME_CONFIG_ID, system_prompt)

    try:
        async with hume.connect(on_message_callback=on_message, on_close_callback=on_close):
            await send_json({"type": "status", "status": "active", "session_id": session.session_id})
            async for data in websocket.iter_bytes():
                if not turn_state["ts_in"]:
                    turn_state["ts_in"] = datetime.now(timezone.utc)
                await hume.send_audio(data)
    except WebSocketDisconnect:
        logger.info("Client disconnected: user=%s session=%s", user_id, session.session_id)
        await finalize_session()
    except Exception as exc:
        logger.exception("Session error for user %s: %s", user_id, exc)
        await finalize_session()
        raise
    finally:
        await finalize_session()
