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

## Technology stack

| Layer | Technology |
|-------|------------|
| HTTP API | **FastAPI** (`api_server.py`) |
| Orchestration | **LangGraph** (`graph/main.py`) — `StateGraph`, `Command` for dynamic edges |
| LLM access | **LangChain** chat models (`services/llm_service.py`) — Ollama or OpenAI |
| Prompts | **YAML** under `prompts/` (`get_prompt` in `services/prompt_loader.py`) |
| RAG | **FAISS** + embeddings (`services/rag_service.py`) — used by QA tools |
| Persistence | **MemorySaver** checkpointer (swap for Redis/Postgres for multi-instance) |

## Repository map

| Path | Responsibility |
|------|------------------|
| `api_server.py` | FastAPI app: CORS, `/process`, `/health`, `/health/ready` |
| `main.py` | `process_message` — thread id, reset handling, `receptionist_graph.invoke` |
| `graph/main.py` | Graph definition: nodes `router`, `qa_agent`, `ordering_agent`, `payment_agent`, `cancellation_agent`, `tools` |
| `graph/router.py` | Intent classification (LLM + heuristics), `Command` to agent or `__end__` for greetings |
| `graph/state.py` | `ReceptionistState` + `sliding_window_messages` reducer |
| `graph/*_agent.py` | Specialist nodes; bind tools; return `Command` to `tools` or `__end__` |
| `tools/` | LangChain tools hitting REST APIs, DB helpers, RAG |
| `services/` | LLM provider, HTTP clients, RAG, prompts |
| `utils/` | Logging, retries, message filtering, conversation formatting |
| `tests/` | Unit + integration (`tests/integration` needs LLM) |

## Intents (router)

Router maps conversation to one of: **`product_inquiry`**, **`ordering`**, **`payment`**, **`cancellation`**, **`general_qa`**, or handles **`greeting`** inline (short-circuit to `__end__` with an assistant message). Invalid model output falls back to **`general_qa`**.

## Companion repositories

- **Backend**: expose REST + set **`AGENT_API_URL`** to this service.
- **Frontend**: usually only **`VITE_BACKEND_URL`**; browser talks to Django, not directly to the agent.

See [Integration]({{ site.canonical_docs_url }}/integration.html).
