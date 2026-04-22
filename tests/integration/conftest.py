"""Fixtures for scenario integration tests."""
from __future__ import annotations

import os

# Before FAISS / PyTorch import: avoid macOS OpenMP duplicate-lib abort (OMP #15).
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
# Quieter console: no full prompt dumps (see utils/logger.log_prompt).
os.environ.setdefault("AGENT_TEST_MINIMAL_LOGS", "1")

import sys
import time
from pathlib import Path
from typing import Any, Callable

import pytest

_AGENT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

from tests.llm_env_select import llm_provider_label, prepare_llm_env, verify_llm_runtime_available
from tests.llm_test_utils import (
    continue_state,
    last_assistant_text,
    llm_unreachable,
    make_receptionist_state,
)


def _emit_scenario_line(user_text: str, result: dict[str, Any], elapsed: float, out_text: str) -> None:
    """Stderr: full user message, arrow routing (intent / handoff), latency, full assistant reply."""
    intent = result.get("intent")
    agent = result.get("active_agent")
    dest = agent if agent else "__end__"
    dim, bold, reset = "\033[2m", "\033[1m", "\033[0m"
    muted, path_c = "\033[90m", "\033[36m"
    arrow = f"{muted} -->{reset}"
    reply = (out_text or "").rstrip("\n")
    if not reply:
        reply = "(empty)"
    sys.stderr.write(f"{dim}{'─' * 56}{reset}\n")
    sys.stderr.write(f"{bold}you{reset}\n{user_text}\n")
    sys.stderr.write(
        f"{path_c}router{reset} {arrow} intent={intent!r} {arrow} {dest!r}  {dim}({elapsed:.2f}s){reset}\n"
    )
    sys.stderr.write(f"{bold}assistant{reset}\n{reply}\n")


def pytest_configure(config: pytest.Config) -> None:
    """Stream stdout live during integration runs (agent logger writes to stdout)."""
    try:
        cap = config.getoption("--capture")
    except (ValueError, AttributeError):
        return
    # Respect explicit -s / --capture=no
    if cap in ("fd", "sys"):
        config.option.capture = "tee-sys"


def _session_collects_integration_tests(session: pytest.Session) -> bool:
    """True if collected items include ``tests/integration`` (including ``--collect-only``)."""
    for item in session.items or []:
        try:
            parts = item.path.parts
        except AttributeError:
            continue
        for i in range(len(parts) - 1):
            if parts[i] == "tests" and parts[i + 1] == "integration":
                return True
    return False


def pytest_collection_finish(session: pytest.Session) -> None:
    """After collection, items exist: enforce LLM availability (``sessionstart`` is too early)."""
    if not _session_collects_integration_tests(session):
        session.config._scenario_integration_hooks = False
        return

    if getattr(session.config.option, "collectonly", False):
        sys.stderr.write(
            "\n\033[33mNote:\033[0m --collect-only lists tests; it does \033[1mnot\033[0m call the LLM or backend. "
            "Run without --collect-only to execute (Ollama or OPENAI_API_KEY required).\n\n"
        )
        return

    err = prepare_llm_env(os.environ)
    if err:
        pytest.exit(
            f"\n\033[91mCannot run scenario integration tests:\033[0m\n  {err}\n",
            returncode=2,
        )
    err_run = verify_llm_runtime_available(os.environ)
    if err_run:
        pytest.exit(
            f"\n\033[91mCannot run scenario integration tests:\033[0m\n  {err_run}\n",
            returncode=2,
        )
    session.config._scenario_integration_hooks = True


def pytest_sessionstart(session: pytest.Session) -> None:
    if getattr(session.config, "_scenario_integration_hooks", False):
        session.config._scenario_suite_start = time.perf_counter()
        # stdout: only WARNING+ from agent logger; stderr turn blocks show user/reply/arrows/time.
        if os.getenv("AGENT_LOG_FULL_PROMPTS", "").lower() not in ("1", "true", "yes"):
            from utils.logger import apply_scenario_trace_logging

            apply_scenario_trace_logging()


