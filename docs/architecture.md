---
layout: default
title: Architecture
permalink: /architecture.html
---

# What this repository does

## Role

The **agent** is the conversational brain. It:

1. Accepts user text (and metadata such as channel, language, customer id) via **`POST /process`** (`api_server.py`).
2. Runs **`receptionist_graph`** (`graph/main.py`): **router** classifies intent, then one of **qa_agent**, **ordering_agent**, **payment_agent**, or **cancellation_agent** runs.
3. Calls **tools** (HTTP to your Django backend, RAG, calculators, etc.) through LangChain tool bindings.
4. Persists **conversation state** with LangGraph’s checkpointer (in-memory saver in this codebase unless you swap it).

## Main paths in the repo

| Path | Purpose |
|------|---------|
| `graph/main.py` | Graph definition: nodes and `call_tools` routing |
| `graph/router.py` | Intent classification and handoff |
| `graph/qa_agent.py`, `ordering_agent.py`, … | Specialist agents |
| `prompts/*.yaml` | Versioned system / task prompts |
| `services/` | LLM provider, HTTP clients to backend, RAG |
| `tools/` | Tool implementations exposed to the LLM |

## Companion repositories (deployed separately)

- **Django backend**: product catalog, cart, payments, webhooks. The agent reaches it via **`BACKEND_API_BASE_URL`** in `.env`.
- **React frontend** (optional): typically talks to the **backend** only; the backend is configured with **`AGENT_API_URL`** to call this service when a flow needs the agent.

[← Home]({{ "/" | relative_url }})
