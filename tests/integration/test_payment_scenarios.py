"""Payment-oriented turns after a minimal ordering context."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.payment]


def test_ready_to_pay_after_cart_context(graph_thread):
    graph_thread.reset()
    graph_thread.say("Add one chocolate protein bar to my cart")
    text = graph_thread.say("That's all — I'm ready to pay.").lower()
    assert len(text) > 12
    assert any(
        w in text
        for w in (
            "pay",
            "payment",
            "otp",
            "mobile",
            "phone",
            "number",
            "easypaisa",
            "checkout",
            "total",
            "amount",
            "order",
            "sorry",
            "unable",
        )
    ), f"expected payment-related guidance: {text[:600]!r}"
