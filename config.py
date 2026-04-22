"""Configuration for the agent system - loads from .env file."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback to system environment
    load_dotenv()

# macOS: PyTorch + faiss-cpu often both link libomp; RAG/FAISS search can abort without this.
if sys.platform == "darwin":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# LLM Provider Configuration
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama').lower()
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.1:8b')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

# Google Calendar Configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID')
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
GOOGLE_TOKEN_PATH = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')

# Language Configuration (defaults - not in .env)
DEFAULT_LANGUAGE = 'en'
DEFAULT_CHANNEL = 'voice'

# Backend API Configuration
BACKEND_API_BASE_URL = os.getenv('BACKEND_API_BASE_URL', 'http://localhost:8000')

# Agent Configuration (defaults - not in .env)
MAX_CONVERSATION_TURNS = 20
ENABLE_VOICE = True
