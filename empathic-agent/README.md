# Louie — Empathic Conversational Agent (MVP)

Research prototype for a university thesis: a multimodal empathic conversational agent powered by **Hume EVI** (voice + emotional prosody) and **Mem0** (persistent personalized memory via Qdrant).

## Features

- Real-time voice conversation with emotional prosody analysis (Hume EVI)
- Persistent cross-session memory (Mem0 + Qdrant vector store)
- FastAPI backend with WebSocket audio streaming
- Automatic latency and emotion logging to CSV (Sprint 4 evaluation)
- Minimal browser UI for 10-minute user testing sessions

## Prerequisites

- Python 3.10+
- Hume API key and EVI config ID ([Hume Platform](https://app.hume.ai/))
- OpenAI API key (used by Mem0 for LLM + embeddings)
- Microphone-enabled browser (Chrome/Edge recommended)

> **Note:** Hume EVI Python SDK officially supports macOS/Linux. On Windows, the backend may still work via WSL or direct WebSocket usage; the browser frontend runs on any OS.

## Setup

```bash
cd empathic-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `HUME_API_KEY` | Hume API key |
| `HUME_CONFIG_ID` | EVI configuration ID |
| `OPENAI_API_KEY` | OpenAI key for Mem0 LLM + embeddings |

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000), enter a participant ID, and click **Start Session**.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `WS` | `/ws/{user_id}` | Voice session WebSocket |
| `GET` | `/memories/{user_id}` | List stored memories (debug) |
| `DELETE` | `/memories/{user_id}` | Reset memories between participants |

## Metrics Logging

Per-session turn logs are written to:

```
logs/session_{session_id}.csv
```

Session summaries are appended to:

```
logs/summary_all_sessions.csv
```

Columns per turn: `turn_id`, timestamps, `latency_ms`, `emotion_primary`, `emotion_score`, `transcript_snippet`.

## Project Structure

```
empathic-agent/
├── main.py              # FastAPI entry point
├── orchestrator.py      # Hume EVI + Mem0 coordination
├── hume_client.py       # Hume EVI WebSocket client
├── mem0_client.py       # Mem0 AsyncMemory wrapper
├── emotion_parser.py    # Clinical emotion extraction
├── session_manager.py   # Session state
├── metrics_logger.py    # CSV metrics for evaluation
├── models/              # Data models
├── static/index.html    # Browser UI
└── logs/                # Session metric CSVs
```

## Evaluation Workflow

1. Assign each participant a unique `user_id` (e.g. `P01`, `P02`).
2. Run a 10-minute voice session per participant.
3. After each session, optionally `DELETE /memories/{user_id}` to reset memory, or keep memories to test recall across sessions.
4. Collect CSV logs from `./logs/` for latency and emotion analysis.

## License

Research / thesis use.
