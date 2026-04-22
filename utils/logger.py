"""Structured logging utility for the agent system."""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def _minimal_test_logs() -> bool:
    """Short console logs (no full prompts); set ``AGENT_TEST_MINIMAL_LOGS=0`` to disable."""
    return os.environ.get("AGENT_TEST_MINIMAL_LOGS", "").lower() in ("1", "true", "yes")


# Set by ``tests/integration/conftest.py`` sessionstart: console shows only warnings/errors;
# turn summaries go to stderr from the test harness (user message, arrows, reply, latency).
_SCENARIO_TRACE_MODE = False


def apply_scenario_trace_logging() -> None:
    """Integration scenario runs: hide agent INFO (no prompt headers, router noise) on stdout."""
    global _SCENARIO_TRACE_MODE
    _SCENARIO_TRACE_MODE = True
    console_handler.setLevel(logging.WARNING)


def _scenario_trace_mode() -> bool:
    return _SCENARIO_TRACE_MODE


# Create logs directory if it doesn't exist
project_root = Path(__file__).resolve().parent.parent
logs_dir = project_root / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure agent logger
agent_logger = logging.getLogger("agent")
agent_logger.setLevel(logging.INFO)

# Remove existing handlers to avoid duplicates
agent_logger.handlers.clear()

# Console handler with colored output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# File handler
log_file = logs_dir / "agent.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Formatter
class AgentFormatter(logging.Formatter):
    """Custom formatter for agent logs."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def format(self, record):
        # Add color for console
        if hasattr(record, "color") and record.color:
            color = self.COLORS.get(record.levelname, "")
            reset = self.COLORS["RESET"]
            record.levelname = f"{color}{record.levelname}{reset}"

        # Format message
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{record.name}] {record.levelname}: {record.getMessage()}"


console_formatter = AgentFormatter()
file_formatter = logging.Formatter(
    "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)


class _ConsoleSkipHeavyPromptsFilter(logging.Filter):
    """Last-resort: keep giant prompt/history blobs off the console when running minimal mode."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not _minimal_test_logs():
            return True
        msg = record.getMessage()
        if "Complete Prompt:" in msg:
            return False
        if "MESSAGES LOG:" in msg and len(msg) > 300:
            return False
        if msg.startswith("CONVERSATION HISTORY:") and len(msg) > 400:
            return False
        return True


console_handler.addFilter(_ConsoleSkipHeavyPromptsFilter())

agent_logger.addHandler(console_handler)
agent_logger.addHandler(file_handler)

# Prevent propagation to root logger
agent_logger.propagate = False


def log_agent_flow(agent_name: str, action: str, details: dict = None):
    """Log agent flow with structured information."""
    details = details or {}
    message = f"🤖 [{agent_name}] {action}"
    if details:
        details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        message += f" | {details_str}"
    agent_logger.info(message, extra={"color": True})


def log_llm_call(provider: str, model: str, prompt_type: str, response_time: float = None):
    """Log LLM API calls."""
    message = f"🧠 LLM Call | Provider={provider} | Model={model} | Type={prompt_type}"
    if response_time:
        message += f" | Time={response_time:.2f}s"
    agent_logger.info(message, extra={"color": True})


def log_tool_call(tool_name: str, params: dict = None, result: str = None):
    """Log tool usage."""
    message = f"🔧 Tool Call | {tool_name}"
    if params:
        params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        message += f" | Params: {params_str}"
    if result:
        result_preview = result[:100] + "..." if len(result) > 100 else result
        message += f" | Result: {result_preview}"
    agent_logger.info(message, extra={"color": True})


def log_intent_classification(intent: str, confidence: str = None):
    """Log intent classification."""
    message = f"🎯 Intent Classification | Intent={intent}"
    if confidence:
        message += f" | Confidence={confidence}"
    agent_logger.info(message, extra={"color": True})


def log_error(error: Exception, context: str = None):
    """Log errors with context."""
    message = "❌ Error"
    if context:
        message += f" | Context={context}"
    message += f" | {type(error).__name__}: {str(error)}"
    agent_logger.error(message, extra={"color": True}, exc_info=True)


def log_prompt(agent_name: str, prompt: str, context: dict = None):
    """Log the prompt being used by an agent.

    With ``AGENT_TEST_MINIMAL_LOGS=1`` (scenario tests), only a one-line header is printed
    to the console; the full prompt is written at DEBUG to ``logs/agent.log`` for post-mortems.
    Set ``AGENT_LOG_FULL_PROMPTS=1`` to always print full prompts to the console.

    In scenario trace mode (integration scenario session), nothing from prompts is emitted at
    INFO or above — only DEBUG to the log file.
    """
    context = context or {}
    message = f"📝 [{agent_name}] Prompt"
    if context:
        context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
        message += f" | {context_str}"

    full_block = f"Complete Prompt:\n{'=' * 80}\n{prompt}\n{'=' * 80}"

    if os.environ.get("AGENT_LOG_FULL_PROMPTS", "").lower() in ("1", "true", "yes"):
        agent_logger.info(message, extra={"color": True})
        agent_logger.info(f"   {full_block}", extra={"color": False})
        return

    if _scenario_trace_mode():
        agent_logger.debug(f"{message}\n{full_block}")
        return

    agent_logger.info(message, extra={"color": True})

    if _minimal_test_logs():
        agent_logger.debug(full_block)
    else:
        agent_logger.info(f"   {full_block}", extra={"color": False})


def log_graph_flow(node_name: str, action: str, details: dict = None):
    """Log graph execution flow."""
    details = details or {}
    message = f"🔄 [GRAPH] {node_name} | {action}"
    if details:
        details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
        message += f" | {details_str}"
    agent_logger.info(message, extra={"color": True})


def log_conversation_history(conversation_history: str):
    """Log conversation history."""
    if _minimal_test_logs():
        agent_logger.debug(f"CONVERSATION HISTORY:\n{conversation_history}")
        return
    agent_logger.info(f"CONVERSATION HISTORY:\n{conversation_history}", extra={"color": False})


def _last_user_snippet(messages) -> str:
    for m in reversed(messages or []):
        t = getattr(m, "type", None)
        if t == "human" or type(m).__name__ == "HumanMessage":
            c = getattr(m, "content", "")
            if isinstance(c, str) and c.strip():
                one = c.replace("\n", " ").strip()
                return one[:200] + ("…" if len(one) > 200 else "")
    return "(no user text)"


def log_messages(messages):
    """Log messages (full list, or compact line when ``AGENT_TEST_MINIMAL_LOGS``)."""
    if _scenario_trace_mode():
        return
    if _minimal_test_logs():
        n = len(messages or [])
        agent_logger.info(
            f"ROUTER_INPUT | message_count={n} | last_user={_last_user_snippet(messages)!r}",
            extra={"color": True},
        )
        return
    agent_logger.info(f"MESSAGES LOG:\n{messages}", extra={"color": False})
