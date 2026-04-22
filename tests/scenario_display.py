"""Shared terminal UI for scenario runs (pytest integration + YAML runner)."""
from __future__ import annotations

import sys
from typing import Any


def emit_scenario_turn_box(user_text: str, result: dict[str, Any], elapsed: float, out_text: str) -> None:
    """Print one turn summary to stderr (no prompts or agent logs in this block)."""
    intent = result.get("intent")
    agent = result.get("active_agent")
    dest = agent if agent else "__end__"
    dim, bold, reset = "\033[2m", "\033[1m", "\033[0m"
    cyan = "\033[36m"
    reply = (out_text or "").rstrip("\n") or "(empty)"
    router_line = f"intent={intent!r}  →  {dest!r}"
    w = 64
    top = dim + "┌" + "─" * w + "┐" + reset
    mid = dim + "├" + "─" * w + "┤" + reset
    bot = dim + "└" + "─" * w + "┘" + reset

    def flush_block(title_plain: str, body: str) -> None:
        sys.stderr.write(f"│ {cyan}{bold}{title_plain}{reset}\n")
        for ln in body.split("\n") or [""]:
            sys.stderr.write(f"│   {ln}\n")

    sys.stderr.write(f"\n{top}\n")
    flush_block("USER INPUT", user_text.rstrip("\n"))
    sys.stderr.write(f"{mid}\n")
    flush_block("ROUTER", router_line)
    sys.stderr.write(f"{mid}\n")
    flush_block("TIME", f"{elapsed:.2f}s")
    sys.stderr.write(f"{mid}\n")
    flush_block("AGENT OUTPUT", reply)
    sys.stderr.write(f"{bot}\n\n")
