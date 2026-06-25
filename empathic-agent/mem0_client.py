import asyncio
import logging
import os
from typing import Any

from mem0 import AsyncMemory

logger = logging.getLogger(__name__)

MEM0_TIMEOUT_SECONDS = 4.0

MEM0_CONFIG = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "user_memories",
            "embedding_model_dims": 1536,
            "on_disk": True,
            "path": "./logs/qdrant_data",
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",
            "temperature": 0.1,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
        },
    },
}


async def init_memory_client() -> AsyncMemory:
    """Initializes and returns the Mem0 AsyncMemory client."""
    return AsyncMemory.from_config(MEM0_CONFIG)


async def _run_with_timeout(coro, operation: str) -> Any:
    try:
        return await asyncio.wait_for(coro, timeout=MEM0_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        logger.warning("Mem0 %s timed out after %.1fs — degraded mode", operation, MEM0_TIMEOUT_SECONDS)
        return None
    except Exception as exc:
        logger.warning("Mem0 %s failed: %s — degraded mode", operation, exc)
        return None


async def save_memory(
    client: AsyncMemory,
    user_id: str,
    messages: list[dict],
    emotion: str,
    emotion_score: float,
) -> None:
    """Persists session messages and emotional context via Mem0."""
    if not messages:
        return

    metadata = {
        "emotion": emotion,
        "emotion_score": emotion_score,
    }

    result = await _run_with_timeout(
        client.add(messages=messages, user_id=user_id, metadata=metadata),
        "save_memory",
    )
    if result is not None:
        logger.info("Saved memories for user %s", user_id)


async def get_relevant_memories(
    client: AsyncMemory,
    user_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Retrieves relevant memories for the user query."""
    result = await _run_with_timeout(
        client.search(
            query=query,
            filters={"user_id": user_id},
            top_k=top_k,
        ),
        "get_relevant_memories",
    )
    if result is None:
        return []

    if isinstance(result, dict):
        return result.get("results", [])
    return result if isinstance(result, list) else []


async def get_all_memories(client: AsyncMemory, user_id: str) -> list[dict]:
    """Returns all memories stored for a user."""
    result = await _run_with_timeout(
        client.get_all(filters={"user_id": user_id}),
        "get_all_memories",
    )
    if result is None:
        return []

    if isinstance(result, dict):
        return result.get("results", result.get("memories", []))
    return result if isinstance(result, list) else []


async def delete_all_memories(client: AsyncMemory, user_id: str) -> None:
    """Deletes all memories for a user (test reset between participants)."""
    result = await _run_with_timeout(
        client.delete_all(user_id=user_id),
        "delete_all_memories",
    )
    if result is not None:
        logger.info("Deleted all memories for user %s", user_id)