def pytest_exception_interact(node, call, report) -> None:
    """After a failure, point to the log file for full prompts (console stays minimal)."""
    if report.when != "call" or not report.failed:
        return
    logf = Path(__file__).resolve().parent.parent / "logs" / "agent.log"
    sys.stderr.write(
        f"\n\033[33mTip:\033[0m full prompts and verbose history are logged at DEBUG in:\n  {logf}\n"
        "Set AGENT_LOG_FULL_PROMPTS=1 before the run to print full prompts to the console.\n\n"
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Short pass/fail/skip summary after scenario integration runs."""
    if not getattr(session.config, "_scenario_integration_hooks", False):
        return
    start = getattr(session.config, "_scenario_suite_start", None)
    elapsed_s = (time.perf_counter() - start) if start is not None else 0.0

    passed = failed = skipped = errors = 0
    tr = session.config.pluginmanager.get_plugin("terminalreporter")
    if tr is not None and hasattr(tr, "stats"):
        passed = len(tr.stats.get("passed", []))
        failed = len(tr.stats.get("failed", []))
        skipped = len(tr.stats.get("skipped", []))
        errors = len(tr.stats.get("error", []))

    bold, dim, reset = "\033[1m", "\033[2m", "\033[0m"
    ok, bad, skip_c, err_c, dim_m = (
        "\033[32m",
        "\033[31m",
        "\033[33m",
        "\033[31m",
        "\033[36m",
    )
    line = "─" * 52
    print(f"\n{dim_m}{line}{reset}")
    print(f"{bold}  Scenario run summary{reset}  {dim}({elapsed_s:.1f}s){reset}")
    print(f"{dim_m}{line}{reset}")
    print(
        f"  {ok}passed{reset} {passed}   "
        f"{bad}failed{reset} {failed}   "
        f"{skip_c}skipped{reset} {skipped}   "
        f"{err_c}errors{reset} {errors}"
    )
    print(f"  {dim}LLM:{reset} {llm_provider_label(os.environ)}")
    total_ran = passed + failed + skipped + errors
    if total_ran and passed == 0 and failed == 0 and errors == 0 and skipped == total_ran:
        print(
            f"  {bad}Warning:{reset} every test was {skip_c}skipped{reset} — "
            "the LLM may have been unreachable mid-run. Check Ollama / OPENAI_API_KEY."
        )
    status_txt = "OK" if exitstatus == 0 else f"exit {exitstatus}"
    status_color = ok if exitstatus == 0 else bad
    print(f"  {dim}Result:{reset} {status_color}{status_txt}{reset}")
    print(f"{dim_m}{line}{reset}\n")


def _llm_configured() -> bool:
    provider = (os.getenv("LLM_PROVIDER") or "ollama").lower().strip()
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    return True


@pytest.fixture(scope="module")
def receptionist_graph():
    from graph.main import receptionist_graph as graph

    return graph


@pytest.fixture
def invoke_graph(receptionist_graph) -> Callable[..., dict[str, Any]]:
    """Single-turn invoke: (user_text, *, thread_id=..., customer_id=...) -> result dict."""

    def _invoke(
        user_text: str,
        *,
        thread_id: str = "thread-default",
        customer_id: str = "test_customer",
    ) -> dict[str, Any]:
        if not _llm_configured():
            pytest.skip("OPENAI_API_KEY not set while LLM_PROVIDER=openai")
        state = make_receptionist_state(
            user_text, conversation_id=thread_id, customer_id=customer_id
        )
        cfg: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        t0 = time.perf_counter()
        try:
            result = receptionist_graph.invoke(state, cfg)
        except BaseException as exc:
            if llm_unreachable(exc):
                pytest.skip(f"LLM unreachable: {exc}")
            raise
        elapsed = time.perf_counter() - t0
        out_text = last_assistant_text(result.get("messages"))
        _emit_scenario_line(user_text, result, elapsed, out_text)
        return result

    return _invoke


@pytest.fixture
def reply_text(invoke_graph) -> Callable[[str], str]:
    """Single user line -> last assistant string."""

    def _reply(user_text: str, *, thread_id: str | None = None) -> str:
        tid = thread_id or f"r-{hash(user_text) % 1_000_000_000}"
        result = invoke_graph(user_text, thread_id=tid)
        return last_assistant_text(result.get("messages"))

    return _reply


@pytest.fixture
def graph_thread(receptionist_graph):
    """Multi-turn helper: call ``reset()`` before a test for an isolated thread."""

    class _T:
        def __init__(self) -> None:
            self._n = 0
            self.thread_id = "mt-0"
            self._last: dict[str, Any] | None = None

        def reset(self) -> None:
            self._n += 1
            self.thread_id = f"mt-{self._n}"
            self._last = None

        def say(self, user_text: str) -> str:
            if not _llm_configured():
                pytest.skip("OPENAI_API_KEY not set while LLM_PROVIDER=openai")
            if self._last is None:
                state = make_receptionist_state(
                    user_text, conversation_id=self.thread_id, customer_id="test_customer"
                )
            else:
                state = continue_state(self._last, user_text)
            cfg: dict[str, Any] = {"configurable": {"thread_id": self.thread_id}}
            t0 = time.perf_counter()
            try:
                self._last = receptionist_graph.invoke(state, cfg)
            except BaseException as exc:
                if llm_unreachable(exc):
                    pytest.skip(f"LLM unreachable: {exc}")
                raise
            elapsed = time.perf_counter() - t0
            out_text = last_assistant_text(self._last.get("messages"))
            _emit_scenario_line(user_text, self._last, elapsed, out_text)
            return out_text

    return _T()
