import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles

from mem0_client import delete_all_memories, get_all_memories, init_memory_client
from orchestrator import run_session

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Mem0 AsyncMemory client...")
    app.state.memory = await init_memory_client()
    yield
    logger.info("Shutting down — cleaning up resources.")
    app.state.memory = None


app = FastAPI(
    title="Louie — Empathic Conversational Agent",
    description="MVP: Hume EVI + Mem0 empathic voice agent for thesis evaluation",
    version="0.1.0",
    lifespan=lifespan,
)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await run_session(websocket, user_id, app.state.memory)


@app.get("/memories/{user_id}")
async def list_memories(user_id: str):
    """Returns all stored memories for a user (debugging)."""
    try:
        memories = await get_all_memories(app.state.memory, user_id)
        return {"user_id": user_id, "count": len(memories), "memories": memories}
    except Exception as exc:
        logger.error("Failed to fetch memories: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/memories/{user_id}")
async def reset_memories(user_id: str):
    """Deletes all memories for a user (test reset between participants)."""
    try:
        await delete_all_memories(app.state.memory, user_id)
        return {"user_id": user_id, "status": "deleted"}
    except Exception as exc:
        logger.error("Failed to delete memories: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
