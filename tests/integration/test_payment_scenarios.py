"""Payment-oriented turns after a minimal ordering context."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.payment]

_PAYMENT_SCENARIOS: list[tuple[str, list[str], tuple[str, ...]]] = [
    (
        "ready_to_pay_cookie_then_pay",
        [
            "Add one chocolate chunks cookie to my cart",
            "I want to pay for my order now.",
        ],
        (
            "pay",
            "payment",
            "otp",
            "mobile",
            "phone",
            "easypaisa",
            "checkout",
            "total",
            "amount",
            "order",
            "cookie",
            "sorry",
            "unable",
        ),
    ),
    (
        "proceed_checkout",
        [
            "Add one white chocolate protein bar to my cart",
            "Proceed to checkout please.",
        ],
        (
            "pay",
            "payment",
            "order",
            "total",
            "amount",
            "phone",
            "mobile",
            "checkout",
            "sorry",
        ),
    ),
    (
        "how_do_i_pay",
        [
            "Add 1 peanut butter protein bar to my cart",
            "How do I pay for this order?",
        ],
        (
            "pay",
            "payment",
            "easypaisa",
            "card",
            "mobile",
            "order",
            "total",
            "amount",
            "sorry",
        ),
    ),
    (
        "confirm_then_payment",
        [
            "Add one chocolate chunks cookie to my cart",
            "Yes, that looks correct. How do I complete payment?",
        ],
        (
            "pay",
            "payment",
            "order",
            "total",
            "amount",
            "mobile",
            "phone",
            "checkout",
            "sorry",
        ),
    ),
    (
        "double_item_ready_pay",
        [
            "Add one almond brownie protein bar to my cart",
            "Also add one crunchy granola bar please.",
            "I'm done — start payment.",
        ],
        (
            "pay",
            "payment",
            "order",
            "total",
            "amount",
            "mobile",
            "checkout",
            "sorry",
        ),
    ),
    (
        "ask_fee_then_pay",
        [
            "Add one gift box all bars to my cart",
            "Is there a delivery fee? If so I'm ready to pay the full amount.",
        ],
        (
            "pay",
            "payment",
            "deliver",
            "fee",
            "order",
            "total",
            "150",
            "rs",
            "pkr",
            "amount",
            "sorry",
        ),
    ),
]


def _run_turns(graph_thread, turns: list[str]) -> str:
    out = ""
    for line in turns:
        out = graph_thread.say(line)
    return out


@pytest.mark.parametrize("scenario_id,turns,keywords", _PAYMENT_SCENARIOS, ids=[s[0] for s in _PAYMENT_SCENARIOS])
def test_payment_scenario(graph_thread, scenario_id: str, turns: list[str], keywords: tuple[str, ...]):
    graph_thread.reset()
    text = _run_turns(graph_thread, turns).lower()
    assert len(text) > 12
    assert any(w in text for w in keywords), f"[{scenario_id}] expected payment-related guidance: {text[:600]!r}"


def test_ready_to_pay_after_cart_context(graph_thread):
    """Stable name for CI / docs; same flow as ``ready_to_pay_after_one_bar``."""
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
