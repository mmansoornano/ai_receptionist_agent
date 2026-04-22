---
layout: default
title: Ordering refactor
---

## Status: deferred

`graph/ordering_agent.py` is intentionally large today: it mixes prompt construction, catalog handling, tool orchestration, and LangGraph **`Command`** routing.

## Planned refactor (no behavior change)

Split into smaller modules (e.g. prompt builders, cart message normalizers, tool wiring) once API and docs stabilize. Track with issues labeled **`refactor/ordering`**.

This does not block shipping demos—the runtime behavior and tests are the source of truth.
