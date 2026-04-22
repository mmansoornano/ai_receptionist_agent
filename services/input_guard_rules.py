"""Load and apply deterministic input guard rules (config/guard_rules.yaml)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_RULES_PATH = _CONFIG_DIR / "guard_rules.yaml"
_cache: dict[str, Any] | None = None
_compiled_regex: list[re.Pattern[str]] = []


def _load_raw() -> dict[str, Any]:
    global _cache
    if _cache is not None:
        return _cache
    if not _RULES_PATH.is_file():
        raise FileNotFoundError(f"Guard rules not found: {_RULES_PATH}")
    with open(_RULES_PATH, encoding="utf-8") as f:
        _cache = yaml.safe_load(f) or {}
    return _cache


def _compile_regexes() -> None:
    global _compiled_regex
    raw = _load_raw()
    patterns = raw.get("regex_blocklist") or []
    _compiled_regex = []
    for p in patterns:
        if not (isinstance(p, str) and p.strip()):
            continue
        try:
            _compiled_regex.append(re.compile(p))
        except re.error:
            continue


def reload_guard_rules() -> None:
    """Tests or hot-reload: clear cache and recompile."""
    global _cache, _compiled_regex
    _cache = None
    _compiled_regex = []
    _compile_regexes()


def _template_key_for_message(u: str) -> str:
    """Pick refusal template id for a blocked message (substring already matched)."""
    u = u.lower()
    if any(
        n in u
        for n in (
            "prescription",
            "adderall",
            "treating physician",
            "write a prescription",
        )
    ):
        return "medical"
    if any(
        n in u
        for n in (
            "pnr",
            "boarding pass",
            "book me a flight",
            "travel agent",
            "flight to",
            "business-class",
            "business class",
            "tickets to",
        )
    ):
        return "travel"
    if "forget the store" in u:
        return "store_attack"
    if any(
        n in u
        for n in (
            "sushi",
            "spicy tuna",
            "doordash",
            "uber eats",
            "pepperoni pizza",
        )
    ) or ("pizz" in u and "pepperoni" in u):
        return "food_service"
    if any(
        n in u
        for n in (
            "print the exact",
            "system prompt",
            "reveal your",
            "ignore all previous",
            "jailbreak",
            "api key",
            "hidden system",
        )
    ):
        return "meta"
    if any(n in u for n in ("you are now", "you're now", "dan ", "do anything now", "system override")):
        return "meta"
    return "default"


def evaluate_deterministic(
    user_text: str,
) -> tuple[Literal["allow", "refuse", "unknown"], str]:
    """
    Fast path: allow (simple greeting), refuse (blocklist + regex), or unknown (need LLM).

    Returns (outcome, customer_visible_reply) — reply is non-empty only when outcome is refuse.
    """
    _compile_regexes()
    raw = _load_raw()
    u = (user_text or "").strip()
    u_lower = u.lower()

    allow = raw.get("simple_greeting_allowlist") or []
    if u_lower in {str(x).lower() for x in allow} or (
        u_lower.endswith("!")
        and u_lower[:-1].strip() in {str(x).lower().rstrip("!") for x in allow if " " not in str(x)}
    ):
        if len(u) > 56 or "http://" in u_lower or "https://" in u_lower:
            pass
        else:
            return "allow", ""

    for sub in raw.get("substring_blocklist") or []:
        if not isinstance(sub, str):
            continue
        if sub.lower() in u_lower:
            templates = raw.get("refusal_templates") or {}
            key = _template_key_for_message(u_lower)
            msg = (templates.get(key) or templates.get("default") or "").strip()
            if not msg:
                msg = "I can only help with our protein bar store. How can I help you today?"
            return "refuse", msg

    for rx in _compiled_regex:
        if rx.search(u):
            templates = raw.get("refusal_templates") or {}
            key = _template_key_for_message(u_lower)
            msg = (templates.get(key) or templates.get("default") or "").strip()
            if not msg:
                msg = "I can only help with our protein bar store. How can I help you today?"
            return "refuse", msg

    return "unknown", ""
