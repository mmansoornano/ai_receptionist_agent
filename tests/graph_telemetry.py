"""Stream-based graph telemetry for emergent-behavior tests (step counts, node visits)."""
from __future__ import annotations

from typing import Any

from graph.state import ReceptionistState

DEFAULT_TEST_RECURSION_LIMIT = 40


def invoke_with_telemetry(
    graph: Any,
    state: ReceptionistState,
    config: dict[str, Any] | None = None,
    *,
    recursion_limit: int = DEFAULT_TEST_RECURSION_LIMIT,
    include_node_histogram: bool = False,
) -> tuple[ReceptionistState, int, dict[str, int]]:
    """
    Run the compiled graph, returning (final_state, super_step_count, node_histogram).

    *super_step_count* is the number of ``stream_mode="values"`` emissions (one per super-step).
    *node_histogram* is only filled when *include_node_histogram* is true (a second
    full graph run using ``stream_mode="updates"``); use for router-thrashing heuristics.
    """
    cfg: dict[str, Any] = {**(config or {}), "recursion_limit": max(1, int(recursion_limit))}
    final_state: ReceptionistState | None = None
    super_steps = 0

    stream = getattr(graph, "stream", None)
    if not callable(stream):
        out = graph.invoke(state, cfg)
        return out, 1, {}

    try:
        for chunk in stream(state, cfg, stream_mode="values"):
            super_steps += 1
            if isinstance(chunk, dict):
                final_state = chunk  # type: ignore[assignment]
    except TypeError:
        for chunk in stream(state, cfg):
            super_steps += 1
            if isinstance(chunk, dict):
                final_state = chunk  # type: ignore[assignment]

    if final_state is None:
        final_state = graph.invoke(state, cfg)  # type: ignore[assignment]
        if super_steps == 0:
            super_steps = 1

    node_histogram: dict[str, int] = {}
    if include_node_histogram and callable(stream):
        try:
            for ev in stream(state, cfg, stream_mode="updates"):
                if isinstance(ev, dict):
                    for node in ev:
                        node_histogram[str(node)] = node_histogram.get(str(node), 0) + 1
        except (TypeError, Exception):
            pass

    return final_state, max(super_steps, 1), node_histogram


def router_reentry_would_be_suspicious(
    node_histogram: dict[str, int],
    *,
    max_router: int = 4,
) -> bool:
    """Heuristic: many router node updates in one run may indicate thrashing."""
    if not node_histogram:
        return False
    r = int(node_histogram.get("router", 0))
    return r > max_router
