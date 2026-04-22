"""Shared pytest fixtures for AI_receptionist_agent tests."""
from __future__ import annotations

import os

# Applies to all tests under tests/ (including test_agent_flow.py, not only tests/integration/).
# Force minimal prompt console output during pytest unless explicitly requesting full prompts.
if os.getenv("AGENT_LOG_FULL_PROMPTS", "").lower() not in ("1", "true", "yes"):
    os.environ["AGENT_TEST_MINIMAL_LOGS"] = "1"
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import sys
from pathlib import Path

from typing import Any

import pytest
from langchain_core.messages import HumanMessage

# Ensure package root is on path when tests are collected from any cwd
_AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

from graph.state import ReceptionistState

_UNSET = object()


def pytest_configure(config: pytest.Config) -> None:
    """Quiet third-party INFO that looks like prompts (LangChain / httpx) during tests."""
    if os.getenv("AGENT_LOG_FULL_PROMPTS", "").lower() in ("1", "true", "yes"):
        return
    import logging

    for name in (
        "langchain",
        "langchain_core",
        "langchain_community",
        "langchain_ollama",
        "langchain_openai",
        "httpx",
        "httpcore",
        "openai",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


def pytest_collection_finish(session: pytest.Session) -> None:
    """After collection, clarify fast-only runs (``sessionstart`` often has no items yet)."""
    if getattr(session.config.option, "collectonly", False):
        return
    items = session.items or []
    if not items:
        return

    def _under_tests_integration(item: pytest.Item) -> bool:
        try:
            parts = item.path.parts
        except AttributeError:
            return False
        for i in range(len(parts) - 1):
            if parts[i] == "tests" and parts[i + 1] == "integration":
                return True
        return False

    if any(_under_tests_integration(item) for item in items):
        return
    sys.stderr.write(
        "\n\033[2mNote: This session only runs fast/unit tests (mocked HTTP and router). "
        "They do not use Ollama, OpenAI, or your Django backend — "
        "passing here does not mean the agent or backend is up.\033[0m\n"
        "\033[2mFor LLM scenario tests:  python tests/run_scenario_tests.py conversation\033[0m\n"
        "\033[2m(or: pytest tests/integration -m integration)\033[0m\n\n"
    )


def minimal_receptionist_state(
    *,
    messages: list | None = None,
    conversation_id: str = "test_conv",
    customer_id: str = "test_customer",
    **overrides,
) -> ReceptionistState:
    """Build a minimal valid ReceptionistState for router/graph tests."""
    base: ReceptionistState = {
        "messages": messages if messages is not None else [],
        "intent": None,
        "conversation_context": None,
        "customer_info": None,
        "cart_data": None,
        "order_data": None,
        "payment_data": None,
        "channel": "sms",
        "language": "en",
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "active_agent": None,
    }
    base.update(overrides)
    return base


@pytest.fixture
def receptionist_state_factory():
    """Callable fixture: (messages=..., **kwargs) -> ReceptionistState.

    Pass ``messages=[]`` for empty history. Omit ``messages`` for a default
    single HumanMessage placeholder.
    """

    def _factory(messages=_UNSET, **kwargs):
        if messages is _UNSET:
            messages = [HumanMessage(content="Hello")]
        return minimal_receptionist_state(messages=messages, **kwargs)

    return _factory


def pytest_terminal_summary(terminalreporter: Any, exitstatus: int, config: Any) -> None:
    """Extra readable pass/fail/skip totals when running scenario CLI."""
    if os.environ.get("AGENT_SCENARIO_RUN") != "1":
        return
    rep = terminalreporter
    passed = len(rep.stats.get("passed", []))
    failed = len(rep.stats.get("failed", []))
    skipped = len(rep.stats.get("skipped", []))
    green, red, yellow, dim, reset = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
    rep.write_sep("=", f"{dim}Result overview{reset}", blue=True)
    rep.write_line(f"  {green}Passed{reset}:   {passed}")
    rep.write_line(f"  {red}Failed{reset}:   {failed}")
    rep.write_line(f"  {yellow}Skipped{reset}: {skipped}")
    if failed:
        rep.write_line(f"\n{red}Suite result: FAILED{reset} (exit {exitstatus})")
    else:
        rep.write_line(f"\n{green}Suite result: PASSED{reset} (no failures; exit {exitstatus})")
