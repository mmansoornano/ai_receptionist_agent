# YAML scenario suites

YAML files here describe **multi-turn chats** against the real LangGraph agent. Each assistant reply is scored by the **LLM judge** (`tests/llm_judge.py`): five rubrics when V2 is on (including **`grounded_in_tools`** and **`tool_use_reasonable`** when tools ran), with a **terminal rubric chart** after every turn.

## Run

From the agent repo root (`AI_receptionist_agent/`):

```bash
python tests/run_yaml_scenarios.py tests/scenarios/example_scenarios.yml
# Security / injection / out-of-domain suite (more scenarios, longer run)
python tests/run_yaml_scenarios.py tests/scenarios/security_scenarios.yml
# Optional: write metrics JSON + static HTML (see docs/testing.md)
python tests/run_yaml_scenarios.py tests/scenarios/example_scenarios.yml --output-dir tests/reports
```

Same **`.env`** as the app (Ollama / OpenAI, `BACKEND_API_BASE_URL`, …). Judge env vars match pytest integration tests (`JUDGE_*`, `AGENT_SKIP_LLM_JUDGE`, …).

## Schema

| Field | Level | Required | Description |
|-------|--------|----------|-------------|
| **`name`** | root | no | Suite display name (default `unnamed_suite`). |
| **`description`** | root | no | Free text. |
| **`defaults`** | root | no | Default `customer_id` and `scenario_kind` for scenarios/turns. |
| **`defaults.customer_id`** | defaults | no | Default `test_customer` if omitted. |
| **`defaults.scenario_kind`** | defaults | no | `normal` or `hostile` (default `normal`). |
| **`scenarios`** | root | **yes** | Non-empty list of scenarios. |
| **`scenarios[].id`** | scenario | **yes** | Stable id (logging / thread suffix). |
| **`scenarios[].description`** | scenario | no | Notes only. |
| **`scenarios[].thread_id`** | scenario | no | LangGraph thread id; auto-generated from suite `name` + `id` if omitted. |
| **`scenarios[].customer_id`** | scenario | no | Overrides `defaults.customer_id`. |
| **`scenarios[].scenario_kind`** | scenario | no | `normal` or `hostile`; overrides default for all turns unless a turn sets its own. |
| **`scenarios[].turns`** | scenario | **yes** | Ordered list of user lines (min length 1). |
| **`turns[].user`** | turn | **yes** | User message for that turn. |
| **`turns[].scenario_kind`** | turn | no | Overrides scenario-level kind for **this** turn only (e.g. benign chat then one hostile line). |

**Multi-turn:** turns after the first reuse the same `thread_id` and append to prior graph state (`continue_state`), like `graph_thread` in pytest.

**Exit code:** `0` if every turn passes the judge; `1` if any turn fails or YAML/graph errors.
