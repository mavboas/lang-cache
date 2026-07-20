import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_google_genai.chat_models import ChatGoogleGenerativeAIError
from pydantic import BaseModel

from app import config
from app.cache_service import CacheService
from app.metrics import MetricsCollector
from app.mock_bank_data import MOCK_ACCOUNTS
from app.semantic_cache import build_semantic_caches

metrics = MetricsCollector()
_service: Optional[CacheService] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _service
    general_cache, specific_cache = build_semantic_caches()
    _service = CacheService(
        general_cache=general_cache,
        specific_cache=specific_cache,
        metrics=metrics,
    )
    yield


app = FastAPI(title="Semantic Cache Metrics API", lifespan=lifespan)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/", include_in_schema=False)
def chat_ui() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


class AskRequest(BaseModel):
    question: str
    account_id: str = config.DEFAULT_ACCOUNT_ID
    use_cache: bool = True
    session_id: str = ""


class AskResponse(BaseModel):
    response: str
    cache_hit: bool
    cache_scope: str
    latency_ms: float
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    tokens_saved: int


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    # Defined as a sync "def" (not "async def") so FastAPI runs it in its
    # threadpool -- the LangChain agent call and redis check/store are blocking.
    try:
        outcome = _service.ask_llm(
            request.question,
            account_id=request.account_id,
            use_cache=request.use_cache,
            session_id=request.session_id,
        )
    except ChatGoogleGenerativeAIError as exc:
        if "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc):
            raise HTTPException(
                status_code=429,
                detail="Limite de requisicoes do provedor de LLM excedido. Tente novamente mais tarde.",
            ) from exc
        raise
    metric = outcome.metric
    return AskResponse(
        response=outcome.response,
        cache_hit=metric.cache_hit,
        cache_scope=metric.cache_scope,
        latency_ms=metric.latency_ms,
        prompt_tokens=metric.prompt_tokens,
        output_tokens=metric.output_tokens,
        total_tokens=metric.total_tokens,
        tokens_saved=metric.tokens_saved,
    )


@app.get("/accounts")
def accounts() -> dict:
    """List available mock account_ids for the demo (no auth -- this is a
    simulation, not a real banking API)."""
    return {
        account_id: {"customer_name": data["customer_name"], "account_type": data["account_type"]}
        for account_id, data in MOCK_ACCOUNTS.items()
    }


@app.get("/stats")
def stats() -> dict:
    return metrics.summary_dict()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
