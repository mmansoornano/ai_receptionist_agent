"""Shared helpers for LLM-backed integration tests (no pytest import required)."""
from __future__ import annotations

from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from graph.state import ReceptionistState


def llm_unreachable(exc: BaseException) -> bool:
    """True when failure is likely due to no LLM endpoint (Ollama/OpenAI)."""
    if isinstance(exc, BaseExceptionGroup):
        return any(llm_unreachable(e) for e in exc.exceptions)
    try:
        import httpx

        if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
            return True
    except ImportError:
        pass
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        if "refused" in str(exc).lower() or getattr(exc, "errno", None) == 61:
            return True
    text = str(exc).lower()
    if "connection refused" in text or "connecterror" in text:
        return True
    if exc.__cause__ is not None:
        return llm_unreachable(exc.__cause__)
    return False


def make_receptionist_state(
    user_text: str,
    *,
    conversation_id: str = "test_conv",
    customer_id: str = "test_customer",
) -> ReceptionistState:
    return {
        "messages": [HumanMessage(content=user_text)],
        "intent": None,
        "conversation_context": None,
        "customer_info": None,
        "cart_data": None,
        "order_data": None,
        "payment_data": None,
        "channel": "sms",
        "language": "en",
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "active_agent": None,
    }


def continue_state(prev: dict[str, Any], user_text: str) -> ReceptionistState:
    """Append a user turn to a prior graph result for multi-turn tests."""
    msgs = list(prev.get("messages") or [])
    msgs.append(HumanMessage(content=user_text))
    out = {**prev, "messages": msgs}
    return cast(ReceptionistState, out)


def _stringify_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts).strip()
    return ""


def last_assistant_text(messages: list[BaseMessage] | None) -> str:
    """Latest AIMessage with non-empty user-visible text."""
    if not messages:
        return ""
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            s = _stringify_content(m.content)
            if s:
                return s
    return ""


def all_assistant_text(messages: list[BaseMessage] | None) -> str:
    parts: list[str] = []
    for m in messages or []:
        if isinstance(m, AIMessage):
            c = _stringify_content(m.content)
            if c:
                parts.append(c.lower())
    return "\n".join(parts)


def tool_call_names_in_run(messages: list[BaseMessage] | None) -> set[str]:
    names: set[str] = set()
    for m in messages or []:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls or []:
                if isinstance(tc, dict) and tc.get("name"):
                    names.add(str(tc["name"]))
                elif hasattr(tc, "name"):
                    names.add(str(tc.name))
        if isinstance(m, ToolMessage) and getattr(m, "name", None):
            names.add(str(m.name))
    return names


def build_tool_summary(
    messages: list[BaseMessage] | None,
    *,
    max_len: int = 1600,
) -> str:
    """Short opaque summary of tool calls and tool results (for the LLM judge). Not a full log."""
    if not messages:
        return ""
    lines: list[str] = []
    for m in messages:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls or []:
                if isinstance(tc, dict) and tc.get("name"):
                    lines.append(f"tool_call: {tc.get('name')}")
                elif hasattr(tc, "name"):
                    lines.append(f"tool_call: {getattr(tc, 'name', '?')}")
        if isinstance(m, ToolMessage):
            name = getattr(m, "name", None) or "tool"
            body = _stringify_content(m.content) if hasattr(m, "content") else ""
            snippet = (body or "")[:500].replace("\n", " ").strip()
            lines.append(f"tool_result {name}: {snippet}")
    out = "\n".join(lines).strip()
    if len(out) > max_len:
        return out[: max_len - 3] + "..."
    return out


def assert_no_obvious_wrong_domain_booking(text: str) -> None:
    """Heuristic: assistant should not affirm unrelated travel, dining, or delivery bookings."""
    t = text.lower()
    bad_phrases = (
        "boarding pass",
        "pnr ",
        "pnr:",
        "flight confirmed",
        "ticket is confirmed",
        "your flight",
        "airline reservation confirmed",
        "table for two at",
        "restaurant reservation confirmed",
        "doordash order confirmed",
        "uber eats order confirmed",
        "prescription has been sent",
        "your dosage is",
    )
    for phrase in bad_phrases:
        assert phrase not in t, f"unexpected domain-leak phrase {phrase!r} in reply"
