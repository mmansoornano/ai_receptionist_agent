---
layout: default
title: Input guardrails
---

## Overview

Every user turn enters the graph at **`input_guard`** (see `graph/main.py`) **before** the router. The guard:

1. **Allowlist** — very short pure greetings (from `config/guard_rules.yaml`) go straight to the **router** with no extra cost.
2. **Deterministic block** — substring and regex rules in `config/guard_rules.yaml` block disallowed input; the client receives a **refusal** `AIMessage` and the run ends with `intent: guardrail_refuse` (main shopping agents are not run).
3. **LLM policy** — if the text is not allowlisted and not blocked, a **small** LLM call (same provider as the app, model from `GUARD_OLLAMA_MODEL` / `GUARD_OPENAI_MODEL` in `config.py`) returns structured **allow** or **refuse** per `prompts/input_guard.yaml`. On LLM error, the guard **fails closed** with a generic safe reply.
4. **Skip LLM** — set **`AGENT_SKIP_GUARD_LLM=1`** to treat unknown lines as **allow** (only explicit rules block). Useful for local tests without a second model round-trip; not recommended for production abuse resistance.

## Configuration

| Source | Role |
|--------|------|
| [`config/guard_rules.yaml`](../config/guard_rules.yaml) | `simple_greeting_allowlist`, `substring_blocklist`, `regex_blocklist`, `refusal_templates` |
| [`prompts/input_guard.yaml`](../prompts/input_guard.yaml) | System prompt for the policy LLM |
| `.env` | `GUARD_OLLAMA_MODEL`, `GUARD_OPENAI_MODEL`, `AGENT_SKIP_GUARD_LLM` |

The **router** and **QA** agents no longer duplicate a large safety catch-all; blocking happens at the guard or via normal shop prompts downstream.

## Tests

- [`tests/test_input_guard.py`](../tests/test_input_guard.py) — deterministic rules and fail-closed behavior.
- Integration security scenarios still run the full graph; blocked turns never reach the router.
