"""BadBoerdi Backend — FastAPI application."""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.database import init_db
from app.routers import chat, config, rag, speech, sessions, safety, widget

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="BadBoerdi API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
app.include_router(speech.router, prefix="/api/speech", tags=["speech"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(safety.router, prefix="/api/safety", tags=["safety"])
app.include_router(widget.router, prefix="/widget", tags=["widget"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini")}


@app.get("/api/debug/mcp-test")
async def mcp_test():
    """Test MCP connection directly."""
    from app.services.mcp_client import call_mcp_tool, parse_wlo_cards, _session_id, _initialized
    try:
        result = await call_mcp_tool("search_wlo_collections", {"query": "Mathematik"})
        cards = parse_wlo_cards(result)
        return {
            "status": "ok",
            "session_id": _session_id,
            "initialized": _initialized,
            "result_length": len(result),
            "result_preview": result[:300],
            "cards_count": len(cards),
            "cards": cards[:2],
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "session_id": _session_id, "initialized": _initialized}
