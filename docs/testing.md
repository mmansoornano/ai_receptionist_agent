---
layout: default
title: Testing
---

## Where to run

All commands assume the repository root **`AI_receptionist_agent/`** (where **`pytest.ini`** and **`.env`** live). Create **`.env`** from **`.env.example`** before scenario or integration runs.

## Quick commands

| Goal | Prerequisites | Command |
|------|-----------------|---------|
| **Fast suite (default)** | `pip install -r requirements.txt` | `python -m pytest` or `python tests/run_all_tests.py` |
| **LLM scenario suites** | Ollama **or** `OPENAI_API_KEY` in `.env` | `python tests/run_scenario_tests.py` or `python tests/run_scenario_tests.py conversation` |
| **Live Django HTTP tools** | Backend up; `BACKEND_API_BASE_URL` reachable | `python -m pytest -m integration tests/test_backend_integration.py` |

**`pytest.ini`** sets **`addopts = -m "not integration"`**, so a plain **`pytest`** run skips integration-marked tests (LLM + live backend). That keeps CI and local checks fast.

## Pytest markers (`pytest.ini`)

| Marker | Meaning |
|--------|---------|
| **`integration`** | Needs live backend and/or LLM |
| **`conversation`** | Greeting / FAQ-style turns |
| **`ordering`** | Cart and ordering flows |
| **`payment`** | Payment flows |
| **`cancellation`** | Cancellation / refund flows |
| **`security`** | Prompt-injection style abuse tests |

Run a slice, for example:

```bash
python -m pytest tests/integration -m "integration and ordering" -v --tb=line
```

List tests without executing (no LLM cost):

```bash
python -m pytest tests/integration --collect-only
```

## Scenario runner (`tests/integration/`)

```bash
cd AI_receptionist_agent
python tests/run_scenario_tests.py              # all suites
python tests/run_scenario_tests.py list         # suite names
python tests/run_scenario_tests.py conversation
python tests/run_scenario_tests.py ordering
python tests/run_scenario_tests.py flows        # all except security
python tests/run_scenario_tests.py --no-live-logs conversation
```

**Provider behavior in tests:** **`tests/llm_env_select.py`** may prefer Ollama when `LLM_PROVIDER` is unset or `ollama`, and fall back to OpenAI when Ollama is down and **`OPENAI_API_KEY`** is set. **`LLM_PROVIDER=openai`** requires a key. With no usable LLM, collection can exit with code **2**.

## Logs and verbosity

- Turn progress prints: scenario runner logs each turn to stderr.
- Full prompts: see **`logs/agent.log`** (DEBUG). Set **`AGENT_LOG_FULL_PROMPTS=1`** for verbose console prompts during debugging.

## Related docs

- [Architecture]({{ site.canonical_docs_url }}/architecture.html) — repository map includes a **Testing** column per area.
- Root **README.md** — authoritative copy of commands, troubleshooting, and macOS OpenMP notes.
