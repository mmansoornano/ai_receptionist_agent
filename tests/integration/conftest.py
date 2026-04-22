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
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

import pytest
from pytest import CaptureFixture

_AGENT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

from tests.llm_env_select import (
    judge_llm_skipped,
    judge_provider_label,
    llm_provider_label,
    prepare_judge_llm_env,
    prepare_llm_env,
    verify_judge_llm_runtime_available,
    verify_llm_runtime_available,
)
from tests.llm_test_utils import (
    build_tool_summary,
    continue_state,
    last_assistant_text,
    llm_unreachable,
    make_receptionist_state,
)
from tests.scenario_display import emit_scenario_turn_box as _emit_scenario_turn_box


def _print_turn_box_visible(
    config: pytest.Config, capsys: CaptureFixture[str], emit: Callable[[], None]
) -> None:
    """Show the turn box on the real TTY. ``capsys.disabled()`` alone can miss fd capture; suspend capturemanager too."""
    capman = None
    pm = config.pluginmanager
    _get = getattr(pm, "get_plugin", None) or getattr(pm, "getplugin", None)
    if _get is not None:
        try:
            capman = _get("capturemanager")
        except LookupError:
            capman = None
    if capman is not None:
        suspend = getattr(capman, "suspend_global_capture", None)
        resume = getattr(capman, "resume_global_capture", None)
        if callable(suspend) and callable(resume):
            suspend(in_=True)
            try:
                emit()
                sys.stderr.flush()
            finally:
                resume()
            return
    with capsys.disabled():
        emit()
    sys.stderr.flush()


def _scenario_kind_for_request(request: pytest.FixtureRequest) -> Literal["normal", "hostile"]:
    return "hostile" if request.node.get_closest_marker("security") else "normal"


def _append_turn_metrics(
    request: pytest.FixtureRequest,
    user_text: str,
    result: dict[str, Any] | None,
    elapsed: float,
    turn_index: int,
    tool_summary: str,
    super_step: int | None,
    node_histogram: dict[str, int] | None,
    verdict: Any,
) -> None:
    mdir = (os.environ.get("AGENT_METRICS_DIR") or "").strip()
    if not mdir:
        return
    from tests.metrics_report import TurnMetricRecord, append_turn

    skipped = judge_llm_skipped(os.environ)
    v = None if skipped else verdict
    append_turn(
        TurnMetricRecord(
            source="pytest",
            suite=request.path.stem,
            scenario_id=request.node.name,
            turn_index=turn_index,
            user_text=user_text[:4000],
            elapsed_s=elapsed,
            intent=(result or {}).get("intent"),
            active_agent=(result or {}).get("active_agent"),
            super_step_count=super_step,
            node_histogram=node_histogram,
            tool_summary=tool_summary[:2000],
            judge_skipped=skipped,
            correct=None if v is None else v.correct,
            no_pii=None if v is None else v.no_pii,
            attack_handling_ok=None if v is None else v.attack_handling_ok,
            grounded_in_tools=None if v is None else v.grounded_in_tools,
            tool_use_reasonable=None if v is None else v.tool_use_reasonable,
            passed=None if v is None else v.passed,
            reason=None if v is None else (v.reason[:800] if getattr(v, "reason", None) else None),
        )
    )


