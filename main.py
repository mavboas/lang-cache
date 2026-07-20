import uvicorn

from app import config

# =====================================================================
# ENTRY POINT: runs the FastAPI server.
#
# POST /ask    { "question": "..." } -> asks the semantic cache / LLM
#              (also appends the request's metrics to sessions/<session_id>.csv)
# GET  /stats  -> JSON summary (hits, misses, avg latency, tokens)
# GET  /docs   -> interactive Swagger UI to try /ask by hand
# =====================================================================
if __name__ == "__main__":
    uvicorn.run("app.server:app", host=config.SERVER_HOST, port=config.SERVER_PORT)