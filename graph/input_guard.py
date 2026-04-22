"""Pre-router input guard: deterministic rules + optional small LLM policy (structured JSON)."""
from __future__ import annotations

import json
import re
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Command
from pydantic import BaseModel, Field

from config import (
    AGENT_SKIP_GUARD_LLM,
    GUARD_OLLAMA_MODEL,
    GUARD_OPENAI_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
)
from graph.state import ReceptionistState
from services.input_guard_rules import evaluate_deterministic, reload_guard_rules
from services.prompt_loader import get_prompt
from utils.logger import log_agent_flow, log_graph_flow, log_llm_call


class GuardLLMVerdict(BaseModel):
    verdict: Literal["allow", "refuse"]
    category: str = Field(default="", max_length=120)
    customer_reply: str = Field(default="", max_length=800)


_FAIL_CLOSED_REPLY = (
    "I can only help with our protein bar store. If you have a question about products, cart, or delivery, I’m here."
)

def _extract_json_object(text: str) -> dict[str, Any]:
    t = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.DOTALL)
    if fence:
        t = fence.group(1).strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no json object in guard response")
    return json.loads(t[start : end + 1])


def _get_guard_llm_invoke():
    """LLM for policy layer only; uses GUARD_* model names, temp=0."""
    p = (LLM_PROVIDER or "ollama").lower().strip()
    if p == "openai":
        key = (OPENAI_API_KEY or "").strip()
        if not key:
            raise RuntimeError("OPENAI_API_KEY required for input guard with LLM_PROVIDER=openai")
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=GUARD_OPENAI_MODEL, temperature=0.0, api_key=key)
    from langchain_ollama import ChatOllama

    return ChatOllama(
        base_url=(OLLAMA_BASE_URL or "http://127.0.0.1:11434").rstrip("/"),
        model=GUARD_OLLAMA_MODEL,
        temperature=0.0,
    )


def _llm_policy_check(user_text: str) -> GuardLLMVerdict:
    system = get_prompt("input_guard")
    human = HumanMessage(
        content="Latest user message (judge this only, JSON reply):\n\n" + (user_text or "")
    )
    llm = _get_guard_llm_invoke()

    structured = getattr(llm, "with_structured_output", None)
    if callable(structured):
        try:
            bound = llm.with_structured_output(GuardLLMVerdict)  # type: ignore[union-attr]
            out = bound.invoke([SystemMessage(content=system), human])
            if isinstance(out, dict):
                return GuardLLMVerdict.model_validate(out)
            return out
        except (TypeError, ValueError, AttributeError):
            pass
        try:
            bound = llm.with_structured_output(GuardLLMVerdict, method="json_schema")  # type: ignore[call-arg]
            out = bound.invoke([SystemMessage(content=system), human])
            if isinstance(out, dict):
                return GuardLLMVerdict.model_validate(out)
            return out
        except (TypeError, ValueError, AttributeError, Exception):
            pass

    resp = llm.invoke([SystemMessage(content=system + "\n\nRespond with JSON only."), human])
    raw = resp.content if isinstance(resp.content, str) else str(resp.content)
    data = _extract_json_object(raw)
    return GuardLLMVerdict.model_validate(data)


def input_guard_node(state: ReceptionistState) -> Command:
    """Block disallowed input before the router. Allow → router. Refuse → one assistant message and end."""
    log_graph_flow("input_guard", "Entering Node")
    messages = state.get("messages", [])
    if not messages:
        return Command(update={}, goto="router")

    last = messages[-1]
    if not isinstance(last, HumanMessage):
        return Command(update={}, goto="router")

    user_text = last.content if isinstance(last.content, str) else str(last.content)
    user_text = (user_text or "").strip()

    outcome, refusal_msg = evaluate_deterministic(user_text)
    if outcome == "allow":
        log_agent_flow("INPUT_GUARD", "allow (deterministic allowlist)", {})
        return Command(update={}, goto="router")
    if outcome == "refuse":
        log_agent_flow("INPUT_GUARD", "refuse (deterministic rule)", {"preview": user_text[:100]})
        return Command(
            update={
                "messages": [AIMessage(content=refusal_msg)],
                "intent": "guardrail_refuse",
                "conversation_context": state.get("conversation_context"),
                "active_agent": None,
            },
            goto="__end__",
        )

    if AGENT_SKIP_GUARD_LLM:
        log_agent_flow("INPUT_GUARD", "unknown → allow (AGENT_SKIP_GUARD_LLM)", {})
        return Command(update={}, goto="router")

    log_agent_flow("INPUT_GUARD", "unknown → LLM policy", {"preview": user_text[:100]})
    p = (LLM_PROVIDER or "ollama").lower().strip()
    mname = GUARD_OLLAMA_MODEL if p == "ollama" else GUARD_OPENAI_MODEL
    log_llm_call(p, mname, "Input Guard")
    try:
        v = _llm_policy_check(user_text)
    except Exception as exc:
        log_agent_flow("INPUT_GUARD", "LLM policy failed, fail-closed", {"err": str(exc)[:200]})
        return Command(
            update={
                "messages": [AIMessage(content=_FAIL_CLOSED_REPLY)],
                "intent": "guardrail_refuse",
                "conversation_context": state.get("conversation_context"),
                "active_agent": None,
            },
            goto="__end__",
        )
    if v.verdict == "refuse":
        reply = (v.customer_reply or _FAIL_CLOSED_REPLY).strip() or _FAIL_CLOSED_REPLY
        return Command(
            update={
                "messages": [AIMessage(content=reply)],
                "intent": "guardrail_refuse",
                "conversation_context": state.get("conversation_context"),
                "active_agent": None,
            },
            goto="__end__",
        )
    return Command(update={}, goto="router")


# For tests: reload rules when needed
__all__ = ["input_guard_node", "reload_guard_rules"]
