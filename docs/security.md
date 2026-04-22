---
layout: default
title: Security
---

## PII in logs (`main.py`)

By default, **INFO** logs **mask** phone / `conversation_id` / `customer_id` and **truncate** long user or assistant text previews. Set **`AGENT_LOG_PII=1`** only on trusted machines when you need full values for debugging.

## HTTP surface (`api_server.py`)

- **`POST /process`** — payload size limits on fields; **503** only on uncaught exceptions (see [HTTP API]({{ site.canonical_docs_url }}/api.html)).
- **CORS** — explicit origins via **`CORS_ORIGINS`** recommended for public demos.

## Secrets

Never commit **`.env`**. Use **`.env.example`** as the template. Rotate keys if a demo repo was ever public with real credentials.

## Prompt injection

Scenario tests under **`tests/integration/`** include abuse-style prompts; run them when you change router or tool prompts. They are not a guarantee of safety in adversarial settings—layer policy + rate limits at the edge for production.
