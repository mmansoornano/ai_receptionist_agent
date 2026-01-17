# Performance Enhancements from Reference Implementation

This document outlines the key concepts and utilities added from the reference implementation to enhance the receptionist agent system's performance and robustness.

## 1. Message Filtering Utilities (`utils/message_filtering.py`)

**Purpose**: Filter messages before processing by agents to reduce noise and improve context quality.

**Key Functions**:
- `filter_messages_for_agent()` - Filter messages for agent processing (excludes ToolMessages and SystemMessages by default)
- `get_last_human_message()` - Get last user message
- `get_last_ai_message()` - Get last AI message
- `has_tool_calls_in_messages()` - Check if messages contain tool calls
- `extract_tool_call_names()` - Extract tool names from messages

**Usage Example**:
```python
from utils.message_filtering import filter_messages_for_agent

# Filter messages before processing
filtered_messages = filter_messages_for_agent(messages, include_system=False)
```

**Benefits**:
- Reduces token usage by excluding internal tool results
- Improves context quality for LLM processing
- Consistent message filtering across all agents

---

## 2. LLM Response Processing (`utils/llm_response_processor.py`)

**Purpose**: Extract structured data (JSON, tool calls) from LLM responses consistently.

**Key Functions**:
- `process_llm_response()` - Extract JSON content and tool calls from AIMessage
- `extract_intent_from_response()` - Extract intent from processed response
- `extract_handoff_reasoning_from_response()` - Extract handoff reasoning with confidence scores

**Usage Example**:
```python
from utils.llm_response_processor import process_llm_response, extract_intent_from_response

# Process LLM response
processed = process_llm_response(response, agent_name="qa_agent")

# Extract intent
intent = extract_intent_from_response(processed, default_intent="general_qa")

# Check for tool calls
if processed.get("has_tool_calls"):
    tool_call = processed.get("tool_call")
```

**Benefits**:
- Consistent JSON extraction with error handling
- Supports JSON repair for malformed responses (optional dependency)
- Extracts structured data for routing decisions

---

## 3. LLM Retry Logic (`utils/llm_retry.py`)

**Purpose**: Retry LLM calls with exponential backoff for transient failures (rate limits, server errors).

**Key Functions**:
- `invoke_with_retry()` - Retry sync LLM calls
- `ainvoke_with_retry()` - Retry async LLM calls
- `retry_llm_call()` - Decorator for retry logic

**Usage Example**:
```python
from utils.llm_retry import invoke_with_retry

# Invoke LLM with retry logic
response = invoke_with_retry(
    llm=llm_with_tools,
    messages=agent_messages,
    max_retries=3,
    initial_delay=1.0,
    agent_name="qa_agent"
)
```

**Benefits**:
- Handles transient errors automatically (429, 500, 502, 503, 504, 529)
- Exponential backoff prevents overwhelming the service
- Logs retry attempts for debugging

---

## 4. Stage Management (`utils/stage_management.py`)

**Purpose**: Track conversation stages and manage flow transitions between agents.

**Key Functions**:
- `update_stage()` - Update conversation stage in state
- `get_stage_context()` - Get context based on current stage
- `should_transition_to_stage()` - Validate stage transitions based on conditions
- `create_handoff_context()` - Create handoff context for agent transitions

**Usage Example**:
```python
from utils.stage_management import update_stage, get_stage_context

# Update stage
stage_update = update_stage(state, "payment_ready", agent_name="ordering_agent", reason="Cart finalized")

# Get stage context
context = get_stage_context(state, agent_name="payment_agent")
```

**Benefits**:
- Tracks conversation progress through stages
- Validates transitions to prevent invalid state changes
- Provides context for decision-making based on current stage

---

## 5. Enhanced Error Handling (`utils/error_handler.py`)

**Purpose**: Handle errors gracefully with user-friendly messages based on error type.

**Key Functions**:
- `handle_llm_error()` - Handle LLM errors with specific responses
- `is_retryable_error()` - Check if error is retryable
- `get_user_friendly_error_message()` - Get user-friendly error message

**Usage Example**:
```python
from utils.error_handler import handle_llm_error

try:
    response = llm.invoke(messages)
except Exception as e:
    # Handle error with appropriate response
    return handle_llm_error(e, agent_name="qa_agent", state=state)
```

