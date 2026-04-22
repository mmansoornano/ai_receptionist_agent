---
layout: default
title: Security and logging
permalink: /security.html
---

# Security and logging (agent service)

## PII in logs (`main.py`)

At **INFO**, phone / `conversation_id` / `customer_id` are **masked**; long user or assistant text is **preview-truncated** unless **`AGENT_LOG_PII=1`** is set (local debugging only).

## HTTP API (`api_server.py`)

- **`POST /process`**: message length cap; **503** only if `process_message` raises an unexpected exception (most graph failures still return a friendly string with **200** — see README).
- **`CORS_ORIGINS`**: comma-separated list. If unset, wildcard origin is used **without** credentials.

## Secrets

Use **`.env.example`** as a template; never commit `.env` or API keys.

[← Home]({{ "/" | relative_url }})