def _apply_llm_judge(
    user_text: str,
    out_text: str,
    scenario_kind: Literal["normal", "hostile"],
    *,
    request: pytest.FixtureRequest,
    result: dict[str, Any],
    elapsed: float,
    turn_index: int,
    tool_summary: str,
    super_step: int | None = None,
    node_histogram: dict[str, int] | None = None,
    config: pytest.Config | None,
    capsys: CaptureFixture[str] | None,
) -> None:
    if judge_llm_skipped(os.environ):
        _append_turn_metrics(
            request, user_text, result, elapsed, turn_index, tool_summary, super_step, node_histogram, None
        )
        return
    from tests.llm_judge import evaluate_turn, format_judge_failure, write_judge_rubric_chart

    try:
        verdict = evaluate_turn(
            user_text, out_text, scenario_kind=scenario_kind, tool_summary=tool_summary or None
        )
    except BaseException as exc:
        if llm_unreachable(exc):
            pytest.skip(f"LLM judge unreachable: {exc}")
        raise

    def _emit_rubric() -> None:
        write_judge_rubric_chart(verdict)

    if config is not None and capsys is not None:
        _print_turn_box_visible(config, capsys, _emit_rubric)
    else:
        _emit_rubric()

    _append_turn_metrics(
        request, user_text, result, elapsed, turn_index, tool_summary, super_step, node_histogram, verdict
    )

    if not verdict.passed:
        pytest.fail(format_judge_failure(verdict))


def pytest_configure(config: pytest.Config) -> None:
    """Optional live tee of stdout; off by default so agent logs stay hidden unless a test fails."""
    if os.environ.get("AGENT_SCENARIO_LIVE_LOGS", "").lower() not in ("1", "true", "yes"):
        return
    try:
        cap = config.getoption("--capture")
    except (ValueError, AttributeError):
        return
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
    err_j = prepare_judge_llm_env(os.environ)
    if err_j:
        pytest.exit(
            f"\n\033[91mCannot run scenario integration tests (LLM judge):\033[0m\n  {err_j}\n",
            returncode=2,
        )
    err_j_run = verify_judge_llm_runtime_available(os.environ)
    if err_j_run:
        pytest.exit(
            f"\n\033[91mCannot run scenario integration tests (LLM judge):\033[0m\n  {err_j_run}\n",
            returncode=2,
        )
    session.config._scenario_integration_hooks = True


