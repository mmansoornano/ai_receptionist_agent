---
layout: default
title: Integration
---

## Three-repo layout

This agent repo is deployed **alone**. Wire it to other services **only with environment variables** (see **`.env.example`** in the repository root).

### Django backend (separate GitHub repository)

| Variable (this repo) | Meaning |
|------------------------|---------|
| `BACKEND_API_BASE_URL` | Public base URL of the Django API (no trailing slash issues—normalize in code if needed). |

| Variable (backend repo) | Meaning |
|---------------------------|---------|
| `AGENT_API_URL` | Public base URL of **this** FastAPI service (where `POST /process` is exposed). |

Typical flow: **Browser → Frontend → Django → (server-side) → Agent** when a feature needs LLM. The SPA’s `VITE_BACKEND_URL` points at Django only; it does **not** need the agent URL unless you change that design.

### CORS

If a browser ever calls this agent directly, set **`CORS_ORIGINS`** here to match those origins. Otherwise restrict at your API gateway.

### TLS

Terminate TLS at your reverse proxy (nginx, Traefik, cloud load balancer) in production; keep **`AGENT_API_HOST` / port`** aligned with what the backend uses in `AGENT_API_URL`.
