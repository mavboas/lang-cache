import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Which LLM provider to use: GEMINI or TECENT
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "GEMINI").upper()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODELO_GEMINI = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# Tencent Hunyuan model served through OpenRouter's OpenAI-compatible API
OPENAI_TECENT_KEY = os.getenv("OPENAI_TECENT_KEY")
TECENT_MODEL = os.getenv("TECENT_MODEL", "tencent/hy3:free")
TECENT_BASE_URL = os.getenv("TECENT_BASE_URL", "https://openrouter.ai/api/v1")

if MODEL_PROVIDER == "GEMINI" and not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")
if MODEL_PROVIDER == "TECENT" and not OPENAI_TECENT_KEY:
    raise ValueError("OPENAI_TECENT_KEY not found in .env file")

# Semantic cache configuration
CACHE_NAME = "artigo_medium_llm_cache"
# Overridden to redis://valkey:6379 when running inside docker-compose
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DISTANCE_THRESHOLD = float(os.getenv("DISTANCE_THRESHOLD", "0.30"))  # The lower, the stricter the similarity
CACHE_TTL = 3600  # Cache time to live: 1 hour
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")

# API server configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# Mock bank agent configuration
DEFAULT_ACCOUNT_ID = os.getenv("DEFAULT_ACCOUNT_ID", "demo-001")
