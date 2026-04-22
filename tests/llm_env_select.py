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


def _verify_provider_runtime(env: Mapping[str, str], provider: str) -> str | None:
    """Return an error message if ``provider`` (ollama|openai) cannot run."""
    lp = provider.lower().strip()
    if lp == "openai":
        if not (env.get("OPENAI_API_KEY") or "").strip():
            return "openai requires OPENAI_API_KEY."
        return None
    if lp == "ollama":
        if not ollama_reachable(env):
            base = env.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
            return (
                f"Ollama is not reachable at {base}. Start Ollama, or set OPENAI_API_KEY "
                "for OpenAI fallback."
            )
        return None
    return f"Unknown LLM provider={lp!r}."


def verify_llm_runtime_available(env: MutableMapping[str, str] | None = None) -> str | None:
    """Return an error message if the configured provider cannot run tests (strict check)."""
    load_agent_dotenv()
    target = os.environ if env is None else env
    lp = (target.get("LLM_PROVIDER") or "ollama").lower().strip()
    if lp == "openai":
        msg = _verify_provider_runtime(target, "openai")
        if msg:
            return "LLM_PROVIDER=openai requires OPENAI_API_KEY." if "OPENAI_API_KEY" in msg else msg
        return None
    if lp == "ollama":
        msg = _verify_provider_runtime(target, "ollama")
        if msg:
            return (
                f"Ollama is not reachable at {target.get('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')}. "
                "Start Ollama, or set OPENAI_API_KEY (and unset LLM_PROVIDER or set LLM_PROVIDER=openai)."
            )
        return None
    return f"Unknown LLM_PROVIDER={lp!r}."


def judge_llm_skipped(env: Mapping[str, str] | None = None) -> bool:
    """When true, scenario tests skip the LLM-as-judge step (``AGENT_SKIP_LLM_JUDGE``)."""
    target = os.environ if env is None else env
    return (target.get("AGENT_SKIP_LLM_JUDGE") or "").lower() in ("1", "true", "yes")


def prepare_judge_llm_env(env: MutableMapping[str, str] | None = None) -> str | None:
    """Set ``AGENT_TEST_JUDGE_PROVIDER`` for the judge LLM (optional ``JUDGE_LLM_PROVIDER`` override)."""
    load_agent_dotenv()
    target = os.environ if env is None else env
    if judge_llm_skipped(target):
        return None
    override = (target.get("JUDGE_LLM_PROVIDER") or "").strip().lower()
    if override in ("openai", "ollama"):
        err = _verify_provider_runtime(target, override)
        if err:
            return f"JUDGE_LLM_PROVIDER={override} is not usable: {err}"
        target["AGENT_TEST_JUDGE_PROVIDER"] = override
        return None
    lp = (target.get("LLM_PROVIDER") or "ollama").strip().lower()
    target["AGENT_TEST_JUDGE_PROVIDER"] = lp
    return None


def verify_judge_llm_runtime_available(env: MutableMapping[str, str] | None = None) -> str | None:
    """Return an error if the judge LLM cannot run (skipped when ``AGENT_SKIP_LLM_JUDGE``)."""
    load_agent_dotenv()
    target = os.environ if env is None else env
    if judge_llm_skipped(target):
        return None
    err = prepare_judge_llm_env(target)
    if err:
        return err
    jp = (target.get("AGENT_TEST_JUDGE_PROVIDER") or "ollama").strip().lower()
    err_run = _verify_provider_runtime(target, jp)
    if err_run:
        return f"LLM judge ({jp}) is not reachable: {err_run}"
    return None


def judge_provider_label(env: Mapping[str, str] | None = None) -> str:
    env = env or os.environ
    if judge_llm_skipped(env):
        return "skipped (AGENT_SKIP_LLM_JUDGE)"
    jp = (env.get("AGENT_TEST_JUDGE_PROVIDER") or env.get("LLM_PROVIDER") or "ollama").lower().strip()
    if jp == "openai":
        m = (env.get("JUDGE_OPENAI_MODEL") or env.get("OPENAI_MODEL") or "gpt-4o-mini").strip()
        return f"judge OpenAI ({m})"
    base = env.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    m = (env.get("JUDGE_OLLAMA_MODEL") or env.get("OLLAMA_MODEL") or "llama3.1:8b").strip()
    return f"judge Ollama ({m} @ {base})"


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
