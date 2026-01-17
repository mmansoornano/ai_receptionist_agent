"""Utilities for managing conversation stages and flow tracking."""
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from graph.state import ReceptionistState
from utils.logger import agent_logger, log_agent_flow


# Define stage types for each agent
ORDERING_STAGES = Literal[
    "general",
    "ordering_handover",
    "ordering_started",
    "item_added",
    "cart_updated",
    "date_selected",
    "payment_ready"
]

PAYMENT_STAGES = Literal[
    "general",
    "payment_handover",
    "payment_started",
    "cart_viewed",
    "payment_link_provided",
    "payment_processing",
    "payment_completed",
    "order_placed"
]

CANCELLATION_STAGES = Literal[
    "general",
    "cancellation_handover",
    "cancellation_started",
    "cancellation_confirmed",
    "cancellation_completed"
]

QA_STAGES = Literal[
    "general",
    "product_inquiry",
    "general_qa",
    "faq_inquiry"
]


def update_stage(
    state: ReceptionistState,
    new_stage: str,
    agent_name: str = "unknown",
    reason: str = ""
) -> Dict[str, Any]:
    """Update conversation stage in state.
    
    Args:
        state: Current state
        new_stage: New stage to set
        agent_name: Name of agent updating stage
        reason: Reason for stage change
    
    Returns:
        Dictionary with stage update for Command
    """
    current_stage = state.get("current_stage", "general")
    
    log_agent_flow(agent_name.upper(), "Stage Update", {
        "from_stage": current_stage,
        "to_stage": new_stage,
        "reason": reason
    })
    
    return {
        "current_stage": new_stage,
        "last_stage": current_stage
    }


def get_stage_context(
    state: ReceptionistState,
    agent_name: str = "unknown"
) -> Dict[str, Any]:
    """Get context information based on current stage.
    
    Args:
        state: Current state
        agent_name: Name of agent requesting context
    
    Returns:
        Dictionary with stage-specific context
    """
    current_stage = state.get("current_stage", "general")
    intent = state.get("intent", "general_qa")
    active_agent = state.get("active_agent")
    cart_data = state.get("cart_data", {})
    order_data = state.get("order_data", {})
    payment_data = state.get("payment_data", {})
    
    context = {
        "current_stage": current_stage,
        "intent": intent,
        "active_agent": active_agent,
        "has_cart_items": bool(cart_data.get("items", [])),
        "cart_item_count": len(cart_data.get("items", [])) if cart_data.get("items") else 0,
        "has_order": bool(order_data),
        "has_payment": bool(payment_data),
        "payment_status": payment_data.get("status") if payment_data else None
    }
    
    return context


def should_transition_to_stage(
    current_stage: str,
    target_stage: str,
    required_conditions: Dict[str, Any],
    state: ReceptionistState
) -> bool:
    """Check if stage transition is allowed based on conditions.
    
    Args:
        current_stage: Current conversation stage
        target_stage: Target stage to transition to
        required_conditions: Dictionary of conditions that must be met
        state: Current state
    
    Returns:
        True if transition is allowed, False otherwise
    """
    # Check each required condition
    for key, expected_value in required_conditions.items():
        if key == "has_cart_items":
            cart_data = state.get("cart_data", {})
            has_items = bool(cart_data.get("items", []))
            if has_items != expected_value:
                return False
        elif key == "intent":
            current_intent = state.get("intent")
            if current_intent != expected_value:
                return False
        elif key == "active_agent":
            current_agent = state.get("active_agent")
            if current_agent != expected_value:
                return False
        # Add more conditions as needed
    
    return True


def create_handoff_context(
    from_agent: str,
    to_agent: str,
    reasoning: Dict[str, Any],
    timestamp: Optional[str] = None
) -> Dict[str, Any]:
    """Create handoff context for agent transitions.
    
    Args:
        from_agent: Name of agent transitioning from
        to_agent: Name of agent transitioning to
        reasoning: Dictionary with handoff reasoning (confidence, reason, etc.)
        timestamp: Optional timestamp (defaults to current time)
    
    Returns:
        Dictionary with handoff context
    """
    return {
        "from_agent": from_agent,
        "to_agent": to_agent,
        "reasoning": reasoning,
        "timestamp": timestamp or datetime.now().isoformat(),
        "confidence": reasoning.get("confidence", 0.0),
        "requires_specialized_agent": reasoning.get("requires_specialized_agent", True),
        "task_status": reasoning.get("task_status", "in_progress")
    }
