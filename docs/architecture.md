---
layout: default
title: Architecture
---

## Role in the system

This service is the **conversational orchestration layer**. It does **not** own the canonical product or order database—that lives in your **Django backend** (separate repo). The agent:

1. Accepts user messages over **`POST /process`**.
2. Merges them into **LangGraph** state (messages, intent, `customer_id`, etc.).
3. Runs **router → specialist agent → [tools]** loops until a reply is produced.
4. Calls your backend through **`BACKEND_API_BASE_URL`** inside tool implementations (`services/*`, `tools/*`).

## Architecture diagram

{% include agent-architecture-figure.html %}

## Technology stack

| Layer | Technology | Testing |
|-------|------------|---------|
| HTTP API | **FastAPI** (`api_server.py`) | Run the app and exercise **OpenAPI** at <code>/docs</code>; health via <code>GET /health</code> and <code>/health/ready</code> |
| Orchestration | **LangGraph** (`graph/main.py`) — `StateGraph`, `Command` for dynamic edges | <code>tests/test_router_unit.py</code>, <code>tests/test_agent_flow.py</code>, <code>tests/integration/</code> (LLM-backed) |
| LLM access | **LangChain** chat models (`services/llm_service.py`) — Ollama or OpenAI | Covered by integration scenarios and router tests (mocked or live per markers) |
| Prompts | **YAML** under `prompts/` (`get_prompt` in `services/prompt_loader.py`) | Indirectly via agent + integration tests; <code>tests/integration/test_prompt_injection.py</code> for abuse-style prompts |
| RAG | **FAISS** + embeddings (`services/rag_service.py`) — used by QA tools | QA paths in integration tests; unit coverage where tools are mocked |
| Persistence | **MemorySaver** checkpointer (swap for Redis/Postgres for multi-instance) | Integration tests use thread ids; multi-instance persistence not covered by default |

## Repository map

| Path | Responsibility | Testing |
|------|----------------|---------|
| `api_server.py` | FastAPI app: CORS, `/process`, `/health`, `/health/ready` | Same stack as <code>main</code> path; smoke with server + HTTP client |
| `main.py` | `process_message` — thread id, reset handling, `receptionist_graph.invoke` | <code>tests/test_agent_flow.py</code>; integration scenarios under <code>tests/integration/</code> |
| `graph/main.py` | Graph definition: nodes `router`, `qa_agent`, `ordering_agent`, `payment_agent`, `cancellation_agent`, `tools` | Graph behavior via router + scenario tests |
| `graph/router.py` | Intent classification (LLM + heuristics), `Command` to agent or `__end__` for greetings | <code>tests/test_router_unit.py</code> |
| `graph/state.py` | `ReceptionistState` + `sliding_window_messages` reducer | Used in conftest fixtures; reducer behavior via graph tests |
| `graph/*_agent.py` | Specialist nodes; bind tools; return `Command` to `tools` or `__end__` | Ordering / payment / cancellation / conversation scenario modules in <code>tests/integration/</code> |
| `tools/` | LangChain tools hitting REST APIs, DB helpers, RAG | <code>tests/test_backend_integration.py</code> (live Django at <code>BACKEND_API_BASE_URL</code>); service unit tests (e.g. cart, payment) |
| `services/` | LLM provider, HTTP clients, RAG, prompts | Mocked in fast unit tests; live LLM in marked integration tests |
| `utils/` | Logging, retries, message filtering, conversation formatting | <code>tests/test_message_utils_unit.py</code>, <code>tests/test_conversation_history_unit.py</code> |
| `tests/` | Unit + integration (`tests/integration` needs LLM) | Run <code>pytest</code> from repo root; see root <strong>README.md</strong> for markers and env |

## Intents (router)

Router maps conversation to one of: **`product_inquiry`**, **`ordering`**, **`payment`**, **`cancellation`**, **`general_qa`**, or handles **`greeting`** inline (short-circuit to `__end__` with an assistant message). Invalid model output falls back to **`general_qa`**.

## Companion repositories

- **Backend**: expose REST + set **`AGENT_API_URL`** to this service.
- **Frontend**: usually only **`VITE_BACKEND_URL`**; browser talks to Django, not directly to the agent.

See [Integration]({{ site.canonical_docs_url }}/integration.html).
