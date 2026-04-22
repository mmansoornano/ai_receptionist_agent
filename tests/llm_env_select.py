"""Pick LLM for tests: reachable Ollama first, else OpenAI when ``OPENAI_API_KEY`` is set.

Even if ``.env`` has ``LLM_PROVIDER=ollama``, tests fall back to OpenAI when Ollama is down
and a key exists (same as leaving ``LLM_PROVIDER`` unset).

Used by ``run_scenario_tests.py`` and ``tests/integration/conftest.py`` so direct
``pytest tests/integration`` matches the scenario runner behavior.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Mapping, MutableMapping


def load_agent_dotenv() -> None:
    """Load ``AI_receptionist_agent/.env`` into ``os.environ`` (existing vars are not overridden)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parent.parent
    path = root / ".env"
    if path.is_file():
        load_dotenv(path)
    else:
        load_dotenv()


def ollama_reachable(env: Mapping[str, str] | None = None) -> bool:
    env = env or os.environ
    base = (env.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
    try:
        urllib.request.urlopen(f"{base}/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def verify_llm_runtime_available(env: MutableMapping[str, str] | None = None) -> str | None:
    """Return an error message if the configured provider cannot run tests (strict check)."""
    load_agent_dotenv()
    target = os.environ if env is None else env
    lp = (target.get("LLM_PROVIDER") or "ollama").lower().strip()
    if lp == "openai":
        if not (target.get("OPENAI_API_KEY") or "").strip():
            return "LLM_PROVIDER=openai requires OPENAI_API_KEY."
        return None
    if lp == "ollama":
        if not ollama_reachable(target):
            base = target.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
            return (
                f"Ollama is not reachable at {base}. Start Ollama, or set OPENAI_API_KEY "
                "(and unset LLM_PROVIDER or set LLM_PROVIDER=openai)."
            )
        return None
    return f"Unknown LLM_PROVIDER={lp!r}."


def prepare_llm_env(env: MutableMapping[str, str] | None = None) -> str | None:
    """Resolve ``LLM_PROVIDER`` for tests: live Ollama first, else OpenAI when a key exists.

    If ``.env`` sets ``LLM_PROVIDER=ollama`` but Ollama is down, falls back to OpenAI when
    ``OPENAI_API_KEY`` is set (so scenario runs match ``LLM_PROVIDER`` unset behavior).

    Mutates ``env`` in place (defaults to ``os.environ``).

    Returns:
        ``None`` on success, or an error message if configuration is invalid /
        no LLM is available.
    """
    load_agent_dotenv()
    target = os.environ if env is None else env
    raw = (target.get("LLM_PROVIDER") or "").strip()
    lp = raw.lower() if raw else ""

    if lp == "openai":
        if not (target.get("OPENAI_API_KEY") or "").strip():
            return "LLM_PROVIDER=openai but OPENAI_API_KEY is not set."
        return None

    # Unset or ollama: prefer reachable Ollama, else OpenAI if key is present
    if lp in ("", "ollama"):
        if ollama_reachable(target):
            target["LLM_PROVIDER"] = "ollama"
            return None
        if (target.get("OPENAI_API_KEY") or "").strip():
            target["LLM_PROVIDER"] = "openai"
            return None
        base = target.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        return (
            f"No LLM available: Ollama is not reachable at {base} and OPENAI_API_KEY is not set. "
            "Start Ollama or set OPENAI_API_KEY in .env."
        )

    return f"Unknown LLM_PROVIDER={raw!r}."


def llm_provider_label(env: Mapping[str, str] | None = None) -> str:
    env = env or os.environ
    p = (env.get("LLM_PROVIDER") or "").lower() or "(unset)"
    if p == "openai":
        return "OpenAI (LLM_PROVIDER=openai)"
    if p == "ollama":
        base = env.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        return f"Ollama ({base})"
    return p
