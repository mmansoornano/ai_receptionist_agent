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

That path uses the same **`invoke_graph`** / **`graph_thread`** fixtures as **`run_scenario_tests.py`**, so each graph turn still prints the **boxed summary** (capture is suspended for that print only — see **What you see each turn** below).

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
python tests/run_scenario_tests.py --live-logs conversation   # optional: noisy live logs
```

**`--live-logs`** is wired by **`run_scenario_tests.py`** (sets **`AGENT_SCENARIO_LIVE_LOGS=1`** for the child **`pytest`**). To get the same live tee when you invoke **`python -m pytest …`** yourself, export **`AGENT_SCENARIO_LIVE_LOGS=1`** in the shell first.

**Provider behavior in tests:** **`tests/llm_env_select.py`** may prefer Ollama when `LLM_PROVIDER` is unset or `ollama`, and fall back to OpenAI when Ollama is down and **`OPENAI_API_KEY`** is set. **`LLM_PROVIDER=openai`** requires a key. With no usable LLM, collection can exit with code **2**.

## What you see each turn (scenario tests)

By default the harness **does not stream agent logs or prompts** while tests pass. After each graph invoke it prints a **single framed block** to your real terminal with:

1. **USER INPUT** — the user line for that turn  
2. **ROUTER** — `intent` and destination node (e.g. `qa_agent` or `__end__`)  
3. **TIME** — wall time for that invoke in seconds  
4. **AGENT OUTPUT** — the assistant text returned for that turn  

That output is written through **`_print_turn_box_visible`** in **`tests/integration/conftest.py`**: it **suspends pytest’s global capture** (same idea whether you use **`python tests/run_scenario_tests.py …`** or **`python -m pytest tests/integration -m "…"`**), then falls back to **`capsys.disabled()`** if no capture manager is present. **Prompts and long agent INFO lines stay off the console** unless a test **fails** (pytest then shows captured output) or you opt into noise with **`--live-logs`**. Full history remains in **`logs/agent.log`** at DEBUG.

Example (stylistic mock for this page; your terminal uses box-drawing characters):

<div class="scenario-turn-mock" aria-hidden="true"><pre class="scenario-turn-mock-pre"><span class="sm-muted">┌────────────────────────────────────────────────────────────────┐</span>
<span class="sm-label">│ USER INPUT</span>
<span class="sm-body">│   What protein bars do you have?</span>
<span class="sm-muted">├────────────────────────────────────────────────────────────────┤</span>
<span class="sm-label">│ ROUTER</span>
<span class="sm-body">│   intent='product_inquiry'  →  'qa_agent'</span>
<span class="sm-muted">├────────────────────────────────────────────────────────────────┤</span>
<span class="sm-label">│ TIME</span>
<span class="sm-body">│   1.24</span>
<span class="sm-muted">├────────────────────────────────────────────────────────────────┤</span>
<span class="sm-label">│ AGENT OUTPUT</span>
<span class="sm-body">│   We carry several flavors including …</span>
<span class="sm-muted">└────────────────────────────────────────────────────────────────┘</span></pre></div>

On **failure**, pytest prints its usual traceback and captured streams; **`pytest_exception_interact`** also reminds you where **`logs/agent.log`** is. Use **`AGENT_LOG_FULL_PROMPTS=1`** only when you deliberately want full prompts echoed to the console.

## Related docs

- [Architecture]({{ site.canonical_docs_url }}/architecture.html) — repository map includes a **Testing** column per area.
- Root **README.md** — authoritative commands and troubleshooting.
