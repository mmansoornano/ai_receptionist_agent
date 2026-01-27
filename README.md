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
   OPENAI_MODEL=gpt-4-turbo-preview

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

Run tests:
```bash
python tests/run_all_tests.py
```

Or run individual test files:
```bash
python tests/test_agent_flow.py
python tests/test_backend_integration.py
```

## Development

For interactive testing:
```bash
python main.py
```

This starts a command-line interface where you can chat with the agent.

## Troubleshooting

1. **Port already in use**: Change `AGENT_API_PORT` in `.env` or use a different port with uvicorn
2. **LLM provider errors**: Ensure Ollama is running (if using Ollama) or OpenAI API key is set
3. **Import errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`

## License

[Add your license here]
