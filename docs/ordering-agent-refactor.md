---
layout: default
title: Ordering agent refactor
permalink: /ordering-agent-refactor.html
---

# Ordering agent module split (deferred)

`graph/ordering_agent.py` is large (ordering logic, tools, message shaping).

## Planned direction

Split **without behavior change** into smaller modules (prompt assembly, tool normalization, graph wiring).

## Status

Deferred; track with issues/PRs labeled `refactor/ordering`.

[← Home]({{ "/" | relative_url }})
