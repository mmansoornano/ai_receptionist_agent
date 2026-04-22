---
layout: default
title: HTTP API
---

Defined in **`api_server.py`** (FastAPI).

## `POST /process`

**Body (JSON):** `message` (string, max **16000** chars), `phone_number`, optional `channel` (default `sms`), `language`, `conversation_id`, `customer_id`.

**Success:** HTTP **200**, JSON `{ "success": true, "response": "<assistant text>", "error": null }`.

**Failures:** Most graph/LLM issues are caught inside **`main.process_message`** and returned as a **friendly string** with **200** + `success: true`. An **unexpected exception** yields HTTP **503** with the same JSON shape and `success: false` plus an `error` string.

## `GET /health`

Liveness: `{ "status": "healthy" }`.

## `GET /health/ready`

Readiness-style **dependency report** (short timeouts):

- **`backend_ok`** — HEAD/GET to `BACKEND_API_BASE_URL` root.
- **`llm_ok`** — if `LLM_PROVIDER=openai`, API key present; if `ollama`, Ollama `/api/tags` reachable.

Response is always **HTTP 200** with `status` `ready` or `degraded`, plus `checks` details—use for dashboards, not strict binary gates unless you interpret the JSON.

## CORS

Set **`CORS_ORIGINS`** in `.env` to a comma-separated list of browser origins. If unset, the app uses **`*`** with **credentials disabled** (safe wildcard pattern).

## Interactive CLI

`python main.py` — same `process_message` path without HTTP.

See also the root **README.md** (OpenAPI at `/docs` when the server runs).
