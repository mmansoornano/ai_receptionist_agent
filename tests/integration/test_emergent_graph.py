"""Emergent-behavior checks: super-step budget and optional router-thrashing heuristic."""
from __future__ import annotations

import os

import pytest

from tests.llm_test_utils import make_receptionist_state

pytestmark = [pytest.mark.integration, pytest.mark.emergent]


def _llm_configured() -> bool:
    return (os.getenv("LLM_PROVIDER") or "ollama").lower().strip() != "openai" or bool(
        os.getenv("OPENAI_API_KEY")
    )


def test_invocation_respects_step_budget() -> None:
    """A single benign turn should not require an excessive number of graph super-steps."""
    if not _llm_configured():
        pytest.skip("OPENAI_API_KEY not set for LLM_PROVIDER=openai")
    from graph.main import receptionist_graph
    from tests.graph_telemetry import DEFAULT_TEST_RECURSION_LIMIT, invoke_with_telemetry

    state = make_receptionist_state("hi", conversation_id="emergent-step-budget", customer_id="test_c")
    cfg: dict = {"configurable": {"thread_id": "emergent-step-budget"}}
    _final, steps, _hist = invoke_with_telemetry(
        receptionist_graph,
        state,
        cfg,
        recursion_limit=DEFAULT_TEST_RECURSION_LIMIT,
        include_node_histogram=False,
    )
    # Typical path: router + qa + optional small loop — stay well under limit.
    assert steps <= 24, f"expected modest super-step count, got {steps}"


def test_router_thrashing_not_suspect_on_simple_greeting() -> None:
    """With node histogram, router should not re-enter a huge number of times for 'hi'."""
    if not _llm_configured():
        pytest.skip("OPENAI_API_KEY not set for LLM_PROVIDER=openai")
    from graph.main import receptionist_graph
    from tests.graph_telemetry import invoke_with_telemetry, router_reentry_would_be_suspicious

    state = make_receptionist_state("hi", conversation_id="emergent-router", customer_id="test_c")
    cfg: dict = {"configurable": {"thread_id": "emergent-router"}}
    _final, _steps, hist = invoke_with_telemetry(
        receptionist_graph,
        state,
        cfg,
        include_node_histogram=True,
    )
    if not hist:
        pytest.skip("no node histogram (stream_mode=updates not available in this run)")
    assert not router_reentry_would_be_suspicious(
        hist, max_router=8
    ), f"unexpected router thrashing histogram={hist!r}"
