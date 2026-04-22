---
layout: default
title: Home
---

## Agent service overview

This repository is the **AI Receptionist agent service**: a **FastAPI** app that runs a **LangGraph** graph for natural-language conversations. It classifies intent, calls specialist agents (QA, ordering, payment, cancellation), executes **tools** (HTTP to your Django API, RAG over a local vector store, calculators), and returns assistant replies. It supports **Ollama** and **OpenAI** via configuration.

<div class="doc-cards">
  <a class="doc-card" href="{{ site.canonical_docs_url }}/architecture.html"><strong>Architecture</strong><span>What the service does, stack, and repo layout</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/graph.html"><strong>LangGraph</strong><span>Nodes, routing, state, and tool loop</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/api.html"><strong>HTTP API</strong><span><code>/process</code>, health checks, limits</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/integration.html"><strong>Integration</strong><span>Backend + frontend repos and env vars</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/security.html"><strong>Security</strong><span>CORS, PII logging, secrets</span></a>
  <a class="doc-card" href="{{ site.canonical_docs_url }}/dependencies.html"><strong>Dependencies</strong><span>Install and optional lock file</span></a>
</div>

## Capabilities

| Area | Details |
|------|---------|
| **Routing** | `graph/router.py` — LLM classification + rules (e.g. add-to-cart, checkout phrases) → intent + target agent or direct greeting reply |
| **QA** | `graph/qa_agent.py` — RAG, calendar, customer lookup, product list, calculators |
| **Ordering** | `graph/ordering_agent.py` — cart tools, catalog, payment handoff |
| **Payment / cancellation** | Dedicated agents + tool nodes |
| **State** | LangGraph checkpointer (`MemorySaver`) keyed by thread id from `main.py` |
| **Tests** | Pytest: fast mocks + `tests/integration` LLM scenarios — see root **README.md** |

## Runbook in code

Clone this repo only, create **`.env`** from **`.env.example`**, install **`requirements.txt`**, then `python api_server.py` or `python main.py`. Full commands and markers live in the repository **README.md** (not duplicated here so a single source stays accurate).