def pytest_sessionstart(session: pytest.Session) -> None:
    if (os.environ.get("AGENT_METRICS_DIR") or "").strip():
        from tests.metrics_report import clear_metrics_buffer

        clear_metrics_buffer()
    if getattr(session.config, "_scenario_integration_hooks", False):
        session.config._scenario_suite_start = time.perf_counter()
        # Console: agent INFO suppressed. Each turn prints a box (capturemanager suspend + capsys fallback).
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
    print(f"  {dim}Agent LLM:{reset} {llm_provider_label(os.environ)}")
    print(f"  {dim}Judge LLM:{reset} {judge_provider_label(os.environ)}")
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

    mdir = (os.environ.get("AGENT_METRICS_DIR") or "").strip()
    if mdir and getattr(session.config, "_scenario_integration_hooks", False):
        from tests.metrics_report import build_static_html, write_metrics_from_buffer

        out = Path(mdir)
        out.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        jp = out / f"metrics-pytest-{stamp}.json"
        write_metrics_from_buffer(jp, source="pytest")
        build_static_html(jp, out / f"metrics-pytest-{stamp}.html")
        print(f"{dim}  Metrics written:{reset} {jp}")


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
def invoke_graph(receptionist_graph, capsys, request) -> Callable[..., dict[str, Any]]:
    """Single-turn invoke: (user_text, *, thread_id=..., customer_id=...) -> result dict."""

    def _invoke(
        user_text: str,
        *,
        thread_id: str = "thread-default",
        customer_id: str = "test_customer",
        scenario_kind: Literal["normal", "hostile"] | None = None,
    ) -> dict[str, Any]:
        if not _llm_configured():
            pytest.skip("OPENAI_API_KEY not set while LLM_PROVIDER=openai")
        sk = scenario_kind or _scenario_kind_for_request(request)
        state = make_receptionist_state(
            user_text, conversation_id=thread_id, customer_id=customer_id
        )
        cfg: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
        t0 = time.perf_counter()
        super_n: int | None = None
        hist: dict[str, int] | None = None
        try:
            if (os.environ.get("AGENT_METRICS_TELEMETRY", "").lower() in ("1", "true", "yes")):
                from tests.graph_telemetry import invoke_with_telemetry

                result, super_n, hist = invoke_with_telemetry(
                    receptionist_graph,
                    state,
                    cfg,
                    include_node_histogram=True,
                )
            else:
                result = receptionist_graph.invoke(state, cfg)
        except BaseException as exc:
            if llm_unreachable(exc):
                pytest.skip(f"LLM unreachable: {exc}")
            raise
        elapsed = time.perf_counter() - t0
        out_text = last_assistant_text(result.get("messages"))
        ts = build_tool_summary(result.get("messages"))

        def _emit() -> None:
            _emit_scenario_turn_box(user_text, result, elapsed, out_text)

        _print_turn_box_visible(request.config, capsys, _emit)
        _apply_llm_judge(
            user_text,
            out_text,
            sk,
            request=request,
            result=result,
            elapsed=elapsed,
            turn_index=0,
            tool_summary=ts,
            super_step=super_n,
            node_histogram=hist,
            config=request.config,
            capsys=capsys,
        )
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
def graph_thread(receptionist_graph, capsys, request):
    """Multi-turn helper: call ``reset()`` before a test for an isolated thread."""

    class _T:
        def __init__(self) -> None:
            self._n = 0
            self.thread_id = f"mt-init-{uuid.uuid4().hex[:8]}"
            self._customer_id = f"itest-{uuid.uuid4().hex[:12]}"
            self._turn_i = -1
            self._last: dict[str, Any] | None = None
            self._request = request

        def reset(self) -> None:
            from tests.cache_reset import clear_in_memory_caches_for_new_scenario

            # Fresh prompt/guard/judge in-memory state so the agent does not carry prior test data.
            clear_in_memory_caches_for_new_scenario()
            self._n += 1
            # Unique per test: LangGraph checkpointers key on thread_id — reusing mt-1, mt-2
            # across tests would restore another test's messages and break cart / customer_id.
            tid = uuid.uuid4().hex[:16]
            self.thread_id = f"mt-{tid}"
            self._customer_id = f"itest-{tid}"
            self._last = None
            self._turn_i = -1

        def say(self, user_text: str) -> str:
            if not _llm_configured():
                pytest.skip("OPENAI_API_KEY not set while LLM_PROVIDER=openai")
            self._turn_i += 1
            if self._last is None:
                state = make_receptionist_state(
                    user_text,
                    conversation_id=self.thread_id,
                    customer_id=self._customer_id,
                )
            else:
                state = continue_state(self._last, user_text)
            cfg: dict[str, Any] = {"configurable": {"thread_id": self.thread_id}}
            t0 = time.perf_counter()
            super_n: int | None = None
            hist: dict[str, int] | None = None
            try:
                if (os.environ.get("AGENT_METRICS_TELEMETRY", "").lower() in ("1", "true", "yes")):
                    from tests.graph_telemetry import invoke_with_telemetry

                    self._last, super_n, hist = invoke_with_telemetry(
                        receptionist_graph, state, cfg, include_node_histogram=True
                    )
                else:
                    self._last = receptionist_graph.invoke(state, cfg)
            except BaseException as exc:
                if llm_unreachable(exc):
                    pytest.skip(f"LLM unreachable: {exc}")
                raise
            elapsed = time.perf_counter() - t0
            out_text = last_assistant_text(self._last.get("messages"))
            ts = build_tool_summary(self._last.get("messages"))

            def _emit() -> None:
                _emit_scenario_turn_box(user_text, self._last, elapsed, out_text)

            _print_turn_box_visible(self._request.config, capsys, _emit)
            sk = _scenario_kind_for_request(self._request)
            _apply_llm_judge(
                user_text,
                out_text,
                sk,
                request=self._request,
                result=self._last,
                elapsed=elapsed,
                turn_index=self._turn_i,
                tool_summary=ts,
                super_step=super_n,
                node_histogram=hist,
                config=self._request.config,
                capsys=capsys,
            )
            return out_text

    return _T()
