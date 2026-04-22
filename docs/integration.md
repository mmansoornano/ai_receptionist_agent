---
layout: default
title: Integration
permalink: /integration.html
---

# Integrating with backend and frontend (separate repos)

This agent repo is meant to be deployed **on its own**. Wire it to your other services with environment variables only.

## Backend (Django) — separate GitHub repo

1. Deploy the backend and note its public origin (e.g. `https://api.example.com`).
2. In **this** repo’s `.env`, set:

   `BACKEND_API_BASE_URL=https://api.example.com`

3. In the **backend** repo’s `.env`, set:

   `AGENT_API_URL=https://agent.example.com`

   (scheme + host + port where this FastAPI app is reachable)

4. Ensure CORS: if the browser ever calls this agent directly, set **`CORS_ORIGINS`** here to your frontend origins. If only server-to-server calls hit this API, you may lock down ingress instead.

## Frontend (React) — separate GitHub repo

The SPA usually uses **`VITE_BACKEND_URL`** (backend only). The backend then proxies or calls the agent using **`AGENT_API_URL`**. You do **not** have to expose the agent to the browser unless your architecture requires it.

## Health checks for orchestration

- `GET /health` — process up.
- `GET /health/ready` — quick checks for backend reachability and LLM configuration (see README).

[← Home]({{ "/" | relative_url }})
