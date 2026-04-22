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

### Option 3: Interactive CLI
```bash
python main.py
```

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

Use **`.env`** in this folder (see **Installation**). Common keys: **`LLM_PROVIDER`** (`ollama` | `openai`), **`OLLAMA_*`**, **`OPENAI_API_KEY`**, **`OPENAI_MODEL`**, **`BACKEND_API_BASE_URL`**, **`AGENT_API_PORT`**.

## Testing

Run commands from **`AI_receptionist_agent/`** (where `pytest.ini` and `.env` live). Scenario tests load **`.env`** automatically; put **`OPENAI_API_KEY`** there if you use OpenAI or Ollama-off fallback.

| What | Needs | Command |
|------|--------|---------|
| **Fast (default) tests** | Python + deps | `python -m pytest` or `python tests/run_all_tests.py` |
| **LLM scenarios** | Ollama **or** `OPENAI_API_KEY` in `.env` | `python tests/run_scenario_tests.py [<suite>]` |
| **Live Django API** | Backend up + env | `python -m pytest -m integration tests/test_backend_integration.py` |

`pytest.ini` defaults to **`-m "not integration"`**, so plain `pytest` does not run LLM or live-backend integration tests.

### LLM scenarios (`tests/integration/`)

```bash
cd AI_receptionist_agent
python tests/run_scenario_tests.py              # all suites
python tests/run_scenario_tests.py conversation   # swap suite: ordering, payment, cancellation, security
python tests/run_scenario_tests.py flows        # all except security
python tests/run_scenario_tests.py list         # suite names
python tests/run_scenario_tests.py --no-live-logs conversation  # buffered logs
```

**Provider selection (tests):** `tests/llm_env_select.py` — if `LLM_PROVIDER` is unset or `ollama`, probes Ollama; if down and **`OPENAI_API_KEY`** is set, switches to OpenAI for that run. If `LLM_PROVIDER=openai`, a key is required. No LLM → exit **2** after collection. The **running app** (`config.py`) does **not** auto-fallback; only tests do.

**pytest:** use `-m "integration and <marker>"` (e.g. `conversation`). Example:

`python -m pytest tests/integration -m "integration and ordering" -v --tb=line`

**One test:** `python -m pytest tests/integration/test_conversation_scenarios.py::test_greeting_gets_friendly_reply -m "integration and conversation" -v --tb=line`

**Output:** stderr shows each turn (user text, `router → intent → node`, time, assistant reply). Prompts stay in **`logs/agent.log`** (DEBUG). **`AGENT_LOG_FULL_PROMPTS=1`** restores verbose console prompts.

**`--collect-only`:** lists tests only; no LLM calls.

### Backend API integration (Django)

```bash
python tests/run_all_tests.py --integration
# or:
python -m pytest -m integration tests/test_backend_integration.py
```

## Troubleshooting

1. **Port already in use**: Change `AGENT_API_PORT` in `.env` or use a different port with uvicorn.
2. **LLM / scenario exit 2**: Ollama unreachable and no `OPENAI_API_KEY`, or bad `LLM_PROVIDER`. Fix `.env`; see **Testing**.
3. **Import errors**: `pip install -r requirements.txt` from `AI_receptionist_agent/`.
4. **Backend off but `pytest` passes**: Default run is fast mocks only. Use scenario runner or `-m integration` on `tests/integration` / `test_backend_integration.py`.
5. **`--collect-only`**: list-only; remove it to execute tests.
6. **macOS OMP #15 / abort** (PyTorch + FAISS): set **`KMP_DUPLICATE_LIB_OK=TRUE`** (already defaulted on macOS in `config.py` and test env); export in shell if needed.

## License

[Add your license here]