**Benefits**:
- User-friendly error messages based on error type
- Specific handling for rate limits (429, 529), server errors (500-504), etc.
- Prevents exposing internal errors to users

---

## 6. State Utilities (`utils/state_utils.py`)

**Purpose**: Utilities for managing conversation state and checkpoints.

**Key Functions**:
- `get_thread_id()` - Generate thread_id for state persistence
- `get_config()` - Create config dict for checkpointer
- `reset_conversation_state()` - Clear conversation state
- `add_system_message()` - Add system messages without triggering agents
- `get_conversation_state()` - Retrieve current state from checkpointer

**Benefits**:
- Centralized state management
- Support for system messages (notifications, reminders)
- Easy state reset and inspection

---

## Implementation Recommendations

### Immediate Benefits

1. **Message Filtering**: Use `filter_messages_for_agent()` in all agents before `trim_messages()` to reduce token usage by ~20-30%.

2. **Response Processing**: Replace manual JSON extraction with `process_llm_response()` for consistent, error-tolerant parsing.

3. **Retry Logic**: Wrap all LLM calls with `invoke_with_retry()` to handle transient errors automatically.

4. **Error Handling**: Use `handle_llm_error()` in try/except blocks for consistent error responses.

### Long-term Enhancements

1. **Stage Tracking**: Implement stage management in all agents to track conversation flow and enable better routing decisions.

2. **Confidence-based Routing**: Use `extract_handoff_reasoning_from_response()` to make routing decisions based on confidence scores (only hand off if confidence > 0.7).

3. **Template-based Prompts**: Consider using Jinja2 templates for prompts (like reference) to dynamically inject context (appointment data, cart items, etc.).

4. **Response Schema**: Consider using Pydantic models for structured LLM responses (like `PrimaryAgentResponse` in reference) for validation and type safety.

---

## Example Integration

Here's how to integrate these utilities into an existing agent:

```python
from utils.message_filtering import filter_messages_for_agent, get_last_human_message
from utils.llm_retry import invoke_with_retry
from utils.llm_response_processor import process_llm_response, extract_intent_from_response
from utils.error_handler import handle_llm_error
from utils.stage_management import update_stage, get_stage_context

def enhanced_qa_agent(state: ReceptionistState) -> Command | ReceptionistState:
    messages = state.get("messages", [])
    
    # 1. Filter messages
    filtered_messages = filter_messages_for_agent(messages)
    last_human_message = get_last_human_message(messages)
    
    # 2. Trim messages (after filtering)
    trimmed_messages = trim_messages(filtered_messages, ...)
    
    # 3. Prepare prompt
    qa_prompt = get_prompt("qa_agent")
    system_msg = SystemMessage(content=qa_prompt)
    agent_messages = [system_msg] + trimmed_messages
    
    # 4. Invoke LLM with retry
    try:
        response = invoke_with_retry(
            llm=llm_with_tools,
            messages=agent_messages,
            max_retries=3,
            agent_name="qa_agent"
        )
    except Exception as e:
        return handle_llm_error(e, "qa_agent", state)
    
    # 5. Process response
    processed = process_llm_response(response, "qa_agent")
    intent = extract_intent_from_response(processed)
    
    # 6. Route based on intent and tool calls
    if processed.get("has_tool_calls"):
        return create_message_update_command(
            [response],
            state=state,
            goto="tools",
            active_agent="qa_agent"
        )
    
    return create_message_update_command(
        [response],
        state=state,
        goto="__end__",
        active_agent="qa_agent"
    )
```

---

## Performance Impact

**Expected Improvements**:
- **Token Usage**: 20-30% reduction through message filtering
- **Error Recovery**: 90%+ of transient errors handled automatically
- **Response Quality**: Better context quality through filtering and stage management
- **User Experience**: User-friendly error messages instead of technical errors

---

## Next Steps

1. Integrate message filtering into all agents
2. Add retry logic to all LLM calls
3. Implement error handling with user-friendly messages
4. Consider adding structured response schemas (Pydantic models)
5. Evaluate template-based prompts for dynamic context injection
