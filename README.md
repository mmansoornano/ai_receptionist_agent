# AI Receptionist Agent

An intelligent AI receptionist agent system built with LangGraph, FastAPI, and multiple LLM providers.

## Features

- Multi-agent system with routing, QA, ordering, payment, and cancellation agents
- Support for multiple LLM providers (OpenAI, Ollama)
- SMS and voice channel support
- Conversation state persistence
- Product knowledge base with RAG
- Cart management
- Payment processing
- Appointment scheduling

## Prerequisites

- Python 3.8+
- Virtual environment (recommended)
- `.env` file with configuration (see Configuration section)

## Installation

1. **Clone or navigate to the project directory**

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the project root with the following variables:
   ```env
   # LLM Provider Configuration
   LLM_PROVIDER=ollama  # or 'openai'
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.1:8b
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini

   # Google Calendar (optional)
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   GOOGLE_CALENDAR_ID=your_calendar_id
   GOOGLE_CREDENTIALS_PATH=credentials.json
   GOOGLE_TOKEN_PATH=token.json

   # Backend API Configuration
   BACKEND_API_BASE_URL=http://localhost:8000

   # Agent API Server Configuration (optional)
   AGENT_API_PORT=8001
   AGENT_API_HOST=0.0.0.0
   ```

## Running the Server

### Option 1: Run the API Server directly
```bash
python api_server.py
```

The server will start on `http://0.0.0.0:8001` by default (or the port specified in `AGENT_API_PORT`).

### Option 2: Run with uvicorn
```bash
uvicorn api_server:app --host 0.0.0.0 --port 8001
```

### Option 3: Interactive Mode (for testing)
```bash
python main.py
```

This will start an interactive command-line interface for testing the agent.

## API Endpoints

### POST `/process`
Process a message through the agent system.

**Request Body:**
```json
{
  "message": "I'd like to order a pizza",
  "phone_number": "+1234567890",
  "channel": "sms",
  "language": "en",
  "conversation_id": "optional_conversation_id",
  "customer_id": "optional_customer_id"
}
```

**Response:**
```json
{
  "success": true,
  "response": "I'd be happy to help you order a pizza...",
  "error": null
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## API Documentation

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## Project Structure

```
.
├── api_server.py          # FastAPI server entry point
├── main.py                # Main agent processing logic
├── config.py              # Configuration management
├── graph/                 # LangGraph agent definitions
│   ├── main.py           # Main graph definition
│   ├── router.py         # Router agent
│   ├── qa_agent.py       # QA agent
│   ├── ordering_agent.py # Ordering agent
│   ├── payment_agent.py  # Payment agent
│   └── cancellation_agent.py # Cancellation agent
├── services/              # Business logic services
│   ├── cart_service.py
│   ├── customer_service.py
│   ├── payment_service.py
│   ├── product_service.py
│   └── rag_service.py    # RAG for product knowledge
├── tools/                 # Agent tools
│   ├── cart_tool.py
│   ├── payment_tool.py
│   ├── product_tool.py
│   └── ...
├── prompts/               # Agent prompts (YAML)
└── tests/                 # Test files
```

## Configuration

The system uses environment variables for configuration. Key settings:

- **LLM_PROVIDER**: Choose between `ollama` (default) or `openai`
- **AGENT_API_PORT**: Port for the API server (default: 8001)
- **BACKEND_API_BASE_URL**: Backend API URL for database operations

## Testing

Overview for someone new:

| What | Needs | Command |
|------|--------|---------|
| **Fast (default) tests** | Python + deps only | `python -m pytest` from `AI_receptionist_agent/` |
| **LLM scenario tests** | Ollama **or** OpenAI key in `.env` | `python tests/run_scenario_tests.py …` |
| **Live Django API tests** | Backend running + env | `pytest tests/test_backend_integration.py -m integration` |

Default `pytest.ini` runs **`-m "not integration"`**, so a plain `pytest` run never hits the LLM or Django integration tests.

---

### Prerequisites for scenario tests

1. **Working directory:** run everything from the **`AI_receptionist_agent`** project root (same folder as `pytest.ini` and `.env`).
2. **`.env`:** put `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, default `gpt-4o-mini`) in **`AI_receptionist_agent/.env`**. The scenario runner loads that file before checking keys (you do not need to `export` vars manually unless you prefer).
3. **At least one LLM:** either start **Ollama** at `OLLAMA_BASE_URL` (default `http://localhost:11434`), **or** set **`OPENAI_API_KEY`** in `.env`.

---

### Fast tests (no LLM / no live backend)

Mocked HTTP, router, and utils only. **Passing these does not prove Ollama, OpenAI, or your Django backend is running.**

```bash
cd AI_receptionist_agent
python -m pytest
# or:
python tests/run_all_tests.py
```

---

### Scenario integration tests (LLM required)

Suites live under **`tests/integration/`** (conversation, ordering, payment, cancellation, security / prompt-injection).

#### Recommended: `run_scenario_tests.py`

