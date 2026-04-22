"""Cancellation and refund-style questions."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.cancellation]


@pytest.mark.parametrize(
    "prompt",
    [
        "I want to cancel my last order",
        "How do refunds work?",
    ],
)
def test_cancellation_or_policy_reply(reply_text, prompt: str):
    text = reply_text(prompt).lower()
    assert len(text) > 15
    assert any(
        w in text
        for w in (
            "cancel",
            "refund",
            "order",
            "policy",
            "customer",
            "support",
            "phone",
            "help",
            "unable",
            "sorry",
        )
    ), f"expected cancellation/refund-oriented reply: {text[:600]!r}"
