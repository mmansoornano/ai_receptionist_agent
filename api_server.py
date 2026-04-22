"""Agent API server using FastAPI."""
from __future__ import annotations

import asyncio
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import (
    BACKEND_API_BASE_URL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
)
from main import process_message


def _cors_allow_origins() -> tuple[list[str], bool]:
    """Explicit origins from CORS_ORIGINS (comma-separated), or wildcard without credentials."""
    raw = (os.getenv("CORS_ORIGINS") or "").strip()
    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        return origins, True
    return ["*"], False


_origins, _credentials = _cors_allow_origins()

app = FastAPI(title="AI Receptionist Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageRequest(BaseModel):
    message: str = Field(..., max_length=16_000)
    phone_number: str = Field(..., max_length=64)
    channel: str = "sms"
    language: str = "en"
    conversation_id: Optional[str] = Field(None, max_length=128)
    customer_id: Optional[str] = Field(None, max_length=128)


class MessageResponse(BaseModel):
    success: bool
    response: str
    error: Optional[str] = None


@app.post("/process", response_model=MessageResponse)
async def process_message_endpoint(request: MessageRequest):
    """Process a message through the agent."""
    try:
        response = process_message(
            message=request.message,
            phone_number=request.phone_number,
            channel=request.channel,
            language=request.language,
            conversation_id=request.conversation_id,
            customer_id=request.customer_id,
        )
        return MessageResponse(success=True, response=response)
    except Exception as e:
        body = MessageResponse(success=False, response="", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body.model_dump(),
        )


def _check_ollama_sync() -> str:
    base = (OLLAMA_BASE_URL or "http://127.0.0.1:11434").rstrip("/")
    try:
        urllib.request.urlopen(f"{base}/api/tags", timeout=2)
        return "reachable"
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return "unreachable"


def _check_openai_configured_sync() -> str:
    return "configured" if (OPENAI_API_KEY or "").strip() else "missing_api_key"


def _check_backend_sync() -> str:
    base = (BACKEND_API_BASE_URL or "").rstrip("/")
    if not base:
        return "not_configured"
    try:
        urllib.request.urlopen(f"{base}/", timeout=2)
        return "reachable"
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return "unreachable"


@app.get("/health")
async def health_check():
    """Shallow liveness: process is up."""
    return {"status": "healthy"}


@app.get("/health/ready")
async def health_ready():
    """Dependency checks with short timeouts. Always HTTP 200; use ``status`` / ``llm_ok`` for automation."""
    backend = await asyncio.to_thread(_check_backend_sync)
    if LLM_PROVIDER == "openai":
        llm_detail = await asyncio.to_thread(_check_openai_configured_sync)
        llm_ok = llm_detail == "configured"
    else:
        ollama = await asyncio.to_thread(_check_ollama_sync)
        if ollama == "reachable":
            llm_detail = "ollama_reachable"
            llm_ok = True
        elif (OPENAI_API_KEY or "").strip():
            llm_detail = "ollama_unreachable_openai_key_present"
            llm_ok = False
        else:
            llm_detail = "ollama_unreachable_no_openai_key"
            llm_ok = False

    backend_ok = backend == "reachable"
    overall = "ready" if llm_ok and backend_ok else "degraded"

    payload: dict[str, Any] = {
        "status": overall,
        "llm_ok": llm_ok,
        "backend_ok": backend_ok,
        "checks": {
            "backend": backend,
            "llm": llm_detail,
            "llm_provider": LLM_PROVIDER,
        },
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("AGENT_API_PORT", "8001"))
    host = os.getenv("AGENT_API_HOST", "0.0.0.0")

    uvicorn.run(app, host=host, port=port)