```bash
cd AI_receptionist_agent

# All suites (conversation + ordering + payment + cancellation + security)
python tests/run_scenario_tests.py
python tests/run_scenario_tests.py all

# One suite at a time
python tests/run_scenario_tests.py conversation
python tests/run_scenario_tests.py ordering
python tests/run_scenario_tests.py payment
python tests/run_scenario_tests.py cancellation
python tests/run_scenario_tests.py security

# Core flows only (no security suite)
python tests/run_scenario_tests.py flows

# Print valid suite names
python tests/run_scenario_tests.py list

# Quieter pytest-style capture (logs mostly after failure)
python tests/run_scenario_tests.py --no-live-logs conversation

# Less pytest chatter
python tests/run_scenario_tests.py -q conversation
```

#### How Ollama vs OpenAI is chosen (tests only)

Logic lives in **`tests/llm_env_select.py`** (`prepare_llm_env`):

- If **`LLM_PROVIDER=openai`:** tests use OpenAI; **`OPENAI_API_KEY`** must be set in `.env` (or the environment).
- If **`LLM_PROVIDER` is unset or `ollama`:** the runner probes Ollama (`/api/tags`). If Ollama is **reachable**, tests use **Ollama**. If Ollama is **not** reachable and **`OPENAI_API_KEY`** is set, **`LLM_PROVIDER` is switched to `openai`** for that run so you can leave `.env` as `LLM_PROVIDER=ollama` for local dev and still run scenarios when Ollama is stopped.
- If Ollama is down **and** there is **no** API key, the run **exits with code 2** after collection (clear error message), not a fake green “all skipped” run.

The **FastAPI / `main.py` app** still follows **`LLM_PROVIDER`** in `config.py` only; it does **not** auto-fallback to OpenAI when Ollama is down (that behavior is for **tests**).

#### Same suites with `pytest` directly

From `AI_receptionist_agent/`, always include **`-m "integration and …"`** so markers match `pytest.ini` (default filter excludes `integration`).

```bash
python -m pytest tests/integration -m "integration and conversation" -v --tb=line
python -m pytest tests/integration -m "integration and ordering" -v --tb=line
python -m pytest tests/integration -m "integration and payment" -v --tb=line
python -m pytest tests/integration -m "integration and cancellation" -v --tb=line
python -m pytest tests/integration -m "integration and security" -v --tb=line
```

#### One file or one test

```bash
# Whole file
python -m pytest tests/integration/test_conversation_scenarios.py -m "integration and conversation" -v --tb=line

# Single test (copy exact node id from pytest output if parametrized)
python -m pytest tests/integration/test_conversation_scenarios.py::test_greeting_gets_friendly_reply -m "integration and conversation" -v --tb=line

# By keyword in test name
python -m pytest tests/integration -m "integration and conversation" -k greeting -v --tb=line
```

#### What prints during scenario runs

- **`run_scenario_tests.py`** uses live streaming (`--capture=tee-sys`, library `log_cli` at WARNING) unless you pass **`--no-live-logs`**.
- During integration scenarios, the agent logger’s **stdout** level is raised so you do **not** get long router / graph / prompt dumps on the console.
- Each graph turn prints a short **stderr** block: your **user** message, a **router → intent → node** (or `__end__`) line with **seconds**, then the **assistant** reply.
- Full prompts and verbose history are written at **DEBUG** to **`logs/agent.log`**. To force full prompts on the console for debugging: **`AGENT_LOG_FULL_PROMPTS=1`** before the command.

Other useful env vars (usually set automatically for pytest):

- **`AGENT_TEST_MINIMAL_LOGS`** — set in `tests/conftest.py` during pytest so normal runs stay quiet; use `AGENT_LOG_FULL_PROMPTS=1` to override prompt visibility when needed.

#### `pytest --collect-only`

`--collect-only` **only lists** tests; it does **not** call the LLM. Remove it to execute scenarios.

#### macOS / FAISS “OMP: Error #15”

PyTorch and `faiss-cpu` may both link OpenMP. The repo sets **`KMP_DUPLICATE_LIB_OK=TRUE`** on macOS in `config.py` and in scenario test env; export it in your shell or `.env` if you still see aborts.

---

### Backend API integration (Django)

Requires a running backend and correct **`BACKEND_API_BASE_URL`** (and auth if your tests need it).

```bash
python tests/run_all_tests.py --integration
# or:
python -m pytest -m integration tests/test_backend_integration.py
```

## Development

For interactive testing:
```bash
python main.py
```

This starts a command-line interface where you can chat with the agent.

## Troubleshooting

1. **Port already in use**: Change `AGENT_API_PORT` in `.env` or use a different port with uvicorn
2. **LLM provider errors**: Ensure Ollama is running (if using Ollama) or set **`OPENAI_API_KEY`** in **`AI_receptionist_agent/.env`** for OpenAI / fallback (see **Testing → How Ollama vs OpenAI is chosen**).
3. **Scenario runner exits with code 2 right away**: No LLM available (Ollama unreachable and no API key), or invalid `LLM_PROVIDER`. Fix `.env` and retry; see scenario test section above.
4. **Import errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`
5. **“I turned the backend off but `pytest` still passes”**: Default `pytest` only runs **fast** tests (mocks). Use `pytest tests/integration -m integration` or `python tests/run_scenario_tests.py …` for LLM scenarios, and `pytest tests/test_backend_integration.py -m integration` for live Django API checks.
6. **`--collect-only` shows tests but nothing runs**: That mode never executes tests; remove `--collect-only` to actually run the agent.

## License

[Add your license here]
