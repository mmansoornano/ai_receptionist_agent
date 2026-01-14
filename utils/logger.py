"""Structured logging utility for the agent system."""
import logging
import sys
from pathlib import Path
from datetime import datetime
import json

# Create logs directory if it doesn't exist
project_root = Path(__file__).parent.parent.parent
logs_dir = project_root / 'logs'
logs_dir.mkdir(exist_ok=True)

# Configure agent logger
agent_logger = logging.getLogger('agent')
agent_logger.setLevel(logging.INFO)

# Remove existing handlers to avoid duplicates
agent_logger.handlers.clear()

# Console handler with colored output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# File handler
log_file = logs_dir / 'agent.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Formatter
class AgentFormatter(logging.Formatter):
    """Custom formatter for agent logs."""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # Add color for console
        if hasattr(record, 'color') and record.color:
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
        
        # Format message
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        return f"[{timestamp}] [{record.name}] {record.levelname}: {record.getMessage()}"

console_formatter = AgentFormatter()
file_formatter = logging.Formatter(
    '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

console_handler.setFormatter(console_formatter)
file_handler.setFormatter(file_formatter)

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
    agent_logger.info(message, extra={'color': True})


def log_llm_call(provider: str, model: str, prompt_type: str, response_time: float = None):
    """Log LLM API calls."""
    message = f"🧠 LLM Call | Provider={provider} | Model={model} | Type={prompt_type}"
    if response_time:
        message += f" | Time={response_time:.2f}s"
    agent_logger.info(message, extra={'color': True})


def log_tool_call(tool_name: str, params: dict = None, result: str = None):
    """Log tool usage."""
    message = f"🔧 Tool Call | {tool_name}"
    if params:
        params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        message += f" | Params: {params_str}"
    if result:
        result_preview = result[:100] + "..." if len(result) > 100 else result
        message += f" | Result: {result_preview}"
    agent_logger.info(message, extra={'color': True})


def log_intent_classification(intent: str, confidence: str = None):
    """Log intent classification."""
    message = f"🎯 Intent Classification | Intent={intent}"
    if confidence:
        message += f" | Confidence={confidence}"
    agent_logger.info(message, extra={'color': True})


def log_error(error: Exception, context: str = None):
    """Log errors with context."""
    message = f"❌ Error"
    if context:
        message += f" | Context={context}"
    message += f" | {type(error).__name__}: {str(error)}"
    agent_logger.error(message, extra={'color': True}, exc_info=True)
