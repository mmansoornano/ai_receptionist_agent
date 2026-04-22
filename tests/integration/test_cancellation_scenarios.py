"""Cancellation and refund-style questions (store policy: no cancel/refund after baking starts)."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.cancellation]

# Reply should reflect store policy: baking / no refund after production starts, contact CS, etc.
_CANCELLATION_KEYWORDS = (
    "baking",
    "refund",
    "cancel",
    "order",
    "policy",
    "after",
    "cannot",
    "can't",
    "no",
    "contact",
    "customer",
    "phone",
    "help",
    "sorry",
    "start",
    "production",
    "eligible",
    "return",
)

_CANCELLATION_PROMPTS = [
    "I want to cancel my last order",
    "How do refunds work?",
    "Can I cancel an order after it ships?",
    "I changed my mind — how do I cancel my cart?",
    "What is your refund policy for damaged items?",
    "I need to speak to someone about a wrong item in my delivery.",
    "How long do refunds take to process?",
    "If I return an unopened box, do I get a full refund?",
]

_CANCELLATION_MULTI: list[tuple[str, list[str], tuple[str, ...]]] = [
    (
        "ordered_then_change_mind",
        [
            "I just placed an order for protein bars",
            "Actually I need to cancel it completely — how?",
        ],
        _CANCELLATION_KEYWORDS,
    ),
    (
        "refund_reason_then_process",
        [
            "One of my bars arrived melted",
            "What is the process for a refund or replacement?",
        ],
        _CANCELLATION_KEYWORDS,
    ),
    (
        "track_then_cancel_confusion",
        ["My order still says processing — can I still cancel it?"],
        _CANCELLATION_KEYWORDS,
    ),
]


@pytest.mark.parametrize("prompt", _CANCELLATION_PROMPTS, ids=[f"single_{i}" for i in range(len(_CANCELLATION_PROMPTS))])
def test_cancellation_or_policy_reply(reply_text, prompt: str):
    text = reply_text(prompt).lower()
    assert len(text) > 15
    assert any(w in text for w in _CANCELLATION_KEYWORDS), (
        f"expected policy-aware reply (baking / no refund after start / contact): {text[:600]!r}"
    )


def _run_turns(graph_thread, turns: list[str]) -> str:
    out = ""
    for line in turns:
        out = graph_thread.say(line)
    return out


@pytest.mark.parametrize("scenario_id,turns,keywords", _CANCELLATION_MULTI, ids=[m[0] for m in _CANCELLATION_MULTI])
def test_cancellation_multi_turn(
    graph_thread, scenario_id: str, turns: list[str], keywords: tuple[str, ...]
):
    graph_thread.reset()
    text = _run_turns(graph_thread, turns).lower()
    assert len(text) > 15
    assert any(w in text for w in keywords), f"[{scenario_id}] {text[:600]!r}"
