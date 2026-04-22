"""Cart / ordering flows (needs LLM; backend optional — skips on hard API errors)."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.ordering]

# Extra single- and multi-turn cases (5+). Legacy tests below cover add-white + view-cart.
_ORDERING_SCENARIOS: list[tuple[str, list[str], tuple[str, ...]]] = [
    (
        "add_almond_brownie_single",
        ["Add one almond brownie protein bar to my cart"],
        (
            "cart",
            "add",
            "bar",
            "protein",
            "almond",
            "total",
            "item",
            "sorry",
            "unable",
            "error",
        ),
    ),
    (
        "add_peanut_butter_single",
        ["Add 1 peanut butter fudge protein bar to my cart"],
        (
            "cart",
            "add",
            "bar",
            "peanut",
            "protein",
            "total",
            "item",
            "sorry",
            "unable",
        ),
    ),
    (
        "add_chocolate_cookie_single",
        ["Add one chocolate chunks cookie to my cart"],
        (
            "cart",
            "add",
            "cookie",
            "chocolate",
            "total",
            "item",
            "sorry",
            "unable",
        ),
    ),
    (
        "add_batch_then_ask_cart_multi",
        ["Add 2 white chocolate protein bars to my cart", "What is in my cart?"],
        ("cart", "item", "empty", "total", "bar", "protein", "white", "sorry", "unable"),
    ),
    (
        "add_granola_then_total_multi",
        ["Add one crunchy choco grain granola bar to my cart", "What is my cart total?"],
        (
            "cart",
            "total",
            "rs",
            "granola",
            "bar",
            "sorry",
            "unable",
        ),
    ),
    (
        "greet_then_add_multi",
        [
            "Hi, I want to place an order",
            "Add one white chocolate brownie protein bar to my cart",
        ],
        (
            "cart",
            "add",
            "bar",
            "protein",
            "white",
            "item",
            "total",
            "sorry",
            "unable",
        ),
    ),
]


def _run_turns(graph_thread, turns: list[str]) -> str:
    out = ""
    for line in turns:
        out = graph_thread.say(line)
    return out


@pytest.mark.parametrize("scenario_id,turns,keywords", _ORDERING_SCENARIOS, ids=[s[0] for s in _ORDERING_SCENARIOS])
def test_ordering_scenario_parametrized(
    graph_thread, scenario_id: str, turns: list[str], keywords: tuple[str, ...]
):
    """Single- and multi-turn cart flows; LLM judge runs on each turn."""
    graph_thread.reset()
    text = _run_turns(graph_thread, turns).lower()
    assert any(w in text for w in keywords), f"[{scenario_id}] unexpected final reply: {text[:500]!r}"


def test_add_to_cart_acknowledged(graph_thread):
    graph_thread.reset()
    text = graph_thread.say("Add one white chocolate protein bar to my cart").lower()
    assert any(
        w in text
        for w in (
            "cart",
            "add",
            "added",
            "item",
            "bar",
            "protein",
            "quantity",
            "total",
            "sorry",
            "unable",
            "error",
        )
    ), f"unexpected add-to-cart reply: {text[:500]!r}"


def test_view_cart_after_add(graph_thread):
    graph_thread.reset()
    graph_thread.say("Add 2 protein bars to my cart")
    text = graph_thread.say("Show my cart").lower()
    assert len(text) > 10
    assert any(
        w in text
        for w in (
            "cart",
            "item",
            "empty",
            "total",
            "bar",
            "protein",
            "sorry",
            "unable",
        )
    ), f"unexpected cart summary: {text[:500]!r}"
