"""Utilities for processing LLM responses and extracting structured data."""
import json
import re
from typing import Dict, Any, Optional, Tuple
from langchain_core.messages import AIMessage
from utils.logger import agent_logger, log_agent_flow


def process_llm_response(
    response: AIMessage,
    agent_name: str = "unknown"
) -> Dict[str, Any]:
    """Process LLM response to extract JSON content and tool calls.
    
    This function extracts structured JSON from LLM responses, which may be:
    - Direct JSON in content
    - JSON wrapped in markdown code blocks
    - Tool calls from the response
    
    Args:
        response: AIMessage from LLM
        agent_name: Name of the agent (for logging)
    
    Returns:
        Dictionary with keys:
        - "raw_response": Original AIMessage
        - "content": Text content of response
        - "json_content": Extracted JSON as dict (if found)
        - "tool_call": First tool call dict (if found)
        - "tool_calls": List of all tool calls (if found)
        - "has_json": Whether JSON was found
        - "has_tool_calls": Whether tool calls were found
    """
    result = {
        "raw_response": response,
        "content": response.content if hasattr(response, 'content') else "",
        "json_content": None,
        "tool_call": None,
        "tool_calls": None,
        "has_json": False,
        "has_tool_calls": False
    }
    
    # Check for tool calls
    if hasattr(response, 'tool_calls') and response.tool_calls:
        result["has_tool_calls"] = True
        result["tool_calls"] = response.tool_calls
        result["tool_call"] = response.tool_calls[0] if response.tool_calls else None
        
        log_agent_flow(agent_name.upper(), "Tool Calls Detected", {
            "tool_count": len(response.tool_calls),
            "tools": [tc.get('name', 'unknown') if isinstance(tc, dict) else getattr(tc, 'name', 'unknown') for tc in response.tool_calls]
        })
    
    # Try to extract JSON from content
    content = result["content"]
    if not content:
        return result
    
    # Try to find JSON in content (might be in markdown code blocks or direct JSON)
    json_match = None
    
    # Pattern 1: JSON in markdown code blocks (```json ... ``` or ``` ... ```)
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    json_match = re.search(json_block_pattern, content, re.DOTALL)
    
    if not json_match:
        # Pattern 2: Direct JSON object (starts with { and ends with })
        json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_match = re.search(json_object_pattern, content, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1) if json_match.groups() else json_match.group(0)
        
        try:
            # Try to repair malformed JSON (handles trailing commas, etc.)
            try:
                from json_repair import repair_json
                repaired_json = repair_json(json_str)
                result["json_content"] = json.loads(repaired_json)
            except ImportError:
                # json_repair not available, try direct parsing
                result["json_content"] = json.loads(json_str)
            
            result["has_json"] = True
            
            log_agent_flow(agent_name.upper(), "JSON Content Extracted", {
                "json_keys": list(result["json_content"].keys()) if isinstance(result["json_content"], dict) else []
            })
            
        except json.JSONDecodeError as e:
            agent_logger.warning(f"⚠️ Failed to parse JSON from {agent_name} response: {e}")
            log_agent_flow(agent_name.upper(), "JSON Parse Failed", {"error": str(e)})
    
    return result


def extract_intent_from_response(
    processed_response: Dict[str, Any],
    default_intent: str = "general_qa"
) -> str:
    """Extract intent from processed LLM response.
    
    Args:
        processed_response: Result from process_llm_response()
        default_intent: Default intent if not found
    
    Returns:
        Extracted intent string
    """
    # Try to get intent from JSON content first
    if processed_response.get("has_json") and processed_response.get("json_content"):
        json_content = processed_response["json_content"]
        if isinstance(json_content, dict):
            intent = json_content.get("intent") or json_content.get("response_type")
            if intent:
                return intent
    
    # Try to get intent from tool call name (some tools indicate intent)
    if processed_response.get("has_tool_calls") and processed_response.get("tool_call"):
        tool_call = processed_response["tool_call"]
        if isinstance(tool_call, dict):
            tool_name = tool_call.get("name", "")
            # Map tool names to intents if needed
            tool_to_intent = {
                "list_all_products": "product_inquiry",
                "add_item_to_cart": "ordering",
                "view_cart": "ordering",
                "process_payment": "payment",
                "cancel_order": "cancellation"
            }
            if tool_name in tool_to_intent:
                return tool_to_intent[tool_name]
    
    return default_intent


def extract_handoff_reasoning_from_response(
    processed_response: Dict[str, Any]
) -> Dict[str, Any]:
    """Extract handoff reasoning from processed LLM response.
    
    Args:
        processed_response: Result from process_llm_response()
    
    Returns:
        Dictionary with handoff reasoning (confidence, should_return, etc.)
    """
    reasoning = {}
    
    if processed_response.get("has_json") and processed_response.get("json_content"):
        json_content = processed_response["json_content"]
        if isinstance(json_content, dict):
            # Look for handoff_reasoning, handoff_context, or similar keys
            reasoning = (
                json_content.get("handoff_reasoning") or
                json_content.get("handoff_context") or
                json_content.get("routing_reasoning") or
                {}
            )
            if not isinstance(reasoning, dict):
                reasoning = {}
    
    # Ensure required fields with defaults
    reasoning.setdefault("confidence", 0.0)
    reasoning.setdefault("should_return_to_primary", False)
    reasoning.setdefault("requires_specialized_agent", True)
    reasoning.setdefault("task_status", "in_progress")
    reasoning.setdefault("reason", "")
    
    return reasoning
