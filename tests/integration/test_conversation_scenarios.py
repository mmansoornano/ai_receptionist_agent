"""Greetings, small talk, prices, location, FAQ-style questions."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.conversation]


@pytest.mark.parametrize(
    "prompt",
    [
        "Hi",
        "Hello!",
        "Hey there",
        "Good morning",
        "Thanks for helping me today",
    ],
)
def test_greeting_gets_friendly_reply(reply_text, prompt: str):
    text = reply_text(prompt)
    assert len(text) >= 8, "expected a real greeting, not an empty reply"


@pytest.mark.parametrize(
    "prompt,expect_any",
    [
        ("What are your prices for protein bars?", ("price", "cost", "pkr", "rs", "rupee", "protein", "$")),
        ("What are the prices?", ("price", "cost", "pkr", "rs", "rupee", "bar", "product", "protein")),
        ("Where are you located?", ("address", "location", "city", "pakistan", "karachi", "lahore", "store")),
        ("What is your location?", ("address", "location", "city", "pakistan", "karachi", "lahore", "store", "based")),
        ("What flavors do you sell?", ("flavor", "chocolate", "vanilla", "bar", "product", "cookie", "protein")),
        ("Do you have gluten-free options?", ("gluten", "free", "yes", "no", "product", "option", "bar")),
        ("What are your shipping options?", ("ship", "deliver", "order", "pakistan", "city", "fee", "cost", "day")),
        (
            "What is your return policy?",
            (
                "return",
                "refund",
                "policy",
                "order",
                "baking",
                "cancel",
                "after",
                "cannot",
                "contact",
                "customer",
                "phone",
                "sorry",
            ),
        ),
        ("Do you sell gift boxes?", ("gift", "box", "bar", "price", "product", "yes", "pk", "pkr")),
        ("What payment methods do you accept?", ("pay", "payment", "cash", "card", "mobile", "easypaisa", "order")),
    ],
)
def test_faq_style_questions(reply_text, prompt: str, expect_any: tuple[str, ...]):
    text = reply_text(prompt).lower()
    assert any(k in text for k in expect_any), (
        f"reply should touch expected topic keywords; got: {text[:400]!r}"
    )


def test_follow_up_stays_coherent(graph_thread):
    graph_thread.reset()
    t1 = graph_thread.say("What sizes do your bars come in?").lower()
    assert len(t1) > 15
    t2 = graph_thread.say("And the price for the smallest pack?").lower()
    assert len(t2) > 10
    assert any(w in t2 for w in ("price", "cost", "pack", "bar", "pkr", "rs", "small", "size"))


def test_multi_turn_flavor_then_compare(graph_thread):
    graph_thread.reset()
    graph_thread.say("Do you have peanut butter flavors?")
    t2 = graph_thread.say("How does the price compare to the almond bar?").lower()
    assert len(t2) > 10
    assert any(w in t2 for w in ("price", "almond", "peanut", "bar", "pkr", "rs", "450", "cost"))


def test_multi_turn_catalog_then_detail(graph_thread):
    graph_thread.reset()
    graph_thread.say("What products do you sell?")
    t2 = graph_thread.say("Tell me more about your granola bars.").lower()
    assert len(t2) > 12
    assert any(w in t2 for w in ("granola", "bar", "chocolate", "price", "pk", "product", "flavor"))


def test_multi_turn_hours_then_delivery(graph_thread):
    graph_thread.reset()
    graph_thread.say("What are your business hours?")
    t2 = graph_thread.say("And how long does delivery usually take?").lower()
    assert len(t2) > 10
    assert any(w in t2 for w in ("deliver", "ship", "day", "order", "pakistan", "city", "hour", "time"))


def test_multi_turn_allergy_then_option(graph_thread):
    graph_thread.reset()
    graph_thread.say("I have a nut allergy — what can I order?")
    t2 = graph_thread.say("Do any of your bars contain peanuts?").lower()
    assert len(t2) > 10
    assert any(w in t2 for w in ("peanut", "nut", "allerg", "bar", "ingredient", "product", "sorry"))
