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

PLACEHOLDER_KEYS = {
    "your_hume_api_key_here",
    "your_hume_config_id_here",
    "your_openai_api_key_here",
    "",
}


def get_hume_credentials() -> tuple[str, str]:
    """Load Hume credentials fresh from .env on each session."""
    load_dotenv(override=True)
    api_key = os.getenv("HUME_API_KEY", "").strip()
    config_id = os.getenv("HUME_CONFIG_ID", "").strip()
    return api_key, config_id


def validate_hume_credentials(api_key: str, config_id: str) -> str | None:
    """Return an error message if credentials are missing or still placeholders."""
    if not api_key or api_key in PLACEHOLDER_KEYS:
        return "HUME_API_KEY no configurada. Edita .env y reinicia el servidor."
    if not config_id or config_id in PLACEHOLDER_KEYS:
        return "HUME_CONFIG_ID no configurado. Edita .env y reinicia el servidor."
    return None

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

        async def emit_emotion(scores: dict) -> None:
            if not scores:
                return
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

        if msg_type == "chat_metadata":
            chat_id = getattr(message, "chat_id", "unknown")
            logger.info("Hume chat started: %s", chat_id)

        elif msg_type == "user_message":
            if getattr(message, "interim", False):
                return

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

            scores = emotion_parser.extract_prosody_scores(message)
            await emit_emotion(scores)

        elif msg_type == "assistant_message":
            content = ""
            if hasattr(message, "message") and message.message:
                content = getattr(message.message, "content", "") or ""
            if content:
                session.add_message("assistant", content)
                await send_json({"type": "transcript", "role": "assistant", "content": content})

            # Fallback: assistant prosody if user_message had none
            if session.emotion_score == 0.0:
                scores = emotion_parser.extract_prosody_scores(message)
                await emit_emotion(scores)

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

    hume_api_key, hume_config_id = get_hume_credentials()
    cred_error = validate_hume_credentials(hume_api_key, hume_config_id)
    if cred_error:
        logger.error(cred_error)
        await send_json({"type": "error", "message": cred_error})
        await finalize_session()
        return

    hume = HumeEVIClient(hume_api_key, hume_config_id, system_prompt)

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
        error_msg = str(exc)
        if "401" in error_msg or "invalid credentials" in error_msg.lower():
            error_msg = (
                "Credenciales de Hume inválidas (401). Verifica HUME_API_KEY y "
                "HUME_CONFIG_ID en .env, guarda el archivo y reinicia uvicorn."
            )
        logger.exception("Session error for user %s: %s", user_id, exc)
        await send_json({"type": "error", "message": error_msg})
        await finalize_session()
    finally:
        await finalize_session()
