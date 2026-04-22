---
layout: default
title: LangGraph
---

## Graph entry (`graph/main.py`)

- **START → `router`** — only static edge; all other routing uses **`Command`** return values.
- **Nodes:** `router`, `qa_agent`, `ordering_agent`, `payment_agent`, `cancellation_agent`, `tools`.

## `call_tools` (shared tool executor)

After an agent returns an **AIMessage** with **`tool_calls`**, the graph jumps to **`tools`**. `call_tools`:

1. Reads **`intent`** and the last message’s **`tool_calls`**.
2. Dispatches to **`ordering_tool_node`**, **`payment_tool_node`**, **`cancellation_tool_node`**, or **`qa_tool_node`** based on intent.
3. Preserves **`active_agent`** and **`intent`** on the way out (tool nodes mainly append **`ToolMessage`**s).
4. Returns **`Command`** with **`goto`** = previous **`active_agent`** so the specialist can continue with tool results—or falls back to an agent map from intent if **`active_agent`** is missing.

## State (`graph/state.py`)

`ReceptionistState` includes at least:

- **`messages`** — reduced with **`sliding_window_messages`** (keeps recent history, tries to keep tool-call / tool-result pairs).
- **`intent`**, **`active_agent`**, **`conversation_context`**, **`customer_id`**, **`conversation_id`**, **`channel`**, **`language`**, plus optional structured slots used by agents.

## QA tools (`graph/qa_agent.py`)

`QA_TOOLS` combines: **`search_knowledge_base`**, **`get_customer`**, **`list_upcoming_events`**, **`PRODUCT_TOOLS`**, **`CALCULATOR_TOOLS`**. The QA node trims history for token limits but **keeps `ToolMessage`s** next to assistant tool calls (required for OpenAI).

## Ordering / payment / cancellation

Each agent follows the same pattern: load prompt from YAML, build messages, **`invoke_with_retry`** on the tool-bound LLM, then **`create_message_update_command`** to append the assistant message and route to **`tools`** or **`__end__`**.

See [Architecture]({{ site.canonical_docs_url }}/architecture.html) and the source under `graph/`.
