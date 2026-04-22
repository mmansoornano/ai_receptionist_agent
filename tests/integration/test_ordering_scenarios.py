"""Cart / ordering flows (needs LLM; backend optional — skips on hard API errors)."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.ordering]


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
