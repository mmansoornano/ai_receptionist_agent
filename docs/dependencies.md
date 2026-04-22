---
layout: default
title: Dependencies
---

## Install

```bash
cd AI_receptionist_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Reproducible demos

`requirements.txt` uses **lower bounds** (`>=`). For a client demo on a fixed date:

```bash
pip freeze > requirements.lock.txt
```

Commit **`requirements.lock.txt`** when you want teammates to `pip install -r requirements.lock.txt` for an identical stack.

## Notable stacks inside the repo

- **LangGraph / LangChain** — graph and LLM/tool abstractions.
- **Django** — pulled in for some tools/ORM paths (see `requirements.txt` comments); many HTTP paths use **`requests`** against **`BACKEND_API_BASE_URL`** instead.

## macOS note

PyTorch + **FAISS** can trigger OpenMP conflicts. This repo sets **`KMP_DUPLICATE_LIB_OK`** on Darwin in `config.py`; export it in the shell if you still see **OMP #15** aborts.
